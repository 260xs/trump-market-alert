# Design

## Pipeline order

1. Collect public statement.
2. Verify source.
3. Verify speaker.
4. Normalize quote.
5. Check duplicate.
6. Extract entities.
7. Map entity to ticker/asset.
8. Check directness.
9. Classify sentiment.
10. Check confidence thresholds.
11. Send Telegram only if rules pass.
12. Store everything in SQLite.
13. Log result.

## Alert lanes

### Strict alert

Strict alerts are for verified text sources, official posts, transcripts, and public RSS items.

### Live provisional alert

Live provisional alerts are optional. They use public livestream audio sampling and speech-to-text. They are never treated as fully verified. They include an approximate timestamp and are clearly labeled as provisional.

## Why live alerts are separate

Live audio transcription can mishear words. Instead of mixing it with verified alerts, live alerts have their own threshold and label. This gives speed without pretending the quote is confirmed.
