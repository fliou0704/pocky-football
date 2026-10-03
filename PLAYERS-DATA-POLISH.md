# Focused Players/data polish

## Scope and resulting behavior

Game Log now uses a full regular NFL season (Weeks 1–18 for the covered 2021–2026 seasons), rather than each fantasy schedule's week set. The ESPN actual playercard request asks for all 18 weeks and preserves the full NFL schedule, weekly production and fantasy points in `player-games.json` schema 2. Fantasy scoring contracts still use their original matchup weeks; Record Book and other pages are unchanged. BYE rows remain explicit. Recent Games is current-season-only and newest first; Complete Game Log runs Week 1 through Week 18.

Career's fantasy GP/FPTS/FPPG now use completed active-slot fantasy starts. Bench/IR rows and NFL-only weeks are excluded. A completed fantasy start counts even if the started player did not participate in the NFL game; its actual fantasy zero remains a zero. FPPG divides started fantasy points by those starts. Position-specific NFL totals independently aggregate the full NFL regular season. A short table note distinguishes these scopes.

## Why participation was undetermined

The previous implementation required stat 210 (GP) or an explicit athlete event-log flag, and otherwise left empty actual records unresolved. It also depended on fantasy-week completion and fantasy-limited schedules. This missed supported Did Not Play cases and omitted NFL-only weeks.

The revised classification uses the actual NFL event ID before inferred team identity, the complete NFL schedule, kickoff, official stat availability and actual NFL production. Explicit played flags or nonzero production prove Played; completed NFL events with an empty matching actual record establish Did Not Play. Missing weekly records also establish Did Not Play when a full 18-week actual-season response covers that player; absent historical player/team evidence remains Unknown. BYE requires a known team's complete schedule with no game. Future/unfinished games without actual participation show Upcoming. No injury reasons are inferred.

NFL completion is independent of fantasy matchup completion. One historical event had no NFL production anywhere in the player pool: Buffalo–Cincinnati, 2022 Week 17. ESPN's event status endpoint explicitly reports `STATUS_CANCELED`, `completed=false`; it is represented as Did Not Play, including for D/ST. The status probe runs only for past events lacking all NFL stat evidence, and caches an allowlisted name/completion flag.

Unknown rows fell from 462 in the previous fantasy-limited snapshot to 18 in the expanded 27,864-row full-season contracts. All 18 remaining rows are Odell Beckham Jr.'s 2022 season: no usable historical NFL team/actual-season records, and the public ESPN event-log response supplies no events detail. Those NFL totals remain unavailable; fantasy starts are independently known from audited lineups.

## Actual transaction direction audit

Authenticated ESPN executed playercard transactions were inspected for all six seasons. Only allowlisted source movement fields were retained in ignored local audit caches; no credentials, members or pending claims were published.

Observed semantics:

| Item | fromTeamId | toTeamId | Meaning |
| --- | --- | --- | --- |
| ADD | 0 | fantasy team | Acquisition from free-agent pool |
| DROP | fantasy team | 0 | Release into free-agent pool |
| TRADE | sending team | receiving team | Transfer |
| DRAFT | 0 | drafting team | Draft selection |

The actual raw free-agent destination was `0`, not a reversed direction. Null destinations are also safely ignored as fantasy teams. Existing `football_activity.normalize_transaction` already mapped these movements correctly. Comparison against checked-in activity events found **zero direction discrepancies in 2,108 matching raw events**.

The bug was in `football_players.py`: each player's transaction copied the parent event type. A combined waiver/free-agent acquisition includes one added player and a different dropped player; the latter incorrectly displayed “Added by” with an empty destination. The new per-player classification treats a from-only movement as Drop, preserves waiver/free-agent labels for to-only acquisitions, and preserves sending/receiving teams for trades. All player contracts were regenerated. Activity contracts required no direction rewrite and their completeness semantics were preserved.

| Season | Raw events matched | Direction discrepancies | Bundled drops corrected |
| --- | ---: | ---: | ---: |
| 2021 | 370 | 0 | 127 |
| 2022 | 464 | 0 | 145 |
| 2023 | 361 | 0 | 109 |
| 2024 | 388 | 0 | 168 |
| 2025 | 343 | 0 | 125 |
| 2026 | 182 | 0 | 13 |
| Total | 2,108 | 0 | 687 |

Human-readable examples verified in contracts/browser: Adam Thielen drafted in 2024 (Round 13, Overall Pick 128), dropped by For Kyren Out Loud on Sep 27, then added by Team Liou via Waivers on Nov 6; Richie James free-agent acquisition in 2022; Davante Adams transferred from Tee Time to semanto gay and kissed allen in 2024. No add rows have empty destinations or drop rows have empty origins across any generated season.

## Files and validation

Changes: NFL normalization/generation in `football_player_games.py`, shared playercard fetching in `football_player_scoring.py`, contract migration in `football_exporter.py`, per-player transactions and starts in `football_players.py`, six full NFL contracts and 539 player profiles, Complete Game Log ordering and Career scope note in `PlayersPage.jsx`, targeted Python/React tests, and the bounded game-status Actions cache.

86 Python tests, 26 Node helper tests and 11 React tests pass. Targeted checks cover non-fantasy NFL Week 18, chronological full logs and descending recents, active-slot starts/bench/IR exclusions, GP/FPPG, BYE/Did Not Play/Upcoming, empty/absent actual records, genuine Unknown, canceled D/ST, raw drop-to-free-agent semantics, bundled drops and add/drop/trade directions. Production build passes under `/pocky-football/`; browser checks cover actual historical Week 18 and corrected transactions, plus a 320px mobile layout without document overflow.

Publication uses a feature PR into main and the existing Pages workflow; final PR/deployment and live verification are reported in the completion message.
