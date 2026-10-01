# Stage 2E — Record Book and activity foundation

## Basketball Brawl inventory (current React implementation)

Inspected read-only: `frontend/src/RecordBook.jsx`, `frontend/src/record-book.css`, `frontend/scripts/generate_record_book.py`, public `record-book.json`, tests, the older Dash Record Book, and design system. Its sources are league weekly CSV, player matchup CSV, daily player CSV, activity CSV, and per-season roster metadata. The current frontend is the template; it uses an All-Time/year selector, championship timeline, stacked record cards, native expandable tables/award rankings, season champion/MVP cards, and an All-Fantasy roster. Mobile stacks content and keeps all details. Player links/headshots depend on its existing Players page.

| Basketball category | Classification | Football handling |
|---|---|---|
| Championship History / Season Champion | Directly applicable | Completed championship-bracket final winner, season-specific name/logo; current champion pending |
| Most Points in One Matchup (Team) | Directly applicable | Highest finalized team score, regular or playoffs |
| Most Points in One Matchup (Player) | Football calculation | Highest actual weekly rostered-player score, plus explicit starter and bench records |
| Most Points in One Day (Player) | Basketball-specific; omit | Football weekly records replace daily scoring |
| Players with 100+ Point Days and counts | Basketball-specific; omit | Weekly leaders and six position leaders replace the NBA daily threshold |
| Players with Negative Point Days and team counts | Football calculation | Expandable negative starter weeks table; includes all occurrences, no bench/IR |
| Top 10 Most Active Players (transactions) | Applicable but source-dependent; defer | Activity stored with qualified coverage; no transaction leaderboard |
| Season MVP | Football calculation | Most regular-season actual starter contributions; all tied leaders shown; current season to date |
| All-Fantasy Team | Football calculation | Season's most frequently observed starter-slot layout; greedily select highest starter-contribution player eligible by real position, unique player IDs, FLEX = RB/WR/TE. Ties choose player ID order and list alternate names. Bench award slots omitted: explicit weekly bench record is retained instead |
| Best Waiver Add | Applicable but source-dependent; defer | Needs verified complete acquisition/holding history |
| Best Draft Pick | Applicable but source-dependent; defer | Draft movements are stored; acquisition attribution/holding intervals not yet verified |
| Journeyman / Other Popular Players | Applicable but source-dependent; defer | No complete movement-history claim; cross-season team IDs do not establish permanent franchises |

Football adds lowest team score, largest margin, closest matchup, highest/lowest regular-season totals, best/worst regular-season record, and longest win/loss streaks. Six position leaders are one expandable table, not six extra sections. No Players page, Teams redesign, or Basketball Brawl changes.

## Record rules and contract

`football_record_book.py` reads existing `<season>/league.json`, `teams.json`, and shared `lineups/<week>.json`; it makes no ESPN calls. `record-book.json` contains `schemaVersion`, `years`, `defaultYear`, `allTime`, and `seasons`. Views contain `champions`, `teamRecords`, `playerRecords`, `positionRecords`, `negativeStarterWeeks`, `mvp`, `allFantasyTeam`, and coverage. Records contain ID/label, numeric value/unit/rule, and **all exact tied holders**. Holders preserve season-specific team identities, year/week or streak bounds, opponent, relevant scores, and player/NFL-team/position/slot where applicable. Ordering is deterministic by season/week/team/player/slot. The React page renders precomputed views, with filter state in `#/record-book[/<season>]`.

- Weekly team and player records: finalized regular-season **and playoff/consolation** matchups. Exclude byes, missing opponents, self-opponents, live/upcoming games and nonfinite scores.
- Closest matchup includes a genuine final tie as a zero margin. Largest victory excludes ties.
- Season totals: recompute from finalized **regular-season** games, exclude playoffs, and require the full scheduled regular season to be finalized. This can become eligible before the playoffs finish. Current 2026 full-season comparisons are empty, not compared against completed years.
- Best/worst regular records: exact win percentage `(wins + ties/2)/games`, using the actual season schedule, not a fixed team count. Exact fractions identify ties; UI also shows W–L–T and games.
- Streaks: within one season, **regular season only**, no cross-season identity assumption. Ties/unfinalized games interrupt. Byes never add a win/loss or extend the recorded end week. Basketball's current Record Book has no streak convention to inherit.
- Players: actual numeric points only. Individual/position records include all observed slots; starter records and MVP use actual starter slots; bench record uses BE/BN only, excludes IR. Missing points are excluded, never zero-filled. Current honors are explicitly to date. NFL labels come from archived ESPN metadata and may not preserve every midseason NFL team change.
- All-Fantasy awards use regular-season starter contributions only; they are an honors roster, not the current team roster. A player who moved fantasy teams retains every contributing fantasy team in the contract.
- Coverage lists missing weekly lineup data and missing player points. Actual snapshots have all required weekly files, but some historical player rows have no actual stat total (often inactive/IR); these are omitted from numeric records.

