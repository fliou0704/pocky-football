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
