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

This project is designed for its own GitHub repository and project site. The workflow in `.github/workflows/pages.yml` builds and deploys the site on pushes to `main`, by manual dispatch, and on Monday, Tuesday, and Friday at 14:00 UTC. Scheduled and manual runs regenerate ESPN data on GitHub; push runs also regenerate when credentials are available, or deploy the checked-in generated JSON when they are not.

Standings and Teams include ESPN seasons 2021 through the configured current season. Each run regenerates one small `league.json` (season-specific standings) and one `teams.json` (season-specific weekly matchups and team overviews) per year. The active season also gets `home.json`. Historical data is checked in as a reproducible snapshot, while GitHub Actions refreshes it from ESPN when secrets are present. No browser request uses ESPN credentials. Team IDs are meaningful **within a season**; do not infer permanent franchise identity across years.

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

Record Book renders precomputed All-Time and 2021–2026 records, season honors, tied holders, and expandable details. Python reuses normalized matchup and weekly lineup snapshots. Executed fantasy activity is generated separately with explicitly qualified coverage; transaction records are deferred. See [Stage 2E rules, source investigation, and contracts](STAGE-2E-RECORD-BOOK.md).
