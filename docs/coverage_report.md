# Public-Figure and Source Coverage Report

Last verification time: 2026-07-18T00:12:19Z
Run type: documentation-only scheduled maintenance audit
Alert policy: unchanged
Telegram: not used
Stock scans: not run
Cron changes: none

## Scope and safety

This report expands, verifies, and documents worldwide public-figure/source coverage only. It does not activate new people, weaken alert rules, evaluate profitability, run live stock scans, or send Telegram market alerts.

Coverage here is not complete global coverage. It records only the people, countries, categories, sources, and gaps reviewed during this audit.

## GitHub Actions status

Requested pre-check: check whether an equivalent job was queued or running, then use workflow_dispatch rather than adding cron.

Result:
- Could not inspect queued/running Actions from this execution environment. The local GitHub CLI was unavailable and unauthenticated/public Actions API requests returned HTTP 403.
- No workflow_dispatch was started because the available connector tools did not expose Actions run/dispatch operations and duplicate-run state could not be verified.
- No cron trigger was added.

Workflow files inspected on `main`:
- `.github/workflows/stable-monitor.yml`: workflow_dispatch only; public-figure scan; Telegram delivery secrets required by workflow; no schedule block present.
- `.github/workflows/hourly-stock-scan.yml`: workflow_dispatch only; stock scan workflow; not run.
- `.github/workflows/stock-candidate-refresh.yml`: workflow_dispatch only; silent stock candidate workflow; not run.
- `.github/workflows/telegram-test.yml`: workflow_dispatch only; exact test message preserved; not run.

Pre-existing test/config mismatch:
- `tests/test_workflows.py` still expects cron schedules and a daily Telegram test schedule.
- The latest repository history includes `Make operational workflows manual-only` and `Remove operational scan cron triggers`, so this audit did not restore cron.

## Current code-enforced status model

The requested statuses are: `Active`, `Candidate`, `Unavailable`, `Stale`, `Disabled`, `Rejected`.

Current repo behavior observed:
- `watchlist.yaml` does not yet contain explicit `status` or machine-readable non-active reason fields.
- Runtime activation is currently inferred from `enabled: true` and `allow_telegram_alerts: true` in `sources.factory.build_monitors`.
- SQLite `watched_people` stores id, name, aliases, role, market_impact_score, and enabled only. It does not persist status, country, organization, role dates, source priority metadata, identity/source confidence, verification timestamps, or non-active reasons.

Recommended safe next implementation, not made in this PR:
- Add registry metadata fields in a backward-compatible way.
- Treat missing `status` as current legacy behavior.
- Add tests for `Candidate`, `Unavailable`, `Stale`, `Disabled`, and `Rejected` entries staying silent.

## Existing active people reviewed

The current `watchlist.yaml` contains 22 code-enabled public figures. Because the registry has no explicit status field, these are listed as code-active rather than newly verified under the requested status schema.

