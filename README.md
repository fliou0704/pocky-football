# Pocky Football

This personal site generates a weekly Home page and standings from an ESPN fantasy football league. It has its own football processing pipeline. Basketball Brawl remains separate and unchanged.

## Configure a league

The current league is selected by its slug in `leagues.json`. To adapt a copy of this project for another league, change the entry's ESPN `leagueId`, `season`, and slug, then generate with that slug. Credential entries contain environment variable names only. League and team display names, records, standings, logos, weekly scores, and player performances come from ESPN.

For private leagues, set those variables in your environment or a local `.env` in this folder. Never commit credentials. `.env` is gitignored. Public leagues can omit `credentials`.

Install Python dependencies with `python -m pip install -r requirements.txt`. Then generate data from this folder:

```sh
python generate.py --league pocky-football
```

The exporter writes `frontend/public/data/<slug>/<season>/league.json` for standings, `teams.json` for season-specific team views, `home.json` for weekly Home content in the active season, and a small `frontend/public/data/site.json` pointing the frontend at the selected league. The normalized JSON contains no credentials. Regenerate it to refresh ESPN scores; the page does not make live ESPN requests. Current scores use ESPN's `totalPointsLive` field because the package's basic `scoreboard()` returned zero while the week was active. ESPN's matchup `winner` marks final results; otherwise a matchup with live scoring is shown as in progress and one without scoring is upcoming.

## Team logos

The exporter checks whether an ESPN logo URL responds as a public HTTPS image. Inaccessible URLs are omitted, and the page shows a team initial. The browser also falls back to the initial if a previously working image later fails.

To override a team logo, put a PNG, JPEG, WebP, or SVG in `frontend/public/team-logos/`, then add its **team ID** to `teamLogoOverrides` in `leagues.json`:

```json
"teamLogoOverrides": {
  "11": "team-logos/team-11.png"
}
```

The path is relative to `frontend/public/`. Regenerate data after editing configuration. Local overrides take priority over ESPN URLs, including on GitHub Pages.

## Owner names and roster history

ESPN first and last names are used when present; otherwise the ESPN display name is the fallback. To correct a name without editing React, add `ownerNameOverrides` to the league entry in `leagues.json`, keyed by **season, then team ID**:

```json
"ownerNameOverrides": {
  "2025": { "3": "Preferred Owner Name" }
}
```

Regenerate data after editing the configuration. The override has first priority. Season and team ID are paired because a team ID can be reused by a different owner in another season. The public JSON contains only the chosen owner name, not ESPN member IDs, logins, or email addresses.

`teams.json` keeps the season-end roster for completed years, labeled **Final Roster**, and ESPN's active roster for the current year. Weekly ESPN scoreboard roster snapshots establish which players belonged to each fantasy team, including starters, bench, and IR. A player seen in those snapshots but absent from that team's current/final roster appears under **Dropped / Former Players** with the weeks observed. This is membership evidence, not a transaction log or a complete account of every player's season points. A traded player can therefore appear for both teams in the appropriate lists.

## Run the page

Install Node.js, then from this folder:

```sh
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite. Home, Standings, Teams, H2H, and Record Book work; Players remains unavailable. The Home page shows the current fantasy week, current matchups, the last completed weekly recap, and standings. A completed season shows its final week recap and regular-season standings. Regenerating with another configured slug updates the independent copy of the site.

## Tests

From this folder, run `python -m unittest discover -s tests -v`. In `frontend`, run `npm test` and `npm run build`.

The Stage 0 diagnostic `inspect_espn_football.py` remains separate from generation.

## GitHub Pages

This project is designed for its own GitHub repository and project site. The workflow in `.github/workflows/pages.yml` builds and deploys the site on pushes to `main`, by manual dispatch, and on Monday, Tuesday, and Friday at 14:00 UTC. Scheduled and manual runs fetch only the configured active ESPN season, validate the complete candidate release, persist generated JSON to `main`, and explicitly build and deploy it. Push runs use the latest persisted snapshots without ESPN requests. All release runs are serialized and reject outdated checkouts or a newer public generation.

Standings and Teams include ESPN seasons 2021 through the configured current season. Routine automated refreshes regenerate active-season source snapshots and dependent cross-season analytics while preserving historical season files. The default local generator still supports full historical generation; use `--current-only` to avoid historical fetches. The active season also gets `home.json`. Historical data is checked in as a reproducible snapshot, while GitHub Actions refreshes it from ESPN when secrets are present. No browser request uses ESPN credentials. Team IDs are meaningful **within a season**; do not infer permanent franchise identity across years.

`teams.json` includes normalized matchups so later H2H and Record Book exporters can use source data directly. It marks single-team playoff entries as byes with no opponent. Manual logo overrides currently apply only to the configured active season because ESPN can reuse a team ID for a different historical team. Schedule playoff labels are generated in Python from each season's regular-season length, winners-bracket rounds, playoff team count, and semifinal losers. ESPN's two consolation ladder types remain distinct.

1. Create a separate GitHub repository for Pocky Football and push this folder to its `main` branch. Never add `.env`.
2. In repository **Settings → Secrets and variables → Actions**, create repository secrets named `ESPN_S2` and `SWID`.
3. In **Settings → Pages**, select **GitHub Actions** as the build and deployment source.
4. Run the workflow from **Actions → Build and deploy Pocky Football → Run workflow**, or push to `main`.

The Vite base path is derived from GitHub's repository name, so assets, JSON, logo overrides, and hash navigation work under `https://<owner>.github.io/<repository>/`. A local build uses `/`; set `VITE_BASE_PATH=/repository/` to test the project path locally. The Pages artifact contains only the static frontend and generated JSON, never the repository's `.env` or the Actions secrets.

