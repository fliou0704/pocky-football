# Team + Record Book refinement

## Integration and scope

The historical audit was preserved as commit `6818b9b` on `codex/historical-activity-audit`. This feature branch, `codex/team-record-book-refinement`, starts from that commit and retains all audited activity tests and contracts. Basketball Brawl's current RecordBook.jsx and record-book.css were inspected as read-only visual references.

Team pages and Record Book are implemented. No standalone Players page, activity/trade-history UI, Home/H2H redesign, permanent franchise identity, or multi-league functionality was added.

## Contracts and files

- `football_record_book.py`: completed-season views, ranked awards, honors, position awards, matchup references, seven bench selections.
- `football_record_rankings.py`: deterministic ranking/ties, player-season scoring qualification and acquisition stints.
- `football_player_scoring.py`: compact actual weekly ESPN scoring and real NFL schedule/kickoff metadata needed where roster snapshots omit unrostered weeks.
- `football_exporter.py`: generates these scoring contracts; completed-season caches are reused, current-season scoring refreshes.
- `football_draft.py`: retains authoritative draft data and enriches real positions from normalized scoring metadata.
- Season `draft.json`: adds real player `position`; all 1,056 authoritative selections remain intact.
- Season `player-scoring.json`: numeric actual scores indexed by player/week, actual weekly NFL teams, safe NFL schedules and coverage. No ESPN account/member identifiers.
- Existing `lineups/*.json`: shared weekly files remain the single H2H/Record Book detail source. Fantasy points remain unchanged; weekly NFL teams are corrected from authoritative stat team IDs and opponents are added when unambiguous.
- `record-book.json` schema 2: completed `years`/`seasons`, ranked `leaders` with competition ranks, primary `holders`, limits and direct references into existing lineups.
- React: `TeamDraft.jsx`, shared `MatchupDetails.jsx`, reusable `RankedRecord`, updated Team hierarchy, award headers and completed-season selector.
- Tests: targeted backend calculations, generated contracts, frontend helpers and four real React interaction tests. Test-only Vitest/jsdom/Testing Library dependencies and locked versions are included.

## Team Draft

Overview remains visible above Schedule / Roster / Draft, with no intervening content. Draft follows the selected season and team ID; selection order uses ESPN overall picks. Round, pick within round, overall pick and real position are displayed. Tabs remain selected when switching seasons. A failed/missing draft has a clean unavailable state.

## Completion and rankings

Only `league.complete` seasons get individual Record Book entries and selector options. Currently those are 2021–2025. An invalid/in-progress year resolves to All-Time. All-Time finalized weekly records/streaks can include 2026. Regular-season aggregate records qualify only once all configured regular weeks are final; full-season player production requires the entire fantasy season to be complete.

Rankings are computed in Python. Weekly team/margin and All-Time player/position lists use Top 10; regular-season aggregates, streaks and pickups use Top 5. Individual player-season and weekly player/bench/position lists use Top 5. Exact ties receive competition ranks (1, 2, 2, 4); every entry tied at the nominal cutoff remains included. Equal records rank equally by exact win percentage, with ties counting half a win; season/week/team/player order only stabilizes display.

Lowest Team Score admits regular-season and championship-bracket games. Placement/third-place and losers-consolation games are excluded from this award because they are outside the championship path. They remain in the historical dataset and other appropriate awards. All matchup awards require final numeric scores and exclude byes/self games. True ties are zero-margin closest matchups.

Each award has its own Basketball Brawl-style section heading. One reusable ranked component handles primary holder, Top N expansion, and one open matchup detail per list. H2H and Record Book import the same lineup component, use the same slot ordering, and read the same historical files. There is no duplicated set of weekly lineups.

## Player scoring

Weekly player awards use actual numeric stored lineup points. General player awards omit fantasy slot; bench awards require BE/BN. Position awards use real player position, including FLEX occupants under RB/WR/TE. Negative-point entries preserve the existing starter eligibility while excluding all D/ST. NFL opponents are displayed only where the actual weekly NFL team maps to exactly one scheduled NFL game.