## Activity findings from actual league 668411840

Tested 2026, 2025, 2021, then generated all supported seasons. Source authentication stays in Python/environment variables. `recent_activity()` uses `kona_league_communication` under the league `/communication/` endpoint. Current 2026 returned 22 transaction topics, with adds, waivers and drops; default completed-season calls failed. A 5-topic page test at offsets 0, 5, 20, 25 returned 5, 5, 2, 0 topics without first/second-page overlap or truncated messages. Thus the current communication feed supports topic limits/offsets, but that does not establish a complete historical feed.

Alternative source verified directly:

`GET https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{leagueId}?view=mTransactions2&scoringPeriodId={period}`

Without explicit periods, completed-season `mTransactions2` returned no transactions. With periods it returned historical draft, free-agent, waiver, drop/roster, and trade-status events. Sweep periods 0 through the maximum of ESPN `latestScoringPeriod` and `transactionScoringPeriod`: 0–19 in completed seasons, 0–4 in current 2026 at inspection. Period 18 in 2021 still had activity, so stopping at the fantasy final week 17 would miss data. Per-period samples returned up to 185 events; this is not limited to the recent-activity default 25. Naive numeric transaction limit/offset filters returned errors; no supported transaction pagination or independent total count was verified.

`kona_playercard`, through the installed package's `get_player_card(ids, finalScoringPeriod)`, supplies executed transaction histories for historical players. Query player IDs observed in shared lineups **plus** all player IDs found in period transaction items, in batches of 100. This returned every requested player in all six seasons. Deduplicate source transaction IDs and reconcile executed card events into the period sweep. Full executed trade transfers appear here even when the period feed has empty/missing-status trade acceptance rows. For 2021 and 2025, sampled card histories each supplied one executed trade absent from the period sweep. Archived executed trades retain `isPending=true`; their `status=EXECUTED`, `processDate` and explicit transfers establish execution. Pending/rejected proposals are never published.

This path was prompted by the [espn-api repository discussion on historical transactions](https://github.com/cwendt94/espn-api/discussions/555), then validated against this league. Earlier `mTransactions`/`mTransactionDetails` probes failed. The production adapter uses only the two verified views.

| Season | Executed normalized movement events (including draft) | Executed trades | Coverage |
|---|---:|---:|---|
| 2021 | 370 | 1 | Qualified partial |
| 2022 | 464 | 1 | Qualified partial |
| 2023 | 361 | 1 | Qualified partial |
| 2024 | 388 | 3 | Qualified partial |
| 2025 | 343 | 1 | Qualified partial |
| 2026 | 182 | 0 | Qualified partial, season in progress |

Snapshots cover source-assigned seasons from draft through late-season/offseason activity (2021 includes January 2022), with no failed periods or missing requested cards in this run. Exact bounds live in each file's coverage metadata. Neither view offers an independently verified total count; unobserved player-only history, missing trade details or archive omissions remain possible. **No transaction-based Record Book category is included.**

## Minimal public activity contract

`<season>/activity.json`:

- `schemaVersion`, `season`, `generatedAt`, `coverage`, `events`.
- Coverage: sources, `complete:false`, status, successful/failed period bounds, requested/returned/missing player counts, source and executed movement counts, unknown name count, first/last timestamps, FAAB-enabled flag, and the explicit limitation.
- Event: hashed `id` (transaction identity, never an account ID), season, UTC `timestamp`, `timestampKind` (`processed` or `proposed`), normalized `type` (`draft`, `waiver_add`, `free_agent_add`, `drop`, `trade`), source week, executed status, `teams`, `faab`, `waiverType`.
- Each team movement: fantasy `teamId`, `playersAdded`, `playersDropped`; players contain `playerId` and `name`. A trade has both teams and their exact transfers in one event.
- `faab` is numeric only when ESPN says the league uses an acquisition budget and this is a waiver add; otherwise null. This league does not use FAAB in the sampled/generated settings, so a raw zero bid is not presented as an FAAB bid.
- Waiver execution type is retained when exposed. If processing time is absent, proposed time is retained and labeled; no invented execution timestamp.

No authors, member IDs, email/login fields, raw payload metadata, credentials or cookies are stored. `movements_for_team()` provides chronological roster-movement evidence for future acquisition/former-player work. Teams page membership semantics are unchanged. Failed refreshes preserve previously verified events and mark coverage stale/unavailable; they never turn missing history into complete zero activity.

## Automatic generation

The existing `generate.py` pipeline now writes weekly lineups, then normalized activity per season, then H2H and Record Book. GitHub Actions retains its existing credentials and frequency. It also rebuilds Record Book offline from normalized snapshots before building Pages, including the checked-in-data fallback when credentials are absent. Activity statistics remain absent from records until completeness can be independently established.
