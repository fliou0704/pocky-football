# Draft analysis V2

`#/draft` opens the active-manager Summary. `#/draft/2021` through `#/draft/2026` open authoritative season boards; `?pick=40` opens an individual evidence selection. Complete tables preserve original draft order. Ranked leaderboards have explicit ordering and expand to their complete eligible lists. The introductory hero, methodology disclosure, and previous Draft Value metric have been removed. No replacement composite combines positional rankings.

## Calculations

Python supplies every analytic result in `draft-analysis.json`. React resolves compact references and controls expansion/search. Generate with `python football_draft_analysis.py`; the existing exporter and GitHub Pages pipeline rebuild the same contract. No additional API source or duplicate historical datasets are introduced.

- **Season FPTS:** sum ESPN league-scored actual weekly totals across the weeks represented in fantasy matchups, including fantasy playoffs/consolation; exclude unused NFL weeks. Credit the originally selected player regardless of later fantasy trades, drops, benching or starts.
- **Overall rank movement:** original overall draft pick minus final overall fantasy-point rank. Final ranks consider all eligible scored players, including undrafted players. Positive means finishing above draft position. This is descriptive and does not claim equal value across positions. Risers include positive movement; fallers include negative movement, each starting with ten rows and expanding to every eligible pick in that category.
- **Positional rank movement:** ordinal draft order within QB, RB, WR, TE, K or D/ST minus final rank among ALL eligible players at that position, including undrafted players. Every drafted player at the position counts toward ordinal draft order, including an unresolved scorer. Missing scores never shift other players' original positional draft order. Final ranks use average ranks for ties; real zero and negative totals count. Rank movement remains null when final rank is unknown. Position-specific manager leaderboards use average movement per eligible pick, with total movement and evaluated/drafted sample counts. Different positions are never merged into a positional score.
- **Round performance:** rank picks by descending season FPTS, using average ranks for ties; every tied highest scorer wins the round. Display every round and its picks in ascending original draft order, with separate performance-rank cells. Expand each round from three selections to its complete board. An unresolved score withholds that round's performance ranking. Normalized round score = `100 * (number of picks in round - rank) / (number of picks in round - 1)`; a singleton denominator is bounded at one. Higher is better. This existing normalization supports comparisons across different league sizes. Overall historical manager comparisons use average normalized round scores alongside raw average round rank, evaluated counts and round wins; no positional composite.
- **Provisional seasons:** only fully finalized fantasy weeks contribute displayed current-season points. Until the season, complete authoritative draft board and scoring source checks qualify, withhold final overall/positional/round ranks and rank movement. Provisional results never enter historical performance rankings.
- **Tendencies:** round, normalized pick `1 + (overall pick - 1) / team count`, first positional selection, and share of selections. Median/mean first-selection round count each manager/position/season once, regardless of repeat positional selections.
- **Rookies:** NFL `rookieSeason == fantasy season`, including undrafted NFL rookies. Missing/future metadata stays unknown; D/ST has no rookie classification. Frequency/share and drafting timing are separate from position-specific rookie movement. No cross-position rookie movement score.

## Active manager scope

Resolve managers using the existing explicit `draft-manager-identities.json` memberships with expected owner-name checks. Determine the active set from the **latest available season's standings**, currently 2026, not from historical team names or reused ESPN IDs. Apply this same set before every Summary aggregate, positional ranking, tendency, rookie analysis and historical trend. Historical seasons still include all draft entries and all participating managers. Unmapped or changed owners retain season-specific identities; duplicate memberships fail generation.

## Unevaluable-pick investigation

`draft-scoring-audit.json` records every formerly excluded completed-season selection, exact ESPN ID, metadata/scoring join checks, recovered week contributions, final status and unresolved weeks. It is regenerated alongside Draft analytics. In the checked-in normalized snapshot:

| Season | Previously excluded | Recovered | Still unresolved |
| --- | ---: | ---: | ---: |
| 2021 | 5 | 5 | 0 |
| 2022 | 26 | 26 | 0 |
| 2023 | 3 | 3 | 0 |
| 2024 | 5 | 5 | 0 |
| 2025 | 4 | 4 | 0 |
| Total | 43 | 43 | 0 |

All 43 had matching ESPN scoring and metadata IDs. None was an unknown metadata join, an undrafted-player issue, or a D/ST ID problem. The prior strict per-week completeness filter rejected gaps after NFL team changes, covered absence of actual production, and the canceled 2022 BUF–CIN game. It also failed to consult alternate normalized actual game records for three weekly scores. Negative D/ST IDs remain signed and join directly; all completed-season D/ST picks were already scored.

