# Public-Figure Coverage Report

Last review: 2026-07-23 00:05 UTC

This report records verified repo coverage and shadow-only candidate discovery. It does not claim complete global coverage.

## Actions Check

- Public Actions page showed the latest visible public-figure workflow run as "Public figure scan - schedule - run #251", triggered July 16, 2026 16:46, conclusion Success.
- The latest visible manual workflow run was "Manual run all scanners - workflow_dispatch - run #5", triggered July 16, 2026 13:33, conclusion Success.
- No workflow was dispatched during this coverage-only run.
- No live stock scan was started.
- No Telegram test or market alert was sent.

## Repository Coverage Reviewed

- Active watchlist files reviewed: `watchlist.yaml`, `config/watchlist_extra.yaml`.
- Active entries observed by configuration inspection: 38.
- Active source types observed: `truthsocial`, `x_api`, `rss`, `youtube_rss`, `live_audio`.
- Supplemental asset maps reviewed: `config/asset_map.yaml`, `config/asset_map_extra.yaml`.
- Dedicated cursor registry discovered: none.
- Dedicated source-failure registry discovered: none.
- Existing coverage report discovered before this run: none.

## Active Coverage Observed

Countries and regions represented by active configuration:

- United States
- Taiwan

Categories represented by active configuration:

- Political leader
- Treasury / finance official
- Central banker
- Regulator
- Trade, commerce and energy policy official
- Mega-cap CEO
- Semiconductor, AI, cloud, data-center and crypto leader
- Bank CEO
- Investor / fund manager
- Official policy feed bundle

## Candidates Added

The following people were added only to `config/public_figure_registry.yaml` as `Candidate`, not to the scanner watchlist:

- Christine Lagarde, European Central Bank, euro area central-bank policy.
- Andrew Bailey, Bank of England, UK monetary policy and banking regulation.
- Kazuo Ueda, Bank of Japan, Japanese monetary policy.
- Pan Gongsheng, People's Bank of China, China monetary policy and FX.
- Ursula von der Leyen, European Commission, EU trade, energy, antitrust, chips and defense policy.
- Haitham Al Ghais, OPEC, oil-market policy.
- Amin H. Nasser, Aramco, oil and energy-sector statements.
- Sam Woods, Bank of England / PRA, bank and insurance regulation.

These are shadow candidates because identity, role and official sources are documented, but parser compatibility, stable IDs, cursor behavior and source-specific dedupe are not yet validated end to end.

## Source Findings

- Official-source priority remains the right default: central-bank, regulator, government, OPEC and company pages should rank above aggregation.
- Google News RSS is useful for discovery but should remain lower-confidence corroboration unless the underlying linked source is direct and verifiable.
- X sources must use the official API only and require `X_BEARER_TOKEN`; no scraping fallback should be added.
- Truth Social handling is already conservative: blocked or unavailable public access returns no statements instead of bypassing access controls.
- Live audio remains optional and provisional; this run did not enable or test live collection.

## Asset Mapping Findings

- Existing maps already include ambiguity controls for Apple fruit, Amazon place, Meta as a general word, Marvel versus Marvell, X, gold as non-market color/context, and oil outside market context.
- No new asset mapping was activated in this run.
- Highest-priority mapping gaps before activating worldwide candidates are non-US share classes, European bank/sector proxies, Japan equity/FX proxies, China offshore/onshore ambiguity and OPEC/oil proxy policy.

## Highest-Priority Gaps

- Add a real source-health registry with last success, last failure, HTTP/status class, parser class and stale-content detection.
- Add persistent per-source cursors using stable post, video, article, speech or timestamp IDs.
- Promote worldwide candidates only after source parser tests prove official ownership, timestamps, stable IDs, pagination, rate limits and dedupe behavior.
- Expand countries beyond the current U.S./Taiwan active footprint in controlled batches: euro area, UK, Japan, China, EU policy, OPEC and Saudi energy first.
- Keep all additions shadow-only unless they meet activation policy in `config/public_figure_registry.yaml`.

## Rollback

This run adds only shadow documentation and tests. Rollback is to remove:

- `config/public_figure_registry.yaml`
- `docs/COVERAGE_REPORT.md`
- `tests/test_public_figure_registry.py`
