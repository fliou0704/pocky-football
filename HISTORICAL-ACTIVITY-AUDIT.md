# Historical activity and draft audit

Validated against live ESPN on 2026-10-01. Backend-only changes; no site features or presentation changed. The 2026 season is an in-progress snapshot through transaction period 4, not a complete future season.

## Season summary

| Season | Draft picks | Actual draft order? | FA adds | Waiver adds | Standalone drops | Trades | Total activity | Coverage assessment |
|---|---:|---|---:|---:|---:|---:|---:|---|
| 2021 | 160 | Yes | 114 | 57 | 38 | 1 | 370 | Likely complete; acquisition boundary differences |
| 2022 | 224 | Yes | 130 | 63 | 46 | 1 | 464 | Likely complete; acquisition boundary differences |
| 2023 | 192 | Yes | 103 | 38 | 27 | 1 | 361 | Likely complete; acquisition boundary differences |
| 2024 | 160 | Yes | 123 | 77 | 25 | 3 | 388 | Likely complete; acquisition boundary differences |
| 2025 | 160 | Yes | 104 | 52 | 26 | 1 | 343 | Likely complete; acquisition boundary differences |
| 2026 | 160 | Yes | 11 | 9 | 2 | 0 | 182 | Independent counters match (snapshot) |

Counts describe transaction events. An acquisition with an associated drop remains one event. Standalone drops exclude those associated drops and trade departures.

## Authoritative draft boards

ESPN league `mDraftDetail` (with `mSettings`) returned every board. Dedicated season-scoped `draft.json` preserves source overall pick number, round, pick within round, drafting team/player, player name, keeper/reserved-for-keeper flags, initial lineup slot, source auto-draft code, and draft timestamps. `draftSlot` is the team’s original position in `settings.draftSettings.pickOrder`; it differs from even-round `pickInRound` in a snake draft. No order is inferred from transaction timestamps. Private draft member/selection identifiers are omitted.

All six drafts are snake drafts, have zero configured keepers, and disable draft-pick trading. Auction budget configuration exists even for snake leagues; zero source bid amounts are not treated as auction purchases. Auction/nominator fields are null. Expected 16 rounds come from nine active slots plus seven bench slots, excluding IR/ER. Every board has contiguous unique overall selections, valid round arithmetic, snake team order, unique drafted players, 16 picks per team, and exact agreement with normalized draft assignments.

| Season | Teams × rounds | Picks | Complete board |
|---|---|---:|---|
| 2021 | 10 × 16 | 160 | Yes |
| 2022 | 14 × 16 | 224 | Yes |
| 2023 | 12 × 16 | 192 | Yes |
| 2024 | 10 × 16 | 160 | Yes |
| 2025 | 10 × 16 | 160 | Yes |
| 2026 | 10 × 16 | 160 | Yes |

## Source coverage and reconciliation

Queried `mTransactions2` explicitly for periods 0–20 in completed seasons (observed transaction/latest period 19 plus a boundary probe), and 0–5 in 2026 (observed period 4 plus boundary probe). Every request succeeded. Requested periods can clamp to the latest period: a boundary response containing old transactions is not evidence of new future activity. Transactions after fantasy week 17 were recovered in 2021 and 2022; empty later periods in other seasons are recorded as successful responses.

Unfiltered season-filtered `kona_playercard` returned the entire ESPN-exposed player universe, including players absent from known fantasy rosters. No known or transaction-referenced player was missing. The collector also supports targeted fallback and counterpart checks. This materially closes the earlier known-player-only coverage risk, although deleted/unexposed archived records remain impossible to disprove.

| Season | Returned player universe | Unique period IDs | Unique card IDs | Repeated ID appearances merged | Card-only executed trades |
|---|---:|---:|---:|---:|---:|
| 2021 | 1119 | 473 | 370 | 497 | 1 |
| 2022 | 1136 | 585 | 464 | 615 | 1 |
| 2023 | 1132 | 458 | 361 | 470 | 1 |
| 2024 | 1099 | 547 | 388 | 558 | 3 |
| 2025 | 1091 | 462 | 343 | 472 | 1 |
| 2026 | 1050 | 268 | 182 | 225 | 0 |

Canonical public identities hash the source transaction ID. Repeated appearances across periods and player histories merge by the same ID, preferring rich executed transfer payloads. Core movement fields are compared independently of source-specific extra fields. Exact semantic signatures include season, timestamp, type, scoring period, team/player changes and FAAB. Different IDs with identical signatures are flagged for review, never silently collapsed. Later re-adds remain separate events.