## Head-to-head (Stage 2D)

The H2H menu links directly to Historical and Theoretical views. Both use two current-season team selectors, a record summary, and newest-first rows, following Basketball Brawl's current H2H layout. Selecting a team removes that ID from the opposite selector. Both selectors start empty. Selected IDs are stored in hash query parameters (`a` and `b`), preserving direct links, refreshes, and mode changes.

`football_h2h.py` reads existing `league.json` and `teams.json` snapshots. It writes `data/<slug>/h2h.json` (current selector teams and season coverage), plus one `h2h/<lower-ID>-<higher-ID>.json` file per pair with both perspectives, summaries, season summaries, and rows. Regular generation also rebuilds H2H after season data refreshes; React only chooses a precomputed view and optional season filter.

Historical H2H counts completed actual matchups, including regular, championship, placement, and consolation games. It retains ties, season-specific names/logos, decimal scores, and detailed playoff round labels. Byes and self-matchups never count. Unlike Basketball Brawl's legacy historical list, consolation meetings remain visible so the list agrees with the overall record; ties are explicitly represented rather than treated as losses. Clicking a row opens both historical weekly lineups; only one row is open at a time.

Theoretical H2H follows Basketball Brawl's regular-season-only rule: both teams must have finite completed scores in the same season and fantasy week. Live/upcoming weeks, byes, and every playoff/consolation week are excluded. Zero is a valid completed score. Each eligible week counts once; `actualMeeting` marks overlaps with real games. Summary and season records are computed in Python.

Team IDs are season identifiers, not verified franchises. A shared ID aggregates only seasons where both selected IDs exist; reused IDs can refer to different owners or teams. No name/owner-based predecessor mapping is used. Rows retain each season's own name and available logo; selectors use current names and the existing logo fallback.

Weekly lineup detail lives in `<season>/lineups/<week>.json`, shared across pairs and modes. Each file contains `schemaVersion`, `season`, `week`, and `teams` keyed by fantasy team ID. Player rows contain only `playerId`, `name`, `slot`, `nflTeam`, `position`, and actual weekly `points` (null when unavailable). These come from ESPN historical scoreboard box-score rosters, including bench and IR, and retain source order. React orders slots QB, RB, WR, TE, FLEX, D/ST, K, BE, IR while preserving repeated-slot order. Detail requests are lazy and cached; missing detail affects only the expanded panel.

## Record Book (Stage 2E)

Record Book renders precomputed All-Time rankings and completed-season honors (currently 2021–2025). Team pages include authoritative historical Draft selections. Ranked matchup awards share H2H weekly lineup details; player-season and Best Pickup awards use actual weekly scoring and audited acquisition stints. See [Team and Record Book refinement](TEAM-RECORD-BOOK-REFINEMENT.md) for contracts, tie/filter rules, coverage qualifications and tests, and [historical activity audit](HISTORICAL-ACTIVITY-AUDIT.md) for source validation. The original [Stage 2E report](STAGE-2E-RECORD-BOOK.md) describes the earlier implementation.

### Player metadata foundation (Stage 2F-A)

The data-only player identity contract and coverage audit are documented in
[STAGE-2F-A-PLAYER-METADATA.md](STAGE-2F-A-PLAYER-METADATA.md).
Generate from existing normalized league snapshots with
`python football_player_metadata.py --refresh --check-headshots`.
Stage 2F-A supplied audited metadata; Stage 2F-B adds the Players section while leaving the workflow schedule unchanged.

