from __future__ import annotations

import logging
from datetime import datetime, timezone

from alerts.discord import DiscordClient
from alerts.telegram import TelegramClient, build_market_alert_text
from config import Settings, load_asset_map
from database.db import Database
from database.models import Statement, AlertDecision
from dedupe import normalize_quote, quote_hash, normalized_quote_hash, alert_duplicate_key
from nlp.entity_extractor import EntityExtractor
from nlp.sentiment_classifier import classify_signal
from nlp.ticker_mapper import TickerMapper

log = logging.getLogger(__name__)


class AlertPipeline:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings
        mapper = TickerMapper(load_asset_map())
        self.extractor = EntityExtractor(mapper)
        self.telegram = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)
        self.discord = DiscordClient(settings.discord_webhook_url)

    def process_statement(self, stmt: Statement) -> int:
        if self._statement_too_old(stmt):
            log.info("Skipping old statement from %s: %s", stmt.source_id, stmt.source_url)
            return 0

        normalized = normalize_quote(stmt.statement_text)
        q_hash = quote_hash(stmt.statement_text)
        nq_hash = normalized_quote_hash(stmt.statement_text)
        statement_id = self.db.store_statement(stmt, normalized, q_hash, nq_hash)

        entities = self.extractor.extract(stmt.statement_text)
        if not entities:
            log.info("No clear direct entity mapping: %s", stmt.statement_text[:160])
            return 0

        signal = classify_signal(stmt.statement_text)
        alerts_sent = 0
        for entity in entities:
            self.db.store_entity(statement_id, entity)
            decision = self._decide(stmt, entity, signal, normalized)
            if not decision.should_send:
                log.info("No alert: %s", decision.reason)
                continue

            alert_key = f"alert:{decision.duplicate_key}"
            if self.db.dedupe_exists(alert_key):
                log.info("Duplicate alert skipped for key %s", decision.duplicate_key)
                continue
            if self.db.recent_similar_alert_exists(stmt.speaker_name, entity.ticker, signal.signal, normalized):
                log.info("Similar recent alert skipped for %s %s %s", stmt.speaker_name, entity.ticker, signal.signal)
                continue

            text = build_market_alert_text(stmt, entity, signal, decision.lane, decision.reason)
            message_id = ""
            telegram_sent = False
            try:
                message_id = self.telegram.send_text(text)
                telegram_sent = True
                alerts_sent += 1
            except Exception as exc:
                # Do not mark alert as deduped if Telegram failed. A later run should retry.
                log.exception("Telegram send failed; alert will not be deduped: %s", exc)
                raise RuntimeError("Telegram delivery failed") from exc

            if telegram_sent:
                self.db.store_alert(statement_id, stmt, entity, signal, decision.lane, decision.duplicate_key, decision.reason, True, message_id)
                self.db.mark_dedupe(alert_key, "alert")

            if self.discord.enabled:
                try:
                    self.discord.send_text(text)
                except Exception:
                    log.exception("Discord send failed")
        return alerts_sent

    def _statement_too_old(self, stmt: Statement) -> bool:
        if stmt.is_live or self.settings.max_statement_age_hours <= 0:
            return False
        published = stmt.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - published.astimezone(timezone.utc)).total_seconds() / 3600
        return age_hours > self.settings.max_statement_age_hours

    def _decide(self, stmt: Statement, entity, signal, normalized_text: str) -> AlertDecision:
        duplicate_key = alert_duplicate_key(stmt, entity, signal)

        if entity.direct_or_inferred != "direct":
            return AlertDecision(False, "none", "Entity is inferred, not a direct mention.", duplicate_key, entity, signal)
        if signal.signal not in {"Good", "Bad"}:
            return AlertDecision(False, "none", f"Signal is {signal.signal}, not strong good/bad.", duplicate_key, entity, signal)
        if entity.entity_confidence < 0.95:
            return AlertDecision(False, "none", f"Entity confidence {entity.entity_confidence:.2f} is below 0.95.", duplicate_key, entity, signal)

        if stmt.is_live:
            if not self.settings.enable_provisional_live_alerts:
                return AlertDecision(False, "none", "Live provisional alerts are disabled.", duplicate_key, entity, signal)
            if stmt.source_confidence < self.settings.live_min_source_confidence:
                return AlertDecision(False, "none", "Live source confidence below threshold.", duplicate_key, entity, signal)
            if stmt.speaker_confidence < self.settings.live_min_speaker_confidence:
                return AlertDecision(False, "none", "Live speaker confidence below threshold.", duplicate_key, entity, signal)
            if stmt.quote_confidence < self.settings.live_min_quote_confidence:
                return AlertDecision(False, "none", "Live quote confidence below threshold.", duplicate_key, entity, signal)
            reason = f"Live provisional direct {signal.signal.lower()} statement about {entity.mapped_name}; verify timestamp {stmt.transcript_timestamp or 'unknown'}."
            return AlertDecision(True, "live_provisional", reason, duplicate_key, entity, signal)

        min_conf = self.settings.min_strict_confidence
        checks = [
            (stmt.source_confidence, "source"),
            (stmt.speaker_confidence, "speaker"),
            (stmt.quote_confidence, "quote"),
            (signal.confidence, "signal"),
        ]
        for value, name in checks:
            if value < min_conf:
                return AlertDecision(False, "none", f"{name} confidence {value:.2f} below {min_conf:.2f}.", duplicate_key, entity, signal)

        reason = f"Direct high-confidence {signal.signal.lower()} statement about {entity.mapped_name}."
        return AlertDecision(True, "strict", reason, duplicate_key, entity, signal)
