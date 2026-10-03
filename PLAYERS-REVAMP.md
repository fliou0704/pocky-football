# Players revamp

This is the initial revamp report. The subsequent [Players data polish](PLAYERS-DATA-POLISH.md) supersedes its fantasy-only week coverage, GP/FPPG scopes and participation limitations.

Players remains based on the current Basketball Brawl profile, spacing, tab and table patterns. Basketball Brawl was inspected read-only. Changes are confined to Players, its generated contracts and the bounded participation cache; no player links were added elsewhere.

## Interface

- Landing is search-only, with at most eight matching results after typing. Both query and searchable names ignore case, accents, punctuation and spacing; displayed names retain their spelling.
- Profiles retain the existing portrait and biography. The metadata snapshot timestamp becomes a local date/time “Last updated” line. No All Players link or page-wide season selector remains.
- Career consists of the Pocky Football Career season table: Season, Fantasy Team, actual GP, position-specific NFL totals, FPTS and FPPG. Multiple fantasy teams retain season-specific identities. Overview and Fantasy Team History are removed.
- Game Log has current-season-only recent played games (up to five), plus a complete log with an independent internal season selector. Week, Opp, position-specific NFL production and FPTS replace the old status column.
- Transactions is one newest-first history across all years. Executed audited adds, drops and trades are combined with draft selections, showing round and overall pick. No pick-in-round, Draft tab, coverage UI or year selector remains. Activity completeness calculations are unchanged.

## Source investigation and fields

Existing checked-in `player-scoring.json` had fantasy points, weekly NFL teams and kickoff schedules, but had discarded the underlying NFL stat dictionary. The existing ESPN `kona_playercard` response already supplies actual weekly NFL stats (`statSourceId=0`, `statSplitTypeId=1`), NFL event IDs and pro team IDs. Generation now preserves only an allowlist in each season's `player-games.json`, restricted to that season's league player universe. The same response continues to generate fantasy scoring; no second fantasy player-pool fetch is introduced.

ESPN category IDs used: passing yards 3, passing TD 4, passing interceptions 20; rushing attempts 23, yards 24 and TD 25; receptions 53 (41 fallback), receiving yards 42 and TD 43; field goals made 83, attempted 84 and extra points 86; defense sacks 99, interceptions 95, fumble recoveries 96, TD 105 and points allowed 120. Passing attempts 0 are normalized but not displayed. QB, RB, WR, TE, K and D/ST each receive relevant columns, never a universal passing table.

Weekly stat 210 explicitly establishes Games Played. ESPN's actual stat dictionaries are sparse: omitted counting categories become zero only after participation establishes an actual stat line. Empty/missing records retain nulls.

Where 210 is absent, a bounded public ESPN athlete-season event-log request supplies the explicit event `played` flag. It runs only for league athletes with ambiguous actual weekly event IDs, caches only event-ID/boolean pairs, and refreshes active-season flags. It does not introduce a separate data provider or metadata pipeline. Unavailable flags stay unknown. nflverse metadata generation is preserved.

## Calculation rules

Python prepares weekly game state, GP, FPPG and season NFL totals. React renders prepared values.

- Known NFL team plus sufficient historical schedule and no game: BYE, with dashes for production/FPTS.
- Future kickoff: Upcoming, with dashes.
- Started game in an unfinished fantasy week: live/pending internally; no status column. Pending shows dashes.
- Completed game with explicit participation, or nonzero actual NFL production: played. A real played zero-point game keeps zero.
- Explicit `played=false`: Did not play, excluded from GP and shown with dashes.
- Unresolved participation: Participation unknown, with dashes. Zero fantasy points alone never prove participation or inactivity.
- A D/ST represents its NFL team's scheduled game, so a completed scheduled defense game counts as participation.

GP counts only played completed games, excluding byes and non-participation. If any completed participation is unresolved, GP/FPPG and complete NFL totals remain null. FPTS is independently summed from available completed fantasy point records, even when GP is unknown. FPPG is FPTS divided by verified GP, not represented fantasy weeks. Unavailable counting stats never become invented totals.

Totals cover NFL weeks represented by each fantasy season's scoring contract, not a promise of the entire NFL regular season. Historical contracts end at fantasy week 17; the active contract currently ends at week 14. Team changes use actual weekly pro-team evidence first; unsupported historical identity/participation is left unknown.

## Contracts and implementation

New: `football_player_games.py`, six season `player-games.json` files and participation tests. Updated: `football_player_scoring.py`, `football_exporter.py`, `football_players.py`, all 539 generated player profiles, `PlayersPage.jsx`, `player-view.js`, `players.css`, and frontend tests. Profile contracts add `currentSeason`, `statColumns`, `seasonStats`, weekly `gameState`/`nflStats`, and draft timestamps. Existing scoring, metadata identity and activity coverage contracts remain intact. Actions caches participation alongside metadata; workflow schedule is unchanged.

Before deployment, 1,548 player-season rows include 96 with incomplete participation (2021:19, 2022:37, 2023:9, 2024:11, 2025:10, 2026:10). Examples include missing historical athlete records and the canceled Buffalo–Cincinnati game in 2022. These are deliberate unknowns, not zero-filled approximations. Scheduled refresh may change active-season counts.

## Validation and publication

82 Python regression tests, 26 Node tests and 9 React tests pass; production build passes with the repository base path. Focused tests cover normalized search, search-only landing, profile timestamp, removed controls, GP/FPPG, sparse stats, participation fallback/cache, position columns, current-only recent games, internal selector, BYE/inactive/upcoming/real zero, and merged chronological draft/activity transactions. Browser review covers desktop plus 390px and 320px mobile layouts with no document overflow; wide tables scroll inside their cards.

Publication proceeds through a feature PR into main and the existing GitHub Pages workflow. PR/deployment results are reported in the completion message.