### Players (Stage 2F-B)

Players follows Basketball Brawl’s search, profile and tab layout with football scoring, weekly roster evidence, draft picks and audited transactions. Hash routes (`#/players/<ESPN ID>/<optional season>`) preserve direct links on GitHub Pages. Player links are confined to Players.

`python football_players.py` builds a compact index and one profile/history contract per league entity from normalized snapshots. Full generation refreshes metadata once from nflverse and rebuilds these files. GitHub Actions caches headshot checks between runs; `--recheck-images` explicitly revalidates old URLs. See [STAGE-2F-B-PLAYERS.md](STAGE-2F-B-PLAYERS.md) for definitions and validation.

### Players revamp

Players is now search-only, with a simplified Career table, position-specific NFL statistics, an independent Game Log season selector, and all-time Transactions including draft selections. Python determines participation and actual GP/FPPG before rendering; ambiguous participation remains unknown. See [Players revamp](PLAYERS-REVAMP.md) for source fields, calculation rules, contracts, validation and limitations.

The [focused Players data polish](PLAYERS-DATA-POLISH.md) extends Game Log to all 18 NFL regular-season weeks, makes Career fantasy totals reflect completed active-slot starts, and fixes bundled-drop labels using audited movement directions.

Manual season-aware team branding: see [TEAM-BRANDING.md](TEAM-BRANDING.md).

## Draft

Draft now includes Summary and six season recaps, full boards, round rankings, position-aware value, explicit manager identities, tendencies, rookie controls, and evidence links. Generate offline with `python football_draft_analysis.py`; see [Draft methodology and coverage](DRAFT-ANALYSIS.md) for exact formulas, exclusions, and maintenance.

## Persisted data releases

`data_refresh.py refresh` stages a current-season fetch in a temporary directory,
checks required contracts, coverage, previous data retention and historical stability,
then promotes the validated candidate. `data_refresh.py validate` checks stored JSON
and, after the first refresh, the per-file hashes in `data/pocky-football/refresh.json`.
The metadata records the successful fetch time, season, matchup period, generation,
run ID and whether sports data changed. It contains no credentials. Ordinary code
builds never advance this timestamp. A valid no-change fetch keeps the existing
persisted files and records its check time in workflow logs rather than creating a
metadata-only commit. The initial metadata bootstrap may create one commit even
when the source payloads are unchanged.

The workflow tests/builds the candidate before committing only generated JSON with
`chore(data): refresh Pocky Football snapshots`. It uses the job's `GITHUB_TOKEN`
with `contents: write` and a normal fast-forward push to `main`; no PAT, force push
or recursive workflow trigger is needed. That token's push does not trigger another
push workflow, so this run explicitly deploys its own tested artifact. Code-only
runs deploy the persisted data without rebuilding JSON into an uncommitted generation.

A failed fetch, invalid/partial source contract, rejected push, advanced `main`,
rollback guard, build failure or failed public verification fails the workflow.
If `main` advances during a run, rerun on latest `main`; it will not overwrite the
newer commit. GitHub may replace pending concurrency runs, but every run that starts
reads current `main`; running releases are not canceled by later pushes. Both event
paths share the same publication lock. Public verification checks generation metadata
and actual manifest/Home/Teams hashes with bounded retries for Pages propagation.

If branch protection rejects the bot push, do not bypass it. The workflow stops
before deployment. An administrator must choose a permitted persistence mechanism
(e.g. a reviewed data PR followed by deployment of its merged snapshot) before
refreshes can resume; direct-write support depends on repository policy. Existing
Pages settings and `ESPN_S2`/`SWID` names remain unchanged. No game-day frequency
change is included.

After merging, manually run **Build and deploy Pocky Football** on `main`, inspect
fetch/validation/persistence/public-verification outcomes and the snapshot commit,
then run a code-only deployment and compare the generation and public JSON hashes.
A green build alone does not prove ingestion or successful public verification.

The first verified persisted refresh ran on October 29, 2026 in
[Actions run 40929630108](https://github.com/fliou0704/pocky-football/actions/runs/40929630108).
It saved snapshot commit `0f3fbba`, advanced Home to Week 8 with Week 7 completed,
and passed public metadata and source JSON hash verification. Season files for
2021–2025 were unchanged. This documentation-only update also exercises the
subsequent push deployment path using that persisted generation.
