# Team of the Week refresh and lineup card

## Cause and correction

The exporter already rebuilt Team of the Week before validation, persistence and
Pages deployment. Weeks 5–7 were `unavailable`, rather than stale files: one missing
score anywhere in the weekly roster pool rejected the entire week. The committed
2026 data has 11, 17 and 16 unscored roster entries in those weeks, primarily bench
and IR players. No conflicting numeric scores or duplicated roster players were
found in those weeks.

The builder now uses reliable actual player-scoring data when a lineup score is
missing; otherwise it excludes that candidate without inventing a zero. It still
requires complete nonempty team roster snapshots, rejects conflicting scores or
duplicated roster identities, and only optimizes fully completed matchup weeks.
The optimizer and league scoring remain unchanged: QB, RB, RB, WR, WR, TE, FLEX,
D/ST, K; unique players; maximum total over the reliable recorded scoring pool.
Coverage records the number of excluded unscored roster players. This is an
optimum over recorded actual scores, not a claim about players without statistics.

## Same-generation refresh and release checks

`football_exporter.generate` continues to call `build_team_of_week` after source
and dependent exports, including in active-only refreshes. `data_refresh.validate`
now independently derives the active season's result from those same inputs and
rejects a mismatching `team-of-week.json`. This covers missing completed weeks,
stale points, incomplete-week results and stale player imagery. The deterministic
source hash and algorithm version help diagnose source changes. Existing whole-
release hashes include this file; normal persistence still stages only generated
JSON, rejects advanced main/rejected pushes and verifies the public generation.

The one-time offline repair rebuilds cached Team of the Week outputs for 2021–2026
and updates the release hashes/generation ID while preserving the actual last
successful ESPN fetch timestamp. No ESPN request or historical source regeneration
is needed. `python football_team_of_week.py` performs this offline repair; routine
scheduled/manual ESPN refreshes continue to rebuild automatically through the
exporter and do not depend on running that command separately.

2026 Weeks 1–7 are available; Week 7 totals **244.28 FPTS**. Week 8 is incomplete
and has no finalized lineup. Each historical season 2021–2025 has all 17 completed
weeks available. Previously available lineups retain their exact selected players,
slots and totals. Only Team of the Week JSON and release metadata change; archived
league, team, draft, activity, lineup and scoring files are untouched.

## Shared presentation

`TeamOfWeek.jsx` is shared by Scoreboard and Home. Home places it after all existing
recap content inside the Weekly/Playoff Recap, using `home.recap.week`, never the
current incomplete week. Scoreboard uses the selected season/week and hides it
for unfinished weeks. Missing data has a loading state and a concise unavailable
message; switching seasons cannot expose a previous season's loaded result.

Basketball Brawl's `Recaps.jsx` lineup and design system were inspected read-only.
The football adaptation uses one compact roster card, nine full-width rows,
position labels, shared player portraits/fallbacks, defense team logos, optional
existing profile links, NFL team/position and tabular weekly scores. The header
shows Total Fantasy Points. Pocky Football typography and green branding remain.
`PlayerPortrait.jsx` shares the existing Players imagery behavior rather than
introducing a second image system. No basketball files were modified.

## Validation

Tests cover real committed 2026 and historical data, recovery of missing lineup
scores, unknown candidate exclusion, nine valid unique slots, bench eligibility,
completion gating, deterministic derivation, stale derived-file rejection, and a
staged new-final-week refresh with persisted freshness hashes and a no-change
repeat. React checks include Home recap placement, selected week/season, missing
contracts, player links, defense marks and broken-image fallbacks.

Browser checks include Home Week 7, Scoreboard Week 7, hidden unfinished Week 8,
2021 Week 1, desktop, 390px and 320px widths. The lineup has nine rows; document
width equals viewport width and no lineup row overflows at both mobile widths.
No browser runtime errors were observed. Deployment verification compares actual
public source JSON to the persisted generation, not just a green build.