Every executed trade appears only in player histories under its executed ID. The period feed has a separate acceptance placeholder with no executed status or player transfers. Those placeholders are excluded rather than counted as duplicate trades. There were zero conflicting executed movement payloads.

Comparison with the pre-task `main` activity files: **zero duplicate IDs, zero semantic duplicate groups, zero newly discovered executed events, zero removed events**, in every season. Earlier Stage 2E reconciliation already recovered all seven trades. The improvement is authoritative draft detail, explicit transfer edges and stronger validation/coverage.

Historical communication endpoints were tested and unavailable; the current feed was paginated and is corroborative only. Communication messages do not become executed transactions.

### Independent counters

`mTeam.transactionCounter` exposes independent team acquisitions, drops, trades and per-period acquisition totals. All drop and trade totals agree for every team in all six seasons. All acquisition totals agree in 2026. Historical acquisition counters undercount the observed executed acquisitions only at season boundaries:

| Season | Team: observed minus source acquisitions | Periods of differences |
|---|---|---|
| 2021 | 10: +1 | 18 |
| 2022 | 6: +1, 7: +3, 10: +1 | 1, 19 |
| 2023 | 2: +1, 5: +3, 6: +1, 12: +1 | 1 |
| 2024 | 2: +1, 3: +1, 6: +2, 11: +1, 16: +1 | 1 |
| 2025 | 1: +1, 2: +1, 3: +1, 12: +2 | 1 |
| 2026 | None | None |

The period-by-period comparison agrees everywhere else. ESPN does not document these counter boundary/reset semantics; they are plausible preseason/postseason exclusions, **not a proven explanation**. Inspecting `skipTransactionCounters` did not establish a skip flag explanation. No missing movement was found, and observed totals exceed rather than fall below counters. Accordingly 2021–2025 are `likely_complete` with `complete=false`; 2026 is `independently_verified_counts` with `complete=true` only for the stated snapshot and player-movement scope. Count agreement is not proof of all historical metadata or an independent event-by-event ledger.

## Transaction semantics

- `EXECUTED` status is authoritative. Archived executed trades may still have `isPending=true`; that stale flag does not exclude them.
- Draft assignments, FREEAGENT ADD, WAIVER ADD, standalone DROP and TRADE transfers map to the five normalized categories. ADD+DROP stays grouped under its source ID.
- Waivers preserve source execution type (`PROCESS`) and processed UTC timestamp. Free-agent/draft/drop timestamps generally use proposed time because ESPN exposes no process time; `timestampKind` makes this explicit.
- None of these seasons uses FAAB. Source bid fields in non-FAAB leagues are not actual payments; normalized `faab` remains null. Historical waiver rank is not exposed; raw rating zero is not labeled as priority, and current team waiver rank is not substituted.
- Failed waiver claims, canceled requests and pending requests are available in period responses. They are excluded from public executed activity; safe aggregate type/status counts are retained in coverage.
- ROSTER/FUTURE_ROSTER lineup/IR changes, trade proposals/declines/veto/uphold workflow records do not count as executed player ownership movements.

## Every executed trade

### 2021 — week 4 — 2021-09-28T16:51:37.567000+00:00

- Dookey  Kong (team 10) → Turkey Eren (team 9): Sony Michel.
- Turkey Eren (team 9) → Dookey  Kong (team 10): Devin Singletary.

Status: executed. All player departures and arrivals balance. Source trade items contain zero draft-pick and budget transfers; no other asset was observed.

### 2022 — week 11 — 2022-11-15T20:20:12.518000+00:00

- Its Bigger Than Black or White✊ (team 6) → semanto gay and kissed allen  (team 12): Isiah Pacheco.
- semanto gay and kissed allen  (team 12) → Its Bigger Than Black or White✊ (team 6): AJ Dillon.

Status: executed. All player departures and arrivals balance. Source trade items contain zero draft-pick and budget transfers; no other asset was observed.

### 2023 — week 3 — 2023-09-24T02:18:38.679000+00:00

- Turkey Eren (team 9) → Eren's Fantasy Football Team (team 5): Amon-Ra St. Brown.
- Eren's Fantasy Football Team (team 5) → Turkey Eren (team 9): James Conner.

Status: executed. All player departures and arrivals balance. Source trade items contain zero draft-pick and budget transfers; no other asset was observed.

