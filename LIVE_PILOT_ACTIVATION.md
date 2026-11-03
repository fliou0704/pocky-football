# 15-minute pilot activation — November 3, 2026

Activation uses the existing repository Actions variable `LIVE_REFRESH_ENABLED=true`.
The existing cron is `7,22,37,52 * * * *` (UTC). No workflow, scoring, frontend,
historical generator, or hosting changes are required. Existing full-refresh
schedules remain unchanged. Disable immediately by setting the variable to `false`.

The existing checker activates 60 minutes before kickoff, during live/delayed
games, and for 60 minutes after the last observed final. Dates come from ESPN,
including unusual weekdays, international starts and rescheduling. Overlapping
windows share one serialized publisher. Completed slates can request one full
current-season reconciliation; this is distinct from routine live polling.

Verification: 11 schedule tests and 12 live/HTTP tests passed; workflow YAML parsed
and the shared `github-pages` serialization group was confirmed. One schedule-only
dry run made three public NFL requests and zero fantasy requests. It identified
Monday's final and requested reconciliation. No export or publication was run by
that dry run. A live game-window deployment has not yet been confirmed.

The existing live collector uses one fantasy response and preserves the full base.
Changed live data still requires Vite assembly and a complete Pages deployment;
unchanged snapshots skip build, commit and deployment. Previously measured changed
jobs took 38 seconds, with public hash confirmation 23 seconds after collection;
these observations fit a 15-minute pilot but are not latency guarantees.

Staging validation, stable generation hashes, latest-main/public rollback guards,
Git persistence and unchanged-data suppression are retained. The repaired full
refresh was verified in run 41657345401. No five-minute activation or browser
polling is included. Monitor scheduled decisions, API counts, publication latency
and failures before considering a five-minute cadence; Actions cron delays and
full-site deployment overhead remain limitations.
