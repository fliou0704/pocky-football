# Pocky Football

This personal site generates a weekly Home page and standings from an ESPN fantasy football league. It has its own football processing pipeline. Basketball Brawl remains separate and unchanged.

## Configure a league

The current league is selected by its slug in `leagues.json`. To adapt a copy of this project for another league, change the entry's ESPN `leagueId`, `season`, and slug, then generate with that slug. Credential entries contain environment variable names only. League and team display names, records, standings, logos, weekly scores, and player performances come from ESPN.

For private leagues, set those variables in your environment or a local `.env` in this folder. Never commit credentials. `.env` is gitignored. Public leagues can omit `credentials`.

Install Python dependencies with `python -m pip install -r requirements.txt`. Then generate data from this folder:

```sh
python generate.py --league pocky-football
```

The exporter writes `frontend/public/data/<slug>/<season>/league.json` for standings, `home.json` for weekly Home content, and a small `frontend/public/data/site.json` pointing the frontend at the selected league. The normalized JSON contains no credentials. Regenerate it to refresh ESPN scores; the page does not make live ESPN requests. Current scores use ESPN's `totalPointsLive` field because the package's basic `scoreboard()` returned zero while the week was active. ESPN's matchup `winner` marks final results; otherwise a matchup with live scoring is shown as in progress and one without scoring is upcoming.

## Team logos

The exporter checks whether an ESPN logo URL responds as a public HTTPS image. Inaccessible URLs are omitted, and the page shows a team initial. The browser also falls back to the initial if a previously working image later fails.

To override a team logo, put a PNG, JPEG, WebP, or SVG in `frontend/public/team-logos/`, then add its **team ID** to `teamLogoOverrides` in `leagues.json`:

```json
"teamLogoOverrides": {
  "11": "team-logos/team-11.png"
}
```

The path is relative to `frontend/public/`. Regenerate data after editing configuration. Local overrides take priority over ESPN URLs, including on GitHub Pages.

## Run the page

Install Node.js, then from this folder:

```sh
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite. Home and Standings work; the other navigation destinations are labeled as unavailable. The Home page shows the current fantasy week, current matchups, the last completed weekly recap, and standings. A completed season shows its final week recap and regular-season standings. Regenerating with another configured slug updates the independent copy of the site.

## Tests

From this folder, run `python -m unittest discover -s tests -v`. In `frontend`, run `npm test` and `npm run build`.

The Stage 0 diagnostic `inspect_espn_football.py` remains separate from generation.

## GitHub Pages

This project is designed for its own GitHub repository and project site. The workflow in `.github/workflows/pages.yml` builds and deploys the site on pushes to `main`, by manual dispatch, and on Monday, Tuesday, and Friday at 14:00 UTC. Scheduled and manual runs regenerate ESPN data on GitHub; push runs also regenerate when credentials are available, or deploy the checked-in generated JSON when they are not.

Standings and Teams include ESPN seasons 2021 through the configured current season. Each run regenerates one small `league.json` (season-specific standings) and one `teams.json` (season-specific weekly matchups and team overviews) per year. The active season also gets `home.json`. Historical data is checked in as a reproducible snapshot, while GitHub Actions refreshes it from ESPN when secrets are present. No browser request uses ESPN credentials. Team IDs are meaningful **within a season**; do not infer permanent franchise identity across years.

`teams.json` includes normalized matchups so later H2H and Record Book exporters can use source data directly. It marks single-team playoff entries as byes with no opponent. Historical player rosters are intentionally omitted: ESPN's season-end roster does not prove who was rostered in an earlier week. A later player-history feature should use historical box scores for that purpose. Manual logo overrides currently apply only to the configured active season because ESPN can reuse a team ID for a different historical team.

1. Create a separate GitHub repository for Pocky Football and push this folder to its `main` branch. Never add `.env`.
2. In repository **Settings → Secrets and variables → Actions**, create repository secrets named `ESPN_S2` and `SWID`.
3. In **Settings → Pages**, select **GitHub Actions** as the build and deployment source.
4. Run the workflow from **Actions → Build and deploy Pocky Football → Run workflow**, or push to `main`.

The Vite base path is derived from GitHub's repository name, so assets, JSON, logo overrides, and hash navigation work under `https://<owner>.github.io/<repository>/`. A local build uses `/`; set `VITE_BASE_PATH=/repository/` to test the project path locally. The Pages artifact contains only the static frontend and generated JSON, never the repository's `.env` or the Actions secrets.