| Person | Current watchlist role/category | Country/region represented | Primary configured sources | Audit status | Notes |
| --- | --- | --- | --- | --- | --- |
| Donald J. Trump | U.S. President / political market mover | United States | Truth Social, X API, White House/news, YouTube, Google News RSS, RSBN live | Active by code | Official White House page found. Truth Social/X need source-specific runtime verification. |
| Kevin Warsh | Federal Reserve Chair / central bank market mover | United States | Federal Reserve/news, Google News RSS | Active by code | Federal Reserve biography states he took office as chair on 2026-05-22 and FOMC chair. |
| Scott Bessent | U.S. Treasury Secretary | United States | Treasury press releases, Google News RSS | Active by code | Treasury official page and press release identify him as 79th Treasury Secretary, sworn in 2025-01-28. |
| Elon Musk | Tesla CEO / technology and crypto market mover | United States/global | Tesla profile, X API, Google News RSS | Active by code | Tesla official profile identifies him as co-founder and CEO. X source requires token. |
| Jensen Huang | NVIDIA founder/CEO | United States/global | NVIDIA profile, Google News RSS | Active by code | NVIDIA newsroom profile identifies him as founder and CEO. |
| Jerome Powell | Federal Reserve Board member / former Fed Chair | United States | Federal Reserve/news, Google News RSS | Active by code | Federal Reserve page says chair term ended 2026-05-22; role should be reviewed to avoid stale `Fed Chair` aliases if present elsewhere. |
| Christopher Waller | Federal Reserve Governor | United States | Google News RSS | Active by code | Needs official Federal Reserve biography URL in registry for stronger source priority. |
| Michelle Bowman | Federal Reserve Governor | United States | Google News RSS | Active by code | Needs official Federal Reserve biography URL in registry for stronger source priority. |
| Neel Kashkari | Minneapolis Fed President | United States | Google News RSS | Active by code | Needs official Minneapolis Fed profile/feed in registry. |
| Austan Goolsbee | Chicago Fed President | United States | Google News RSS | Active by code | Needs official Chicago Fed profile/feed in registry. |
| Jamie Dimon | JPMorgan Chase CEO | United States/global | Google News RSS | Active by code | Needs official JPMorgan leadership/newsroom source before treating as original-source coverage. |
| David Solomon | Goldman Sachs CEO | United States/global | Google News RSS | Active by code | Needs official Goldman Sachs leadership/newsroom source before treating as original-source coverage. |
| Brian Moynihan | Bank of America CEO | United States/global | Google News RSS | Active by code | Needs official Bank of America leadership/newsroom source before treating as original-source coverage. |
| Satya Nadella | Microsoft chairman/CEO | United States/global | Google News RSS | Active by code | Microsoft Source profile identifies him as chairman and CEO. |
| Sundar Pichai | Alphabet/Google CEO | United States/global | Google News RSS | Active by code | Needs official Alphabet/Google leadership/newsroom source in registry. |
| Tim Cook | Apple CEO | United States/global | Google News RSS | Active by code | Needs official Apple leadership/newsroom source in registry. |
| Mark Zuckerberg | Meta founder/CEO | United States/global | Google News RSS | Active by code | Public official Meta/Facebook profile found in search, but registry needs durable official newsroom/profile URL. |
| Sam Altman | OpenAI CEO / AI leader | United States/global | X API, Google News RSS | Active by code | X source requires token; OpenAI official source/feed should be preferred when available. |
| Lisa Su | AMD CEO | United States/global | Google News RSS | Active by code | Needs official AMD leadership/newsroom source in registry. |
| Michael Saylor | MicroStrategy/Strategy founder / Bitcoin market mover | United States/crypto | X API, Google News RSS | Active by code | X source requires token; company/investor-relations sources should be added before original-source activation. |
| Cathie Wood | ARK Invest CEO / investor | United States/global | X API, Google News RSS | Active by code | X source requires token; official ARK source/feed should be preferred. |
| Bill Ackman | Pershing Square CEO / investor | United States/global | X API, Google News RSS | Active by code | X source requires token; official Pershing source/feed should be preferred. |

## Worldwide candidates discovered for future registry expansion

No candidate below was activated in this PR. All should remain `Candidate` until identity, role, official sources, asset relevance, parser compatibility, and alert-silence tests are implemented.

