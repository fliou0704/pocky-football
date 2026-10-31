# Stage 1: lightweight live refresh and controlled pilot

## Scope and rollout

PR #28's infrastructure audit is incorporated on main. Stage 1 retains GitHub Pages and the existing Mon/Tue/Fri 14:00 UTC full-refresh schedule. Five-minute and one-minute polling are not enabled. Basketball Brawl is untouched.

The implementation is split into a collector/scheduler PR and a browser/workflow pilot PR. Automatic activation defaults to **disabled**. There was no active NFL game window during the initial Saturday-morning checks, so this is not evidence of a successful live-game production pilot. Publication results are recorded below as controlled checks become available.

Collector/scheduler [PR #29](https://github.com/fliou0704/pocky-football/pull/29) and browser/workflow [PR #30](https://github.com/fliou0704/pocky-football/pull/30) are merged. The repository pilot variable was checked and is absent, so the quarter-hour job remains disabled. Local verification passed **201 Python tests**, **115 frontend tests** (40 Node + 75 Vitest), and the production build. Desktop roster labels and mobile scoreboard scores were verified with a replayed authentic source response and subsequently on the public site; the mobile page was 390 px wide with no horizontal overflow or broken images. The replay was confined to ignored build output and was replaced by the clean production build.

### Controlled production results (October 31, 2026)

- [Code-only deployment 41190338891](https://github.com/fliou0704/pocky-football/actions/runs/41190338891) passed tests, release validation, rollback guard and public verification without fetching fantasy data.
- [Manual live publication 41190371506](https://github.com/fliou0704/pocky-football/actions/runs/41190371506) succeeded: **one fantasy GET, 341,600 decoded bytes, 0.2048 s HTTP collection, 0.0129 s collector processing, 2.450 s refresh including staging/validation, 38 s runner job**. Exactly `live.json` and `refresh.json` were persisted in commit `8a066616b6fd1deac459bebde009b23fc631b3a1`; comparing that commit to the implementation base confirms no historical or full-snapshot file changed.
- Its public generation is `655856a00d0853d77bb22a32fd24d8536ee0d422432b45931b1b71603b0fe6c5`. Fetch timestamp 09:52:32.550930 UTC → exact public hash verification 09:52:55.775087 UTC: **23.224 seconds**. This is a single healthy observation, not a guaranteed latency percentile.
- [Unchanged manual repeat 41190527613](https://github.com/fliou0704/pocky-football/actions/runs/41190527613) succeeded: one fantasy GET, 341,249 decoded bytes, 0.1578 s collection, 2.902 s total refresh, **19 s runner job**. Same generation/commit retained; Node installation, build, persistence and deployment all skipped.
- [Read-only schedule check 41190594820](https://github.com/fliou0704/pocky-football/actions/runs/41190594820) succeeded: three public NFL requests, 226,411 decoded bytes, 0.1607 s collection, **15 s runner job**. Reported `no-game-window`, `due=false`; no fantasy collection, build, persistence or deployment.
- Public browser verification confirmed Week 8 roster point labels, actual starter and bench scores, preserved season overview, and current scoreboard totals. Real during-game cadence, delayed Actions ticks during a slate, and actual postgame automatic reconciliation remain unverified; **automatic pilot activation is still disabled**.

## Commands and configuration

```sh
python data_refresh.py refresh                         # existing full refresh, instrumented
python data_refresh.py refresh --mode live             # stage/validate one current-week overlay
python data_refresh.py refresh --mode live --dry-run   # temporary copy only; no persistence
python data_refresh.py plan --dry-run                  # NFL calendar only, no fantasy query/writes
LIVE_REFRESH_ENABLED=true python data_refresh.py plan # due-time decision and private calendar state
python data_refresh.py complete --mode live           # record accepted collection, only after success
```

`--state` optionally changes the private `.cache/live-schedule/state.json` location. `complete --mode full` also records reconciled finals. An unchanged successful collection counts as success for duplicate prevention. A failed collect/deploy does not. Workflow `auto` uses the flag; explicit manual `live` is a controlled test, not automatic activation. Workflow `plan` performs a read-only schedule check and never publishes.

The pilot workflow, once integrated, has a quarter-hour eligibility trigger at minutes 7/22/37/52. Its job runs only if the repository Actions variable **`LIVE_REFRESH_ENABLED` is exactly `true`**. An absent variable means false. The existing full schedule remains independent. Do not set the variable until the acceptance checklist is verified in a real game window. Disable by setting it false or deleting it. There are no new secrets, accounts, paid services, or competing publishers.

## Source and data contract

One authenticated current-season request uses `mMatchupScore,mScoreboard,mStatus`, filtered to the current scoring/matchup period. It bypasses the library's four-call bootstrap and does not fetch historical seasons, playercard universes, transactions, logos, draft analysis, player profiles, records, biographies, NFL participation eventlogs, or historical rosters.

`pocky-football/live.json` is a **separate actual-scoring overlay**, not a rewrite of season-long JSON semantics. It contains league/season/week, current matchups and totals, the same response's current weekly lineups (starters/bench/IR), actual player points and injury metadata, score adjustments, `fetchedAt`, `snapshotId`, `baseGenerationId`, and hashes of its three base source files. It contains no raw ESPN response, cookies, owner IDs or private URLs. `appliedStatTotal` supplies ESPN's actual league-scored points, including an authoritative pregame zero; projections never substitute for actual scoring.

All expected teams and matchup identities must match the persisted season. Duplicate players/teams, missing starter scores, malformed totals, missing/changed starter assignments, and starter totals inconsistent with team totals beyond rounding tolerance fail closed. Commissioner adjustments are retained for reconciliation. Unknown bench scores remain null; previously verified bench values and optional player metadata survive an omission. A nonempty but changed starter layout is conservatively rejected until a full refresh supplies its new base. Empty starting slots are not silently invented.

Full refreshes continue to own standings, history, recaps, all-play, Team of the Week, records and player career data. A successful full reconciliation **removes the overlay**, recomputes full contracts normally, and publishes a full generation. Live period advancement raises `ReconciliationRequired`; workflow collection allows one explicit full fallback on that signal, rather than writing into the wrong fantasy week. Multiweek scoring/matchup period divergence also requires full reconciliation in this first stage.

## Integrity and publication

Live refresh first runs the existing full release validator on the persisted base. It then copies data into private staging, collects/normalizes the live response, and verifies that every other source/asset byte is unchanged. Only `live.json` and `refresh.json` can be promoted. Existing source hashes are reused only after the base validates and byte equality is proven. No heavy derived builder runs in live mode. A local nonblocking file lock rejects concurrent refreshes of the same directory.

`refresh.json` preserves `generationId`, all data/asset hashes, source revision, run ID and successful fetch time; adds `mode`, `baseGenerationId` and the raw-byte `liveContentHash`. The base generation is checked independently. Fetch timestamps do not change the overlay's semantic snapshot ID: unchanged data retains the previous bytes/generation and reports `changed=false`. No metadata-only commit or deployment is needed. Failed refreshes keep the last good data. Full-refresh historical and rollback validations remain intact.

The shared Pages workflow remains the only deployment path. Eligible jobs share the existing `github-pages` serialization group, moved to job scope so disabled pilot ticks cannot replace pending real deployments. Active publishing jobs are not canceled. Latest-main checkout, fast-forward-only persistence, narrow generated-file commit scope, public rollback guard and public hash verification are retained. Code pushes reuse the latest persisted data. Changed live runs still assemble the site via Vite (compilation was inexpensive in the audit), but skip repeated full frontend suites; unchanged/no-game runs skip Node setup, build, persistence and deployment entirely. Code changes run all tests/build as before. Post-deploy verification additionally checks the live JSON hash.

Actions cache retains private schedule state across serialized runs; cache loss can cause a redundant reconciliation/check, but unchanged generation suppression and latest-main/public guards still protect publication. Single 15-minute UTC slots prevent duplicate scheduler invocations. Git rejection or public verification failure does not mark the tick complete. Schedule and collector failures never imply a successful fresh release.

## Schedule decisions

The NFL public scoreboard's multi-date-range query returned HTTP 400 during verification. The implemented checker therefore uses **three supported single-date requests**: yesterday/today/tomorrow relative to UTC. This covers midnight-crossing games and the next pregame window without hardcoded NFL dates, weekdays or assumed three-hour game durations. Each decision reports first/last kickoff timestamps per UTC day. Team/roster data is not requested by the checker.

Clock-injected pure logic activates 60 minutes before kickoff, stays active while games overlap or are in progress/delayed, and continues for 60 minutes after the first observed final. Confirmed finals already observed retain that final-observation timestamp. A cold-start final more than 12 hours after kickoff does not manufacture a new hour of live polling; it can request one full reconciliation. Genuine long games observed while in progress still receive the full postgame window. Final/canceled events trigger a full reconciliation after the last active window; reconciled event IDs suppress repeats. Unobserved exact completion time is unavailable, so first-observed-final is a conservative proxy, not a claim of an actual whistle timestamp.

Postponed games leave the active fantasy window and are rediscovered at their new kickoff. Previously observed live/delayed games missing from a date bucket remain tracked, because disappearance does not prove completion. A status unresolved beyond 24 hours is flagged for attention and stops generating expensive fantasy work. An unavailable/invalid/inconsistent calendar returns `due=false` plus attention, retaining previous state. It never interprets network failure as all games final. Resumption uses fresh calendar evidence. There is no claim of an ESPN-supported schedule SLA.

UTC epoch slots handle DST and late Actions starts. No missed historical polling ticks are replayed in a burst. A Sunday with an actual gap beyond the pre/post buffers can safely pause and resume. Quarter-hour cron is best effort; queue delays and dropped scheduled runs remain possible.

## Instrumentation and measurements

`football_http.py` observes shared `requests.Session.send`, including pinned-library calls and worker threads. Logs retain static categories/views, counts, failed attempts, explicitly tracked bounded-client retries, 304s, HTTP cache hits, measured decoded bytes, separate Content-Length bytes, aggregate request seconds, union-of-HTTP collection wall time and non-HTTP generation/processing wall time. Separate total-refresh timing includes staging and validation. Full exporter retries implemented internally outside the new bounded client are counted as HTTP attempts but not reliably identified as retries. Logo archive/negative-cache and headshot-verification local hits are explicitly counted. Streamed image bodies not yet consumed are not forced into memory just for metrics; Content-Length is reported where available. These byte measures are not a claim of exact compressed network usage.

No arbitrary endpoint path, query, request headers, response body, credentials or exception URL is included in summaries. They are compact JSON in logs and GitHub step summaries. `get_json` uses 5-second connect / 20-second read timeouts, at most two attempts for timeout/connection/5xx, and no retries on 401/403/429. Authenticated requests do not follow redirects. Rate limiting stops the operation; numerical sustained ESPN limits remain unknown. The existing full library's behavior is observed without changing its request semantics.

| Metric | Audited full refresh | Optimized live dry run |
|---|---|---|
| ESPN calls | ~106, source-derived and sampled | **1 measured fantasy GET** |
| Upstream decoded data | 35–50 MB estimate, compressed transfer unmeasured | **341,249 bytes measured** |
| Collection wall | Not separately instrumented in old logs | **0.3003 s measured** |
| JSON/non-HTTP generation inside collector | Not separately measured | **0.0705 s measured** |
| Export + staging/validation | 27.10–34.32 s in CI | **6.026 s measured locally** |
| Runner total | 118–185 s measured | 38 s changed / 19 s unchanged measured in Actions |
| Confirmed public availability | Variable, ~118 s after recorded fetch in scheduled audit sample | 23.224 s from fetch to public exact-hash confirmation |
| Derived builders | Full cross-season rebuild | None |
| Changed files | Last full commit changed 557 | At most two: overlay and metadata |
| Historical/base sports sources | Current-only full export reuses history | Every base source/asset byte remains unchanged |

This is a >99% request reduction for **collector calls**, not the entire orchestration: each schedule gate adds three cheap public NFL reads. The final dry run used a real authenticated response and validated in a temporary copy; it did not persist/publish. An earlier prototype took 23.442 seconds because it redundantly rehashed the full site; that was fixed before rollout. No full ESPN export was rerun for comparison; the audit remains the full baseline.

Schedule dry run measured three HTTP 200s, 226,372 decoded bytes, 0.2957 seconds collection and 0.3421 seconds total; no fantasy call, no active window, no state write. These local observations are not latency percentiles.

## Browser compatibility and next-stage readiness

The small frontend adapter reads release metadata once per route load, uses a generation-keyed/no-store live fetch, verifies its raw-byte hash and base ID, and verifies the relevant base-file byte hashes before applying anything. Home totals, Scoreboard totals, current roster assignments and week points share one overlay. Historical seasons, standings, career histories and derived recaps retain full-snapshot semantics. A mismatched or unavailable optional overlay falls back to full data instead of breaking the site. Rosters preserve known season points internally and label displayed live points by week.

There are **no polling timers**. An already open tab still needs navigation/reload; browser auto-refresh is the next stage. For that stage, check a compact generation pointer, then reload `live.json` and the hash-pinned base files (`{season}/league.json`, `teams.json`, `home.json`) only if its base generation changes. Current weekly lineups are carried inside `live.json`; no separate fetch is necessary for this overlay. Full recaps/weekly/TW files should update only with their reconciled full generation. Keep selected route/season/week/team outside refreshed data state. Existing ten-minute caching on mutable Pages files is handled for the compatibility adapter by explicit revalidation/no-store and hash checks, but no global CDN timing guarantee is introduced.

## Pilot acceptance and usage

Completed offline checks cover weekdays and unusual kickoff hours, pre/post boundaries, DST, late invocations, overlap/gaps, early/late finals, postponement/rescheduling, delayed/suspended games, no-game periods, schedule failure, duplicate prevention, actual committed team identities, score/roster consistency, partial failures, missing bench metadata, unchanged snapshots, full reconciliation, base integrity, request redaction, cache counters, bounded retries, local concurrency and existing stale Git/public guards. Follow-up edge checks ensure unknown view/query values cannot leak into metrics and redirected response bodies are not counted twice. Complete Python/frontend/build results and controlled publication are recorded above.

Before activation: verify correct current scores, substantially reduced requests, no routine overlaps/backlog, persisted JSON, correct public generation, code-only rollback protection, untouched historical bytes, idle skip, retained last-good release on errors, and actual runner/API metrics. A controlled off-window manual publication can verify mechanics; it cannot satisfy real game-window acceptance. Keep the flag false until that missing evidence is obtained.

If enabled for 24 active hours/week: ~96 live ticks, 672 quarter-hour eligibility checks (~2,016 public NFL requests), three existing baseline full runs, and roughly three postgame reconciliations. Collector load is ~96 fantasy calls plus ~636 ESPN calls from six full runs, excluding conditional image/recovery traffic. Only changed ticks deploy/commit. At 28 active hours live ticks rise to ~112. Every idle check still has Actions setup overhead; the measured cost is included below. This public repository uses free standard Actions runners, but artifact/cache/Git growth and CDN latency still need monitoring.

Updating that model with the controlled **15 s idle / 19 s unchanged / 38 s changed** jobs gives approximately **190–225 runner-minutes/week**, assuming 24 active hours and six full reconciliations at the audited 3.1 min each; code deployments, queue delay and longer propagation are additional. Expected decoded upstream processing is roughly **0.4–0.5 GB/week** using the estimated full-refresh bytes and measured gate/live bytes. There are at most ~96 live data commits/deployments plus full runs; unchanged ticks reduce this count. These remain projections from a small sample, not observed weekly pilot usage. With the flag disabled, no quarter-hour job allocates a runner or makes these requests.

Next: conduct one supervised real-window 15-minute sequence, including an unchanged tick and postgame reconciliation. Measure fetch-to-public and browser-visible age; only then enable the repository flag. Five minutes requires measured confidence in runtime/queues and upstream tolerance, not just changing cron. Automatic browser generation polling remains a separate, narrowly scoped follow-up.
