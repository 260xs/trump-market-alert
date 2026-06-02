from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

from .classify import classify_signal
from .config import load_settings, load_yaml, require_settings
from .db import Database
from .extract import best_quote, contains_trump_reference, normalize_text, stable_hash
from .mapping import EntityMapper
from .models import Alert, EntityMatch, SourceItem, utc_now
from .notifiers import format_alert, send_alert, send_discord_message
from .sources import fetch_all_sources

LOG = logging.getLogger(__name__)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def is_recent(item: SourceItem, max_age_hours: int) -> bool:
    if item.published_at_utc is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    return item.published_at_utc >= cutoff


def is_direct_trump_source(item: SourceItem) -> bool:
    name = item.source_name.lower()
    return item.source_type == "truth_social" or "donald j trump" in name or "@realdonaldtrump" in name


def build_alert(item: SourceItem, match: EntityMatch, mapper: EntityMapper) -> Alert:
    combined = normalize_text(f"{item.title}. {item.text}")
    quote_terms = mapper.all_terms_for_quote(match)
    quote = best_quote(combined, quote_terms)
    classification = classify_signal(quote, match)
    published_day = item.published_at_utc.date().isoformat() if item.published_at_utc else "unknown-date"
    # Dedupe the same quote/entity/day across duplicate news articles and mirrored posts.
    fingerprint = stable_hash(quote.lower(), match.entity_id, published_day)

    return Alert(
        fingerprint=fingerprint,
        quote=quote,
        source_name=item.source_name,
        source_type=item.source_type,
        source_url=item.url,
        time_published=item.published_at_utc,
        time_detected=utc_now(),
        entity_name=match.name,
        entity_type=match.entity_type,
        matched_alias=match.matched_alias,
        related_assets=match.related_assets,
        signal=classification.signal,
        confidence=classification.confidence,
        alert_type=classification.alert_type,
        reason=classification.reason,
    )


def process_item(item: SourceItem, mapper: EntityMapper) -> list[Alert]:
    combined = normalize_text(f"{item.title}. {item.text}")
    if not combined:
        return []

    direct_source = is_direct_trump_source(item)
    if not direct_source and not contains_trump_reference(combined):
        return []

    matches = mapper.match(combined)
    market_context = mapper.has_market_context(combined)

    if not matches and not market_context:
        return []

    if not matches:
        matches = [mapper.generic_market_match()]

    alerts: list[Alert] = []
    for match in matches[:3]:
        alerts.append(build_alert(item, match, mapper))
    return alerts


def run_once() -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    require_settings(settings)

    sources_config = load_yaml(settings.sources_path)
    entities_config = load_yaml(settings.entities_path)
    mapper = EntityMapper.from_config(entities_config)

    polling = sources_config.get("polling", {}) or {}
    max_item_age_hours = int(polling.get("max_item_age_hours", 96))
    cleanup_raw_days = int(polling.get("cleanup_raw_days", 180))
    cleanup_runs_days = int(polling.get("cleanup_runs_days", 30))

    run_id: int | None = None
    items_seen = 0
    alerts_sent = 0

    with Database(settings.database_url) as db:
        db.init()
        run_id = db.start_run()
        try:
            db.cleanup(raw_days=cleanup_raw_days, run_days=cleanup_runs_days)
            items = fetch_all_sources(sources_config, x_bearer_token=settings.x_bearer_token)
            LOG.info("Fetched %s source items", len(items))

            for item in items:
                if not is_recent(item, max_item_age_hours):
                    continue
                items_seen += 1
                combined = normalize_text(f"{item.title}. {item.text}")
                db.upsert_raw_item(item, stable_hash(combined))

                for alert in process_item(item, mapper):
                    if not db.insert_alert_if_new(alert):
                        continue
                    send_alert(settings.telegram_bot_token, settings.telegram_chat_id, alert)
                    alerts_sent += 1
                    if settings.discord_webhook_url:
                        try:
                            send_discord_message(settings.discord_webhook_url, format_alert(alert))
                        except Exception as exc:  # noqa: BLE001
                            LOG.warning("Discord notification failed: %s", exc)

            db.finish_run(run_id, "success", items_seen, alerts_sent)
            LOG.info("Run complete. items_seen=%s alerts_sent=%s", items_seen, alerts_sent)
            return 0
        except Exception as exc:  # noqa: BLE001
            LOG.exception("Run failed")
            if run_id is not None:
                db.finish_run(run_id, "failed", items_seen, alerts_sent, error=str(exc))
            raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Trump Market Alert scanner")
    parser.add_argument("--once", action="store_true", help="Run exactly one scan and exit")
    args = parser.parse_args(argv)

    if not args.once:
        print("This deployment is designed for scheduled --once runs.", file=sys.stderr)
    return run_once()


if __name__ == "__main__":
    raise SystemExit(main())
