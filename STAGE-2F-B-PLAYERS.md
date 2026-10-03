# Stage 2F-B: Players

## Basketball Brawl reference

Inspected Basketball Brawl’s `Players.jsx`, `PlayerSearch.jsx`, `PlayerIdentity.jsx`, `player-data.js`, `players.css`, and design system before implementation. Reproduced its name search (including accent/punctuation normalization), compact search on detail pages, large headshot/profile card, optional biography fields, Career / log / Transactions tabs, recent five performances, season selection, team identities, table scrolling within cards, and stacked mobile profiles/transactions. Pocky’s existing masthead, green accents, typography, `Section`, `Team`, card classes, and overview statistics are reused. Basketball Brawl was not modified.

The two sites are separate builds, so no cross-repository runtime dependency was introduced. Common search and biography formatting follow the existing Brawl pattern in one football helper module; football scoring and ownership evidence are precomputed behind the normalized JSON boundary. No existing football component or record calculation was duplicated.

## Players experience

- Enabled Players navigation only. Existing Home, Teams, H2H, Record Book, roster and matchup player names remain unchanged.
- Alphabetical browse, name search, position filter, and a separate team-defense browse mode. The index holds all 539 audited entities (507 humans, 32 defenses).
- Human profiles show name/headshot, latest NFL team, position/jersey, age calculated from DOB, height/weight, DOB, college, NFL Draft and rookie season where available. Optional nulls disappear cleanly. Failed images use an initials fallback.
- D/ST profiles show a team logo, name and NFL team with no human biography.
- Career: league-scored and starter summary, season totals, fantasy teams observed, and expandable ownership evidence and final/current roster snapshots.
- Weekly Log: recent five and complete newest-first scores, season/week, historical NFL matchup when available, observed fantasy roster/slot and score, and final/live/upcoming status.
- Draft: authoritative fantasy season/team/round/pick-in-round/overall selections, separately from the NFL Draft biography.
- Transactions: executed free-agent adds, waivers, drops and trades with explicit source/destination teams. Draft events are shown separately. Historical activity coverage limitations remain visible.
- All-Time and only seasons with actual league presence. `#/players/<signed ESPN ID>/<optional season>` preserves player and season across refresh under the GitHub Pages base path. Invalid/non-present season choices resolve to All-Time; unknown IDs display an explicit not-found message.

Brawl’s NBA box-score columns, minutes-based rates, and games-played semantics were omitted because football’s current contracts do not supply equivalent audited data. No awards or charts were invented; the inspected Brawl implementation uses tables rather than charts. Football adds explicit draft history, D/ST identity, position browsing, scored-week versus starter totals, and weekly ownership evidence. A current roster absence is not automatically labeled a fantasy free agent.

## Data contracts and generation

`football_players.py` reads the existing normalized league, teams/rosters, weekly lineups, player-scoring, draft and activity files, plus Stage 2F-A’s audited `players.json`. It makes no network requests.

Generated:

- `frontend/public/data/pocky-football/players-index.json`: alphabetical index, basic identity/search fields, actual presence seasons and one profile path per signed ESPN ID. About 209 KB uncompressed.
- `frontend/public/data/pocky-football/players/<ESPN ID>.json`: public profile allowlist, precomputed career/season summaries, weekly score rows with only this player’s roster snapshots, team ownership evidence, draft picks, and executed movements. Median profile about 22 KB; largest about 67 KB. It does not duplicate whole activity or lineup datasets.
- `site.json` gains `playersPath`.

Full exporter generation refreshes the nflverse source once, reuses cached URL checks, and rebuilds Players after normalized snapshots. GitHub Actions caches `.cache/player-metadata` across runs and rebuilds compact Players contracts before the existing build/deploy. No new secret, paid API, frontend dependency, or schedule increase. ESPN private fields are never added to the player contracts.

The audited identity generator is retained. The only cache refinement separates source refresh from image rechecking: `--refresh` retrieves source data, while `--recheck-images` explicitly revalidates old URL results. New headshot URLs are checked automatically in checked generation. The browser handles later failures.

## Scoring and ownership definitions

- Scores use this league’s actual ESPN applied totals, not generic scoring.
- Season/career league-scored FPTS sum available numeric scores in finalized fantasy weeks across that season’s normalized scoring scope, including weeks without league ownership. These are not points necessarily contributed to a fantasy team.
- Finalized weekly lineup values provide a fallback only when the scoring pool lacks that player/week and the observed values agree. A disagreement between audited lineup and scoring data fails generation.
- Explicit numeric zero is counted. Missing/null is retained and excluded from averages. Scored weeks are not claimed as NFL games played or healthy appearances.
- Starter FPTS and starts count numeric scores from active fantasy lineup slots in finalized weeks only, using the shared existing starter-slot definition. Bench/IR scores do not contribute. Live points are shown as provisional but excluded from summaries.
- Weekly fantasy ownership comes from that week’s actual lineup roster only. Drafts, current/final rosters and transactions separately establish recorded team appearances; no uninterrupted ownership periods or free-agent status are inferred from gaps.
- Latest profile team/jersey are explicitly labeled separately from historical weekly NFL facts. Human coverage and identity remain the Stage 2F-A foundation.

## Validation

- **78 Python tests passed**, including seven foundation tests and two Players tests. The complete generated universe is checked against audited metadata; all generated player histories are checked against source draft picks, event counts, lineup teams/slots/scores and scoring pool values. Null, zero, live and bench scoring behavior is tested. Tests adapt to new configured seasons and players.
- **25 frontend helper tests and 8 React tests passed**. Includes search/filter/selection, signed-ID routes, age/height/nulls, season fallback, draft and transaction sections, D/ST exclusion, image fallback, compact fetching and stale/not-found detail replacement.
- Production build passed with `/pocky-football/` base path.
- Browser checks: search → profile; historical season selection and draft; direct URL refresh; rendered headshots; historical trade from/to teams; D/ST logo and no human fields; desktop and 390px/320px profiles/logs with document width no larger than viewport.
- Home, Standings, Teams, H2H and Record Book smoke checks passed without alerts. No player-detail links exist on those checked pages. No browser console errors during these checks.
- Basketball Brawl files were read only. No authenticated ESPN calls were needed locally; publication uses the established GitHub Actions refresh.

## Remaining limitations

Coverage depends on the available audited snapshots and transaction feeds. Missing scores remain unknown; byes/inactive zero scores are not converted to an invented games-played statistic. Historical transaction timestamps can be proposed rather than processed; the UI discloses that distinction. The metadata foundation has 48 missing jersey numbers and 83 empty NFL Draft records; no values or undrafted status are invented. Latest-source team abbreviations can differ from historical ESPN aliases. Tables scroll inside their cards on narrow screens, following Brawl’s log/table behavior.

Site-wide player linking remains outside this stage.
