from __future__ import annotations

import logging

from alerts.discord import DiscordClient
from alerts.telegram import TelegramClient, build_market_alert_text
from config import Settings, load_asset_map
from database.db import Database, hash_text
from database.models import Statement, AlertDecision
from dedupe import normalize_quote, quote_hash, normalized_quote_hash, platform_key, alert_duplicate_key
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
        normalized = normalize_quote(stmt.statement_text)
        q_hash = quote_hash(stmt.statement_text)
        nq_hash = normalized_quote_hash(stmt.statement_text)

        statement_id = self.db.store_statement(stmt, normalized, q_hash, nq_hash)

        # Pre-alert dedupe only for the same platform item/post.
        # Do not dedupe by quote here, because a weak source may see a quote first
        # and a stronger verified source may confirm it later. Final alert dedupe
        # happens only after an alert passes all filters.
        if stmt.platform_item_id and self.db.dedupe_seen(platform_key(stmt), "platform_item"):
            log.info("Duplicate platform item skipped: %s", stmt.platform_item_id)
            return 0

        entities = self.extractor.extract(stmt.statement_text)
        if not entities:
            log.info("No clear direct entity mapping: %s", stmt.statement_text[:160])
            return 0

        signal = classify_signal(stmt.statement_text)
        alerts_sent = 0
        for entity in entities:
            self.db.store_entity(statement_id, entity)
            decision = self._decide(stmt, entity, signal)
            if not decision.should_send:
                log.info("No alert: %s", decision.reason)
                continue
            if self.db.dedupe_seen(f"alert:{decision.duplicate_key}", "alert"):
                log.info("Duplicate alert skipped for key %s", decision.duplicate_key)
                continue
            text = build_market_alert_text(stmt, entity, signal, decision.lane, decision.reason)
            message_id = ""
            telegram_sent = False
            try:
                message_id = self.telegram.send_text(text)
                telegram_sent = True
                alerts_sent += 1
            except Exception as exc:
                log.exception("Telegram send failed: %s", exc)
            if self.discord.enabled:
                try:
                    self.discord.send_text(text)
                except Exception:
                    log.exception("Discord send failed")
            self.db.store_alert(statement_id, stmt, entity, signal, decision.lane, decision.duplicate_key, decision.reason, telegram_sent, message_id)
        return alerts_sent

    def _decide(self, stmt: Statement, entity, signal) -> AlertDecision:
        duplicate_key = alert_duplicate_key(stmt, entity, signal)

        if entity.direct_or_inferred != "direct":
            return AlertDecision(False, "none", "Entity is inferred, not a direct mention.", duplicate_key, entity, signal)
        if signal.signal not in {"Strong Bullish", "Strong Bearish"}:
            return AlertDecision(False, "none", f"Signal is {signal.signal}, not strong bullish/bearish.", duplicate_key, entity, signal)
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
