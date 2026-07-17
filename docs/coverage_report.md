# Public-Figure Coverage Report

Reviewed at: 2026-07-17 00:20 UTC

This run expanded and verified worldwide public-figure/source coverage only. It did not run live stock scans, evaluate profitability, change alert strategy, send Telegram, add cron, or activate any new live alert source.

## GitHub Actions

- `stable-monitor.yml`, `hourly-stock-scan.yml`, `stock-candidate-refresh.yml`, and `telegram-test.yml` exist and are `workflow_dispatch` only.
- The local environment could not query or dispatch GitHub Actions runs because direct GitHub network access and the GitHub CLI were unavailable in the container. No workflow was started from this run.
- The public-figure workflow remains concurrency-protected with `market-moving-public-figure-alert`.

## Existing Coverage Reviewed

Live watchlist files reviewed:

- `watchlist.yaml`
- `config/watchlist_extra.yaml`
- `config/asset_map.yaml`
- `config/asset_map_extra.yaml`

The current enabled coverage is strongest for United States policy figures, U.S. mega-cap/AI executives, U.S. bank executives, crypto investors, and several semiconductor/data-center leaders. Existing additive coverage already includes U.S. commerce/trade/energy/regulator entries and technology, semiconductor, banking, energy, and investor figures.

The scanner still uses strict alert gates in `pipeline.py`: direct entity mention, `Good` or `Bad`, confidence checks at or above the strict threshold, and duplicate checks before Telegram delivery.

## Worldwide People Verified

The shadow registry in `config/public_figure_registry_review.yaml` records verified identity, role, official source, market relevance, status, confidence, and collection cursor fields for these people:

| Person | Region | Category | Status | Primary verified source |
| --- | --- | --- | --- | --- |
| Christine Lagarde | European Union | central_bank | Active | ECB official speech page |
| Andrew Bailey | United Kingdom | central_bank | Active | Bank of England speeches page |
| Kazuo Ueda | Japan | central_bank | Active | Bank of Japan speeches/statements page |
| Pan Gongsheng | China | central_bank | Candidate | SAFE/PBOC official speech mirror and BIS author page |
| Ursula von der Leyen | European Union | government_policy | Candidate | European Commission Press Corner |
| Haitham Al Ghais | OPEC | energy_policy | Active | OPEC speeches page |
| Abdulaziz bin Salman Al Saud | Saudi Arabia | energy_policy | Candidate | OPEC Saudi Arabia member page |
| Amin H. Nasser | Saudi Arabia | energy_ceo | Active | Aramco leadership and speech pages |
| Christophe Fouquet | Netherlands | semiconductor_ceo | Active | ASML board and release pages |
| Richard Teng | Global crypto | crypto_leader | Candidate | Binance official company post |

Candidate entries are intentionally not enabled for live collection until parser/API behavior, stable IDs, rate limits, legal access, timestamps, cursor behavior, and duplicate handling are tested.

## Countries And Categories Represented

Verified in this run:

- Countries/regions: European Union, United Kingdom, Japan, China, OPEC, Saudi Arabia, Netherlands, global crypto.
- Categories: central bankers, government/trade/industrial policy, energy policy, energy CEOs, semiconductor CEOs, crypto leaders.

Existing repository coverage also includes the United States, Taiwan, major U.S. technology firms, U.S. bank CEOs, crypto investors, and AI infrastructure leaders.

## Source Review

Official or original sources verified for coverage planning:

- ECB official speech pages.
- Bank of England speeches page.
- Bank of Japan speeches/statements page.
- SAFE/PBOC official English speech page and BIS speech mirror for PBOC material.
- European Commission Press Corner.
- OPEC speeches and member pages.
- Aramco leadership and speeches pages.
- ASML board and press-release pages.
- Binance official company post pages.

Source issues not repaired in this run:

- The repo currently has an RSS/HTML feed collector but no confirmed general official-site HTML adapter for all verified government and company pages.
- X API sources require `X_BEARER_TOKEN` and were not tested.
- YouTube/live transcript sources require timestamp and duplicate-segment validation and were not tested.
- Some government/company pages are HTML lists without RSS and need source-specific selector tests before activation.

No broken source selector, timestamp parser, pagination, retry, rate-limit, cursor, or dedupe failure was confirmed from an executable run, so no source adapter code was changed.

## Asset Mapping Review

Reviewed mapping files:

- `config/asset_map.yaml`
- `config/asset_map_extra.yaml`

No asset mapping was changed in this run. Existing ambiguity blocks already cover key false-positive risks including Apple fruit, Amazon place context, ordinary Meta usage, Marvel versus Marvell, X ambiguity, gold color context, oil non-market context, ticker-only `F`, ticker-only `CAT`, and `ARM` ambiguity.

Potential future mappings should remain evidence-backed and should not be added until legal company name, exchange, ticker/share class, and contextual disambiguation are verified.

## Highest-Priority Gaps

1. Add a tested official-site HTML source adapter for central-bank, regulator, government, OPEC, and company speech/release pages with stable IDs, timestamp parsing, cursor recovery, redirect handling, and stale-content handling.
2. Add tests for the shadow registry schema: allowed statuses, required non-active reasons, confidence fields, source URLs, and no accidental `enabled: true` scanner activation.
3. Add regional coverage for Canada, Australia, India, Brazil, Mexico, South Korea, Singapore, UAE, Qatar, Germany, France, Italy, and major African economies using official central-bank, finance-ministry, energy, regulator, and company sources.
4. Test legal access and cursor behavior for official social accounts before adding more X, YouTube, LinkedIn, or podcast sources.
5. Keep direct-asset and ambiguity tests ahead of any activation for broad government leaders whose statements may be political but not directly tradable.

## Rollback

This change is additive and shadow-only. Roll back by removing:

- `config/public_figure_registry_review.yaml`
- `docs/coverage_report.md`

No live scanner config, Telegram settings, workflows, source adapters, alert rules, or stock scanner files were changed.