Recovery follows the existing Players contracts:

1. Use a finite weekly league-scored total when present. If the normalized actual NFL game record also contains a different finite total, leave the result unresolved.
2. Otherwise use a finite `player-games.json` actual points value, including zero.
3. Explicit `played=false` establishes no game production. A complete historical NFL schedule can establish a bye or canceled game.
4. The same covered-season rule used by `football_player_games.game_state` and `football_players.py` treats an absent weekly actual record in a covered actual season as no production (bye/non-participation). Require the player ID in `playersWithActualSeasonRecords` AND all selected weeks in the requested game-data weeks. A partial/absent schedule cannot establish a bye by itself. Team timing uses historical weekly observations; current NFL metadata does not establish an old team. For missing records around a trade, no-production classification follows source coverage even if exact team membership timing is ambiguous.
5. Absent player coverage, a played record without a score, conflicting sources or an explicit invalid weekly total stays unknown. Never infer zero from missing metadata or an unmatched ID. Known points with unknown positional identity remain visible without manufacturing final ranks.

The 43 recovered picks account for 123 formerly missing weekly contributions: three actual scores, 39 byes, 12 canceled-game gaps, and 69 covered no-actual-record gaps. These counts describe the checked-in snapshot and may change on regeneration. This does not claim independent transaction-by-transaction proof of every NFL absence; it reuses the explicit normalized source-coverage semantics already used by Players.

Concrete examples:

- **2022 Nyheim Hines (3916430):** week 1's 11.4 FPTS exists in normalized actual game records but not the weekly scoring dictionary. Recovered season total: 69.4.
- **2024 Mike Williams (3045138):** week 1 explicitly records a played game with **0.0** points. Zero is valid. Recovered season total: 53.3.
- **2025 Rashid Shaheed (4032473):** week 1's 9.3 FPTS comes from normalized actual game records. Recovered season total: 155.4.
- **2022 Christian McCaffrey (3117251):** his week 9 bye was rejected because his historical team set contains CAR and SF. Historical game records/schedule and covered no-production rules resolve it. Total: 339.46.
- **2022 Josh Allen (3918298):** missing weeks are BUF's week 7 bye and the canceled week 17 BUF–CIN game. Total: 373.76.
- **2021 Henry Ruggs III (4241475):** actual production ends early; his covered season has no later weekly actual records. Preserve his recorded 84.5 FPTS instead of excluding him for no subsequent production.

All 896 completed-season picks now have final rankings. The 160 current 2026 picks remain provisional; they were not part of the 43 completed-season coverage exclusions. Unknown future inputs remain visible with — and missing-week evidence.

## Validation

Run `python -m unittest discover -s tests -v`, `pnpm --dir frontend test`, and `VITE_BASE_PATH=/pocky-football/ pnpm --dir frontend build`. Targeted tests cover original draft order, round ranking/ties/normalization, overall and positional movement including undrafted players, original positional order despite missing scoring, active identity filtering in all Summary sections, historical inactive managers, positive/zero score recovery, genuine missing data, source conflicts, D/ST IDs and provisional seasons. UI tests cover table expansion, draft ordering/rank cells, team logos, removed UI and season selection.

## Gain-based rankings and ongoing NFL seasons (2026 update)

Positional draft-slot gain is actual overall pick minus the original overall
pick of the Nth selection at that position, where N is performance positional
rank (including eligible undrafted players), not draft-order positional rank.
If N exceeds the drafted positional pool, the benchmark is the final overall
pick of the **entire draft + 1**. Canonical picks mark this with
`benchmarkStatus: below_drafted_range`; the UI says “Below drafted positional
range”. Missing/unreliable ranks have no benchmark. Legacy fractional input is
rejected defensively, but the builder no longer produces fractional ranks.

All Draft performance ranks use competition ranking: 1, 2, 2, 4. Numerical ties
remain tied; player IDs only determine deterministic display ordering. Round
Rank, round wins, and value standouts now maximize **raw positional draft-slot
gain**, replacing both the FPTS-based Round Rank and relative-gain standout.
Best positional finish remains separate supporting recognition. Manager Average
Round Rank is still ascending, now averaging gain-based round ranks. Summary
retains its active-manager filter, current branding, and finalized-season-only
scope; positional averages now include known out-of-range finishes.

Completed seasons preserve the existing full fantasy-season evaluation window
(all scheduled league matchup weeks, including playoffs); total fantasy points
determine positional performance. Ongoing seasons use only fully completed NFL
regular-season weeks. The normalized schedule must contain the established
32-team, 272-game, 17-games-per-team regular season; partial schedules, unknown
statuses and unfinished/rescheduled events cannot establish a completed week.
No calendar-date completion inference is added. A canceled event is terminal.
A future NFL schedule-format change would require updating this validation.

