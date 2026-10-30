# Weekly league stories

`football_weekly.py` derives one `SEASON/weekly.json` per season from committed
`league.json`, `teams.json`, and weekly lineup snapshots. It makes no ESPN calls.
The exporter rebuilds these contracts after its existing normalized data and
Team of the Week steps. Release validation independently derives and compares
all six season contracts before promotion. The refresh schedule, staging,
persistence, rollback guards and deployment workflow are unchanged.

`WeeklyRecap.jsx` is shared by Home and Scoreboard. Home selects the newest
completed recap. Scoreboard mounts only the expanded selected week's recap,
and additionally checks the selected matchups are final. `TeamOfWeek.jsx` keeps
its existing optimal nine-player contract and displays the existing weekly
`teamId` attribution through the season-aware `Team` logo resolver. Null
ownership means Free Agent; absent/unresolvable ownership means Unknown.

## Statistical conventions

- All-play requires final, finite scoring for every team, one appearance per
  team, and complete league coverage. Regular-season weeks only. Missing weeks
  are listed in `excludedAllPlayWeeks`; future/incomplete weeks are not counted.
  Sorting uses `(wins + ties / 2) / games`, retaining official rank as the stable
  tiebreaker. The official standings order and records remain unchanged.
- Consecutive wins use actual regular-season winners. Ties, losses, byes,
  unfinished games and missing weeks break streaks. Three wins qualifies.
  First wins use actual victories, including Week 1 and postseason victories;
  uncertain earlier coverage suppresses a potentially false first-win claim.
- The leaderboard uses actual matchup points and competition ranks (1, 1, 3).
  Equal scores order by team ID; collapsed Top Team explicitly labels ties.
- Top Two Scorers requires unique first and second scores and reliable scores
  across the league. Ambiguous ties and unscored byes omit this award. Only a
  real scheduled matchup qualifies. Awards share season/week/sorted-team IDs;
  overlapping Closest Matchup and Top Two Scorers render once. Closest Matchup
  retains championship-bracket scope in playoffs; tied margins use matchup ID.
- Preview indicators render only in Home, only for upcoming/live matches.
  The generator calculates them before processing that week's results.
  Rivalries use owner-checked memberships in `draft-manager-identities.json`,
  include prior regular/playoff meetings once, and require at least one meeting.
  W–L–T includes tied meetings; a prior tied-only series can read 0–0–1.
- Official entering-week ranks are archived in `teams.enteringWeekRanks` only
  when ESPN's rank snapshot has exactly the prior regular-season W/L/T and PF,
  and no selected-week finals. Existing archives persist through refreshes.
  Week 1 and older weeks without archived official ranks omit Top Two Showdown;
  historical ranks are never guessed from season-ending standings. Week 8 of
  2026 is the first verified archive. Newly verified manager memberships require
  explicit review of the identity mapping before cross-season rivalry inclusion.

## Coverage and verification

The committed contracts cover 92 completed weeks: 17 each in 2021–2025 and
seven in 2026. All 92 have an available optimal lineup. Historical source
snapshots and optimal-lineup calculations were preserved. This offline release
updates generation hashes while retaining the last real ESPN fetch timestamp.

Validation performed:

- Full Python suite: 177 tests passed before the final release-staleness test;
  release tests rerun with the additional stale weekly-contract rejection.
- Frontend: 38 Node tests and 73 React tests passed; focused recap/Scoreboard
  checks rerun after final completion gating changes. Production build passed.
- Actual browser checks at desktop 1280px, 390px and 320px: no document overflow;
  correct recap order; full-width Top Team expansion/collapse; weekly roster
  ownership/logos; live Home previews; historical Scoreboard navigation and
  recap collapse; 2021 Week 1 first wins; 2022 Week 9 combined matchup awards;
  mobile/desktop all-play sorting with official ranks preserved.
- Temporary local Home fixtures verified upcoming preview badges and zero
  completed-matchup badges. Fixtures were removed before commit. Browser console
  was clear and loaded images showed no missing sources. Screenshots saved in
  `/tmp/pocky-weekly-desktop.png` and `/tmp/pocky-weekly-320.png`.
