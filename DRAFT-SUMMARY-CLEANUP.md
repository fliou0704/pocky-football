# Draft Summary cleanup and Cloud synchronization

## Synchronization and preservation

Work started on `codex/draft-v2` at `7693724`, ten commits behind fetched `origin/main` (`b6a5000`, PR #16). There were no local-only commits. Four tracked branding edits and four untracked branding files were backed up in `/private/tmp/pocky-branding-backup-20261029/` as an archive, binary patch, and SHA-256 manifest, and in the retained Git safety stash named `Safety backup: local team branding before Cloud synchronization 2026-10-29`.

The feature branch `codex/draft-summary-cleanup` starts from `b6a5000`. Conflicts were integrated, not selected wholesale: the local team renderer moved into Cloud's shared `Match.jsx`, alongside a single exported `BrandingSeason` context. The app imports that context and retains Cloud's Scoreboard routing, data loading, matchup components and Team of the Week. Season-specific Teams/H2H branding and the local manual override resolver/tests/config/documentation were preserved. The fallback remains manual image → automatic ESPN image → team initial. No history was rewritten and the safety stash was not dropped.

## Summary-only behavior

The introduction is exactly **Summary only includes current managers**. Summary branding is resolved from latest-season standings through the existing manager mapping, including an unfinished season. Historical pick identities remain untouched.

Overall Round Performance and each historical round show only manager/team and the mean of actual within-round performance ranks, sorted ascending (unknowns last). No normalized round score or positional metric contributes to this mean.

Positional tables retain Cloud's existing positional benchmark formula: actual overall pick minus the actual overall pick of the Nth player drafted at that position, where N is final positional rank. The Brees example (pick 100, finish QB5, QB5 drafted at 67) yields +33. Fractional tied ranks, missing ranks and ranks beyond the positional draft pool have no invented reference. Each position shows mean gain among available actual benchmarks; unavailable outcomes remain visible in inline details with their reason. No FPTS-above-expectation column or composite score remains in Summary. Year-specific calculations required by individual-year views remain intact.

Draft Tendencies retains raw mean round and mean first overall pick, with the label Avg First Pick. QB/TE sort by mean first pick; RB/WR/K/D/ST sort by mean round. First picks still receive one vote per manager/position/season. Rookie Selections by Manager is inside Draft Tendencies, sorted by rookie count descending. Other Summary rookie/timing analyses and their exclusive calculations were removed.

A single shared expandable manager-table component serves overall, positional, tendencies, rookie and round tables. Clicking any manager-row cell toggles inline canonical pick details. Native keyboard buttons expose expanded state and controls IDs. Each table keeps at most one expanded manager; different tables are independent. Expanded picks scroll inside the table; no evidence navigation is required. All historical rounds open to every eligible current manager.

## Verification

Rebuild analytics offline with `python football_draft_analysis.py`. Compare the resulting `seasons` and `audit` objects to the parent committed JSON: both remain exactly equal. No ESPN data was requested and no workflow was dispatched.

Run `python -m unittest discover -s tests -v`, `pnpm --dir frontend test`, and `VITE_BASE_PATH=/pocky-football/ pnpm --dir frontend build`. Tests cover current names/logos, manager aggregation, actual mean round ranks, positional benchmark gain, tendency/rookie sorting, historical rounds, row toggles and inline picks, committed Summary rendering, and integration of branding with Home, Scoreboard, Team of the Week, Teams and Draft.