Ongoing positional ranking uses exact unrounded total points / verified NFL
games played, displaying FPPG to two decimals. Participation uses the existing
`football_player_games.game_state` evidence contract and matched scheduled
NFL event IDs. Explicit played zeroes count; byes, DNP and canceled games do
not. Covered absent actual-season records mean nonparticipation; absent source
coverage, unknown participation, mismatched events and conflicting scores stay
unavailable. Positive actual NFL stats may establish participation under the
existing contract. Fantasy starts and elapsed weeks never provide the divisor.

Normal qualification requires at least `ceil(completed NFL weeks / 2)` games
(and at least one). Independently, the complete available reliable-scoring
positional pool is competition-ranked by cumulative points, including undrafted
players. A below-threshold player qualifies when this cumulative positional rank
is within the number drafted at that position, with at least one verified game
and valid FPPG. They then enter the **same FPPG** leaderboard. Canonical picks
track `qualification` (`normal`, `total_points`, `insufficient_games`,
`missing_participation`, `missing_scoring`, or `final`), `gamesPlayed`, `fppg`,
and `rankingBasis`. UI exception label: “Qualified by total points”.

Reliable individual picks remain evaluable when another selection is unavailable;
round comparisons explicitly label partial coverage. Incomplete draft coverage or
source-level scoring conflicts prevent benchmarks/ranks. Provisional season
averages remain local to that season and do not enter finalized career Summary.
Year folders with valid drafts are discovered automatically; there is no latest
year constant in the Draft builder or selector.

All meaningful data headers are sortable through the shared `draft-sort.jsx`
controls: Summary overall/positions/tendencies/rookies/historical rounds, season
Overall Performance, expanded underlying picks, round tables, gains/losses, and
Full Draft Board. Numeric source fields drive rank sorts (not formatted QB/K
labels); missing values remain last in either direction, ties use stable IDs,
and sorting copies rows without changing statistics or expansion state. Native
buttons support keyboard activation and `aria-sort` communicates direction.
There are no action-only or decorative columns requiring a sorting exemption.
Tables retain horizontal overflow within their containers on narrow screens.

Offline checks against committed examples:

| Season / player | Performance rank | Actual pick | Benchmark | Gain |
|---|---:|---:|---:|---:|
| 2025 Jaxon Smith-Njigba | WR2 | 30 | 3 | +27 |
| 2025 Josh Allen | QB1 | 26 | 25 | +1 |
| 2025 Trey McBride | TE1 | 28 | 21 | +7 |
| 2024 Christian McCaffrey | RB67 | 1 | 161 | -160 |
| 2026 Jared Goff (provisional) | QB2 | 141 | 49 | +92 |
| 2026 Breece Hall (provisional exception) | RB17 | 38 | 31 | +7 |

Goff: 18.02 + 28.94 + 20.48 + 19.36 + 29.78 + 16.44 = 133.02 / 6 =
22.17 FPPG; his bye is excluded. Hall: 8.5 + 14.2 + 19.8 = 42.5 / 3 =
14.1667 FPPG; four explicitly unplayed games are excluded. The snapshot confirms
seven NFL weeks, so the normal minimum is four. The total-points exception admits
Hall. The generated 2026 snapshot evaluates 146/160 picks; 14 have insufficient
participation. These are unavailable evaluations, not fabricated low rankings.

The existing refresh already rebuilds Draft after normalized scoring and
player-games refresh, then validates/persists the whole generation. No workflow,
frequency, logo archive, rollback guard, source snapshots, or ESPN export behavior
changed. Offline regeneration updates derived generation hashes via
`update_derived_metadata` without claiming a fresh ESPN fetch. Older methodology
sections/reports describe earlier releases; this section supersedes their
midrank, out-of-range exclusion, final-only season and relative-gain rules.

Release validation: 171 Python tests, 38 Node tests, and 68 React tests pass;
production build and release JSON validation pass. jsdom concurrency is capped
at two workers because unrestricted workers caused real-data render tests to
compete for CPU and exceed the existing five-second timeout; assertion checks
and timeouts are unchanged. Browser checks covered Summary and inline sorting,
2025 Round 3 gain order, 2024 McCaffrey fallback, 2023 Tucker/Elliott tied K2,
2026 provisional rounds and Hall's exception, keyboard sorting, and 390px/320px
layouts without page-level horizontal overflow.