### 2024 — week 5 — 2024-10-01T07:00:00+00:00

- Tee Time (team 6) → semanto gay and kissed allen  (team 12): Derek Carr.
- semanto gay and kissed allen  (team 12) → Tee Time (team 6): Austin Ekeler.

Status: executed. All player departures and arrivals balance. Source trade items contain zero draft-pick and budget transfers; no other asset was observed.

### 2024 — week 5 — 2024-10-01T07:00:00+00:00

- semanto gay and kissed allen  (team 12) → Tee Time (team 6): Justin Tucker.
- Tee Time (team 6) → semanto gay and kissed allen  (team 12): Matt Prater.

Status: executed. All player departures and arrivals balance. Source trade items contain zero draft-pick and budget transfers; no other asset was observed.

### 2024 — week 7 — 2024-10-16T23:14:46.422000+00:00

- Tee Time (team 6) → semanto gay and kissed allen  (team 12): Austin Ekeler, Davante Adams.
- semanto gay and kissed allen  (team 12) → Tee Time (team 6): Brian Thomas Jr., Joe Flacco.

Status: executed. All player departures and arrivals balance. Source trade items contain zero draft-pick and budget transfers; no other asset was observed.

### 2025 — week 1 — 2025-09-04T03:40:06.724000+00:00

- semanto gay and kissed allen  (team 12) → if u got me get rid of me (team 6): A.J. Brown, Kyren Williams, Stefon Diggs.
- if u got me get rid of me (team 6) → semanto gay and kissed allen  (team 12): Josh Jacobs, Xavier Worthy, DeVonta Smith.

Status: executed. All player departures and arrivals balance. Source trade items contain zero draft-pick and budget transfers; no other asset was observed.

All seven observed trades involve two teams. Transfer edges support three or more participants and are tested, but no actual multi-team trade occurred in this league. No partially reconstructed trade was found.

## Ownership and roster checks

Chronological movement checks cover every draft arrival, add, drop and trade. Transfers apply atomically, and later re-acquisitions are counted separately. Zero owner-origin mismatches or already-owned acquisitions were found. Independently, every player in every saved weekly roster is checked against possible owners within that scoring period. This avoids guessing the exact timestamp of archived roster snapshots. **16,153 roster entries** across weeks 1–17 of 2021–2025 and weeks 1–3 of 2026 passed, with zero anomalies. This is a sanity check, not a precise full-season roster reconstruction.

## Remaining limitations

1. **Confirmed missing:** no missing executed player movement or draft selection was identified. Historical communication access is unavailable. Exact processed timestamps are absent on many otherwise executed instant/draft/drop records; proposed timestamps remain explicitly labeled.
2. **Not exposed in the tested sources:** historical waiver priority, precise weekly roster-snapshot timestamps, an authoritative full event ledger independent of these sources, and undocumented acquisition-counter boundary/reset rules. No actual FAAB/auction/keeper/draft-pick-trade data exists for these six configurations. Other leagues’ asset formats are unverified.
3. **Apparently complete but not independently proven:** 2021–2025 acquisitions/waivers because boundary counters differ. Drop/trade counts independently match throughout, and all recovered events pass source/roster checks; archived omissions or compensating errors cannot be mathematically ruled out. The unfiltered player universe covers ESPN-exposed players, not provably every deleted historical player. 2026 coverage ends at the export snapshot.

## Contracts and refresh

- `activity.json` schema 2 preserves existing event IDs/categories/team movements and adds directed trade `transfers`, safe asset observations, validation, source/counter coverage and draft summary.
- `draft.json` schema 1 is the authoritative board; draft position is not duplicated into timestamp-based activity records.
- `python3 football_activity_exporter.py --league pocky-football` refreshes only activity/draft contracts using the existing environment credential configuration. The regular exporter also generates these contracts. No new frontend dependency is introduced.
- Source failures preserve prior movements as stale and never assert fresh completeness. Failed draft refresh is explicitly marked rather than presenting an older board as newly validated.

## Verification

Full relevant Python suite: **59 tests passed**, including generated six-season contracts, draft count/order/round checks, negative NFL defense IDs, exact semantic duplicate detection, genuine repeated moves, source reconciliation/conflicts, multi-team transfer balance, counter coverage gates, ownership/roster anomalies, and private field exclusion. Credentials remain environment-only and `.env` is ignored. No frontend source, Record Book output, deployment or publication was changed.
