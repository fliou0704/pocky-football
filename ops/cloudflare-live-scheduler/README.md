# Football Cloudflare dispatch — deployment and cutover

Football Worker only: `pocky-football-live-scheduler`. Do not deploy from the
Basketball Brawl directory or alter its Worker/token/configuration.

## GitHub changes

The existing scheduler uses five-minute UTC slots. NFL game-window logic is
unchanged. `mode=auto` remains authoritative; the Worker does not query ESPN.

Live runs validate, persist `live.json` and `refresh.json` to main, assert latest
main/public rollback safety, then publish/read back Supabase. They skip Node,
Vite, Pages artifacts/deployment and public exact-generation verification.
The Git generation and full base remain recoverable across fresh runners;
Supabase retains its atomic revision/week/source-time guards. Unchanged runs
skip Git writes and Supabase writes, but still check latest main and readback.
Supabase failure now fails the live job and leaves the persisted candidate for
the next tick to retry; scheduler completion requires successful publication.
Full reconciliations and code pushes retain the existing Pages pipeline. A period
rollover may intentionally switch an auto/live attempt to full reconciliation.
Existing Pages data therefore does not track each live-only Supabase update;
the full reconciliation/code deployment supplies its next complete release.

One `github-pages` concurrency group serializes all publication jobs, with active
runs retained and pending work coalesced by GitHub. Persisted scheduler cache/UTC
slots suppress repeated completed ticks; Git and database guards remain the
correctness boundary even if a cache is lost. This is not an exactly-once
dispatch guarantee. No new Durable Object, public trigger endpoint or competing
publisher is introduced.

## Required access (not provided/deployed in this task)

- Cloudflare Wrangler login to your account, or `CLOUDFLARE_API_TOKEN` with Workers
  Scripts Edit for the intended account and `CLOUDFLARE_ACCOUNT_ID`.
- A **new/restricted fine-grained GitHub token**, selecting only
  `fliou0704/pocky-football`, repository **Actions: read/write** (metadata read is
  implicit). Store it only as Cloudflare secret `GITHUB_DISPATCH_TOKEN`.
- No ESPN or Supabase credentials in Cloudflare. Do not copy a basketball token.

From this directory, using the same Wrangler deployment approach as basketball:

```sh
npx wrangler@4.156.0 login
npx wrangler@4.156.0 deploy
npx wrangler@4.156.0 secret put GITHUB_DISPATCH_TOKEN
```

The initial deployment is disabled (`SCHEDULER_ENABLED=false`). The GitHub
repository variable `LIVE_REFRESH_ENABLED=true` must remain enabled for auto mode.
Do not paste token values into shell commands, source files, logs or chat.

## One controlled real Cloudflare dispatch and cutover

1. Start `npx wrangler@4.156.0 tail` in one terminal.
2. Enable the football Worker with
   `npx wrangler@4.156.0 deploy --var SCHEDULER_ENABLED:true`.
3. Observe its first real cron event: log `status=accepted` and a corresponding
   GitHub `workflow_dispatch` run on main using `mode=auto`. Cron propagation may
   take up to 15 minutes. If minimizing test dispatches, immediately redeploy with
   `--var SCHEDULER_ENABLED:false` after the first accepted event.
4. Inspect that run: outside NFL windows it should skip fantasy work (except a
   due postgame reconciliation); during a window it must persist valid data,
   verify Supabase publication and skip Pages for effective live mode. HTTP 204
   proves dispatch acceptance only, not successful collection/publication.
5. **Only after verified Cloudflare-origin execution**, set the GitHub repository
   Actions variable `CLOUDFLARE_LIVE_VERIFIED=true`. This disables the legacy
   15-minute eligibility job before runner allocation. Its cron declaration is
   retained for easy rollback, but cannot compete for publication after cutover.
   Full Mon/Tue/Fri cron runs remain enabled.
6. Re-enable the football Worker with the same `--var SCHEDULER_ENABLED:true`
   command if it was paused. Do not leave both schedulers enabled indefinitely.

Rollback: first deploy the football Worker with `--var SCHEDULER_ENABLED:false`,
then set `CLOUDFLARE_LIVE_VERIFIED=false` (or remove it) to restore the legacy
15-minute GitHub eligibility job. Leave `LIVE_REFRESH_ENABLED=true`. For an
emergency stop of all auto fantasy collection, also set that variable false.

## Verification

`node --test test/worker.test.mjs` tests dispatch construction, disabled behavior
and failed GitHub responses without real calls. Focused Python tests cover
five-minute eligibility, live/full/unchanged workflow paths and Supabase
unchanged/stale/invalid/readback failures. No full ESPN export is needed.

Worker deployment and Cloudflare-origin verification remain pending. The existing
15-minute GitHub job remains active until the explicit cutover flag is set.