| Candidate | Country/region | Category | Official evidence reviewed | Plausible market relevance | Proposed status | Machine-readable reason |
| --- | --- | --- | --- | --- | --- | --- |
| Christine Lagarde | Euro area | central_bank | ECB official CV: President of the ECB since Nov. 2019; ESRB chair; BIS/G7/G20 roles. | EUR rates, European equities, banks, bonds, euro, gold/dollar sensitivity. | Candidate | `verified_role_but_not_configured` |
| Kazuo Ueda | Japan | central_bank | Bank of Japan official governor page. | JPY, Japanese equities, rates, banks, global carry-trade sensitivity. | Candidate | `verified_role_but_not_configured` |
| Andrew Bailey | United Kingdom | central_bank | Bank of England official biography; appointment 2020-03-16 to 2028-03-15. | GBP, gilt yields, UK banks, FTSE, crypto/stablecoin regulation. | Candidate | `verified_role_but_not_configured` |
| Paul S. Atkins | United States | regulator | SEC official page; sworn in as 34th SEC Chair on 2025-04-21. | Securities regulation, crypto, ETFs, broker/dealer and exchange sectors. | Candidate | `verified_role_but_not_configured` |
| Ursula von der Leyen | European Union | government/trade/defense | European Commission president page; second mandate through 2029. | Trade, tariffs, defense industrial policy, autos, energy, EU equities. | Candidate | `verified_role_but_not_configured` |
| Xi Jinping | China | government/technology/trade | Official/public Chinese state sources and public reporting identify him as President/CCP General Secretary. | China equities, semiconductors, AI, trade, commodities, global risk assets. | Candidate | `official_source_model_needs_careful_review` |
| Prince Abdulaziz bin Salman | Saudi Arabia | energy_official | Saudipedia/official public profile found; Minister of Energy since 2019-09-08. | Oil, energy equities, OPEC policy, inflation expectations. | Candidate | `verified_role_needs_original_feed` |
| Haitham Al Ghais | OPEC | energy_official | OPEC official Secretary General page/PDF biography. | Oil, energy equities, inflation expectations. | Candidate | `verified_role_needs_parser_test` |

## Countries and categories represented

Currently represented by code-enabled watchlist entries:
- Countries/regions: United States/global only, with some global-market CEOs/investors.
- Categories: political leader, treasury, central bank, bank CEO, mega-cap technology CEO, AI leader, semiconductor CEO, crypto leader, investor.

Reviewed but not activated in this audit:
- Euro area, Japan, United Kingdom, European Union, China, Saudi Arabia, OPEC.
- Categories: central bankers, securities regulator, trade/government leader, energy officials.

Highest-priority gaps:
- Non-U.S. central banks: ECB, BoJ, BoE, PBoC, SNB, Bank of Canada, Reserve Bank of Australia.
- Energy/trade officials: Saudi Energy Ministry, OPEC, U.S. Trade Representative, EU trade/competition officials, China commerce/foreign ministry sources.
- Regulators: SEC, CFTC, ESMA, FCA, MAS, Hong Kong SFC.
- Defense and semiconductor policy leaders: U.S. Commerce/export-control officials, Taiwan and Netherlands semiconductor policy sources.
- Original company sources for current CEO/watchlist entries that rely mostly on Google News RSS.

## Source adapter audit

Configured source types supported by code:
- `rss`: parsed with `feedparser`, first 20 entries, title + summary, entry id/link used for dedupe. Quote confidence is 0.70 and speaker confidence is 0.75, so these should not send strict verified Telegram alerts by themselves.
- `youtube_rss`: parses official YouTube channel RSS, tries public transcript API if available, uses video id for dedupe. Title-only entries have low quote confidence.
- `x_api`: uses official X API only. If `X_BEARER_TOKEN` is empty or API returns 401/403/429, it returns no statements and does not scrape or bypass access.
- `truthsocial`: best-effort public HTML/JSON only. Blocks 401/403/404 without bypass. HTML fallback has low quote confidence.
- `live_audio`: optional only when `ENABLE_LIVE_AUDIO=true`; requires `yt-dlp`, `ffmpeg`, and `faster-whisper`; provisional confidence only.

Source quality findings:
- Google News RSS is not an original source. It is useful for discovery and quote leads, but configured confidence values should keep it below strict alert thresholds.
- X sources are original only when authenticated through official API and matched to verified account usernames.
- YouTube source IDs are stable by video id; transcript availability controls quote confidence.
- Truth Social public HTML fallback lacks stable post IDs and timestamps unless JSON status data is available; keep strict alerting blocked unless stable IDs/timestamps are obtained.
- Live audio has cursor/dedupe via video id + live offset, but transcript confidence is provisional.

Unavailable or unverified source checks in this run:
- Direct HTTP checks from the container to public official sites returned no HTTP status (`000`) because outbound network access was restricted.
- GitHub Actions queued/running status could not be checked due unavailable local GitHub CLI and HTTP 403 from unauthenticated Actions API.
- No source failure table from production SQLite was available in this execution environment.