Highest Scoring Player in a Season replaces Highest Starter Score. It sums the source's unique numeric actual player/week values over the league's configured fantasy weeks, including playoffs/consolation and all roster statuses, without depending on fantasy ownership. It includes scores from unrostered weeks and excludes trailing NFL weeks. All historical leagues here use fantasy weeks 1–17.

Qualification is conservative: numeric actual coverage for every scheduled NFL game in those weeks, allowing an explicitly established NFL bye. Missing played-week values exclude the player-season rather than becoming invented zeros. Multiple source values for one player/week must agree. NFL team display comes from the season's actual stat team IDs, including multiple NFL teams if represented.

| Season | Players with weekly data | Qualified player-seasons |
|---|---:|---:|
| 2021 | 935 | 686 |
| 2022 | 817 | 600 |
| 2023 | 790 | 602 |
| 2024 | 773 | 581 |
| 2025 | 784 | 589 |

**Historical limitation:** these are rankings of sufficiently covered player-seasons. Some inactive/partial careers and missing played-week records cannot qualify. For example, the 2022 source does not provide Josh Allen's week 17 numeric actual score; its schedule does not supply a reliable canceled-game marker. That player-season is excluded rather than assigning a guessed zero. This limitation is recorded here and in machine-readable coverage, with no explanatory clutter on the page.

## Best Pickup

Completed-season awards accept audited `free_agent_add` and `waiver_add` events only. Each acquisition creates its own stint; drops and outgoing trades close it. Draft/trade arrivals never count as pickups. Each numeric weekly performance is credited only if the acquiring team held the player at the actual NFL kickoff: acquisition timestamp ≤ kickoff < drop/trade timestamp. This also handles Thursday games, late-week additions and reacquisitions. Points count on bench/IR as well as in starting slots. Missing played-week scores within a stint prevent that stint from qualifying. The audited `likely_complete` or independently verified movement coverage is required. All five completed seasons have eligible Top 5 awards.

Rows preserve the exact source acquisition event, waiver/free-agent type, timestamp/week, nullable FAAB, acquiring team and credited weeks. FAAB stays null for these non-FAAB leagues.

## All-Fantasy Team

Existing MVP/All-Fantasy scoring philosophy remains regular-season **starter contributions**. Nine starters fill the observed QB/RB/RB/WR/WR/TE/FLEX/D/ST/K pattern. The seven highest-scoring remaining eligible players form Bench using the same contribution metric. No player repeats and no IR is selected. Equal selection scores use player-ID order, with starter tied alternatives preserved. Every completed season has 9 starters + 7 bench.

## Verification and delivery

- Python: 69 tests pass, preserving the audited pipeline suite and adding ranking, consolation, player-week deduplication, configured-week scope, pickup stint and generated-contract checks.
- Frontend helper tests: 22 pass.
- Real React interaction tests: 4 pass (rank expansion, exclusive/cached detail, player display, historical Team Draft and failure state, completed-season selector).
- Browser: real production preview checked Top 10, one open matchup per list, shared lineups, draft order and 2021→2022 switching while staying on Draft, 9+7 roster, and completed-season options.
- Mobile: 390px layout checked without horizontal overflow; shared lineups stack into one column.
- GitHub Pages production base `/pocky-football/`: build succeeds and asset/data paths load in the production preview.
- 15,265 stored lineup scores compared with the weekly scoring source; zero conflicts. 1,438 historical NFL-team labels corrected. Scores and fantasy ownership were preserved.
- Credentials remain environment-only; `.env` ignored; no authentication values or private member/account identifiers enter the generated contracts.

All requested award types are implemented with the coverage qualifications above. No publication, merge or deployment is performed by this refinement task; changes are reviewable on the feature branch. Players remains out of scope.