## Asset mapping audit

Reviewed `config/asset_map.yaml` and `nlp/ticker_mapper.py`.

Existing confirmed safeguards:
- Apple fruit contexts are avoided for `AAPL`.
- Amazon rainforest/river/jungle contexts are avoided for `AMZN`.
- `Meta` alone is blocked as ambiguous unless `Meta Platforms`, `Facebook`, or ticker `META` appears.
- `Marvel` is blocked to avoid confusing Marvel content with Marvell Technology (`MRVL`).
- `X` alone is blocked as too ambiguous.
- Gold and oil require market/commodity context and avoid ordinary contexts such as color, medal, cooking oil, and painting.

No asset mappings were added or changed in this audit.

Potential mapping follow-ups, not changed here:
- Add tests proving `Marvel` blocks all mappings even if `Marvell Technology` is absent.
- Add tests proving sector mappings require market context where configured.
- Review `Strategy` as an alias for MicroStrategy because ordinary usage is common; current avoid contexts reduce but may not eliminate ambiguity.

## Source failures and cursors

Runtime persistence observed:
- `source_state` records last checked, last success, last error, run count, and failure count.
- `dedupe_keys`, `raw_statements.platform_item_id`, normalized quote hashes, and alert duplicate keys provide dedupe coverage.

Gaps:
- No per-source collection cursor table beyond source state and dedupe keys.
- No registry-level last verification timestamp or official-source verification timestamp.
- No machine-readable quarantine reason for stale/unavailable/rejected people.
- No production SQLite snapshot was available here to inspect current source failures.

## Prioritized expansion order

Priority never lowers alert-confidence rules.

1. Add `Candidate` registry metadata and tests before enabling new people.
2. Add official original-source feeds for existing active people currently relying on Google News RSS.
3. Candidate: Christine Lagarde / ECB official speeches and press releases.
4. Candidate: Kevin Warsh/Fed official speeches, testimonies, FOMC materials, and source-specific stable IDs.
5. Candidate: Kazuo Ueda / BoJ speeches, statements, press conferences.
6. Candidate: Andrew Bailey / BoE speeches, news, testimony pages.
7. Candidate: Paul Atkins / SEC speeches, statements, press releases.
8. Candidate: energy officials with original OPEC/Saudi official sources and conservative quote parsing.
9. Candidate: EU trade/competition/commission sources where direct quote and context are available.
10. Candidate: China official sources only after parser, translation/context, and attribution reliability are explicitly tested.

## Changes made in this PR

Files changed:
- `docs/coverage_report.md` added.

No code/config behavior changed:
- No watchlist entries activated.
- No source adapters changed.
- No asset mappings changed.
- No strategy rules changed.
- No workflow cron added.
- No Telegram send attempted.
- No stock scan run.

## Validation performed

Repository inspection through GitHub connector:
- `watchlist.yaml`
- `config/asset_map.yaml`
- `.github/workflows/stable-monitor.yml`
- `.github/workflows/hourly-stock-scan.yml`
- `.github/workflows/stock-candidate-refresh.yml`
- `.github/workflows/telegram-test.yml`
- `pipeline.py`
- `scheduler.py`
- `config.py`
- `database/db.py`
- `database/models.py`
- `dedupe.py`
- `sources/factory.py`
- `sources/rss_monitor.py`
- `sources/youtube_monitor.py`
- `sources/x_monitor.py`
- `sources/truthsocial_monitor.py`
- `sources/live_audio_monitor.py`
- `nlp/ticker_mapper.py`
- `tests/test_workflows.py`

Tests:
- Not run locally because the repository could not be cloned in this container; direct `git clone` failed with a CONNECT tunnel HTTP 403.
- Full suite is expected to fail until the pre-existing workflow test mismatch is resolved or tests are updated for manual-only workflows.

Rollback:
- Revert the documentation-only commit that adds `docs/coverage_report.md`.
