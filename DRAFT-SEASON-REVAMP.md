# Individual Draft season revamp

Scope: individual Draft seasons 2021–2026. The feature branch is based on merged PR #17 at `34e9800`, preserving the integrated branding, shared matchups, Scoreboard, Team of the Week and Summary cleanup. All analysis uses committed data; no ESPN request or Pages-setting change is required.

## Candidate comparison

`football_draft_standouts.compare_methods` evaluates every completed draft round from 2021–2025: **80 rounds**. Two candidates were compared before selecting the round-value rule:

1. **Raw positional draft-slot gain:** actual overall pick minus the actual overall pick of the Nth player drafted at the same position, where N is final positional rank. Interpretable but favors the larger absolute gain even when an earlier selection delivers a greater proportional improvement. Ties can arise solely from equal raw distances.
2. **Relative positional draft-slot gain:** the same gain divided by the original overall pick. This is a proportion of an ordinal draft-slot number, not a claim about dollars, economic capital or added fantasy points. It has no fitted weights, bonuses, thresholds or position-specific parameters. Higher is better, and positive/negative retain their meaning. Exact rational arithmetic determines ties.

Raw gain and relative gain select different leader sets in **8 of 80 rounds**. Examples:

| Season / round | Raw-gain leaders | Relative-gain leader |
| --- | --- | --- |
| 2021 / 2 | Najee Harris: +17 at pick 20 (85.0%) | Jonathan Taylor: +12 at pick 13 (92.3%) |
| 2021 / 6 | Josh Allen: +46 at pick 56 (82.1%) | Mark Andrews: +44 at pick 52 (84.6%) |
| 2024 / 12 | Chuba Hubbard: +94 at pick 120 (78.3%) | Chase Brown: +90 at pick 112 (80.4%) |
| 2025 / 2 | Christian McCaffrey / Jonathan Taylor: +15 each | Christian McCaffrey: +15 at pick 16 (93.8%) |

For context, the old raw-FPTS rule selected quarterbacks in 40 of 80 rounds. Relative gain selects QB in 5, RB in 35, WR in 33, TE in 6 and K in 1. These are descriptive results, **not proof of complete positional neutrality**. Relative gain still reflects positional draft depth, roster/scoring rules and available benchmarks. It compares picks only within their round and does not rank all seasons or rounds together.

## Selected method: two separate, explicit roles

The **Draft value standout** maximizes:

`(actual overall pick - positional benchmark overall pick) / actual overall pick`

The displayed percentage is that proportion × 100. It supplements the existing raw draft-slot gain; it does not replace or alter it. A negative winning result means the least-negative available proportional result, not a positive return.

A separate **Best positional finish** recognition goes to the lowest final positional rank in the round. All ties are shared. When a value winner also has the best positional finish, that role is noted on the same card instead of duplicating the player. This is deliberately **not a weighted composite or a single ordered list of incomparable accomplishments**. The value role measures draft-order improvement; the finish role recognizes absolute positional excellence.

This treats elite early picks honestly: a first overall pick who finishes as the league points leader necessarily finishes first at their position and receives best-finish recognition even with zero gain. An early QB finishing QB1 or QB2 can similarly receive the best positional-finish recognition if that is the best finish in their round. High QB points alone never determine either role. A zero-gain player is not falsely described as a draft-slot bargain, and a later breakout does not erase their exceptional outcome.

No committed first overall selection in 2021–2025 is the league points leader, so that precise hypothetical is tested with a focused fixture. The real **2023 Christian McCaffrey**, drafted third overall, finished RB1 with **391.3 FPTS and zero draft-slot gain** and now receives finish recognition alongside the value winner. The real 2024 first overall McCaffrey has no valid benchmark and is not assigned an invented gain. All first-round results were evaluated, including the injured/disappointing first selections.

### Committed 2025 Round 3

| Player | Pick | Final position | Season FPTS | Benchmark pick | Gain | Relative gain |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Jaxon Smith-Njigba | 30 | WR2 | 345.50 | 3 | +27 | **90.0%** |
| James Cook III | 29 | RB6 | 300.70 | 15 | +14 | 48.3% |
| Trey McBride | 28 | TE1 | 302.40 | 21 | +7 | 25.0% |
| Josh Allen | 26 | QB1 | 364.62 | 25 | +1 | 3.8% |

**JSN is the value standout. Allen and McBride share best positional finish.** No player names enter the selection algorithm. Raw QB fantasy points no longer decide the draft-value award.

## Missing and provisional outcomes

The existing benchmark function is unchanged. Final rank beyond the drafted positional pool, fractional tied rank or missing rank means no exact Nth selection: no benchmark or gain is fabricated, and that pick is excluded only from the value component. A known final positional rank can still qualify for best-finish recognition. If no direct benchmarks exist, only the finish role is available. Unknown scoring withholds that round's standout comparison. Incomplete seasons withhold both roles until final rankings qualify. All original picks, including unavailable outcomes, remain in the draft-order table.

Best-finish comparisons have their own limits: ranks at positions with different pool sizes are not equal point values, and best finish in a weak late round does not imply an elite NFL season. The label is relative to that round; it is not an arbitrary QB1 bonus or cross-position FPTS comparison.

## UI and invariants

The season information note and diagnostic section are removed. Overall Performance reuses Summary's accessible expandable-row component, showing team/manager and Average Round Rank ascending. Its inline details contain only that manager's season picks with historical team identity intact. Each table permits one expanded manager at a time. Round panels retain every pick in original order; FPTS rank remains clearly labeled as a points-only comparison. Standout cards show player, position, fantasy team/logo, season points and the reason for recognition.

The Summary contract is unchanged. Existing canonical player rows, team/position calculations, riser/faller arrays, Full Draft Board data and gain/loss formulas are unchanged. Existing `round.leaders` remains available as the raw-points leader data for compatibility; season UI now uses the new `round.standouts` annotations. This preserves Summary round ranks, wins and any downstream consumers rather than silently redefining them. No gain/loss/board label, layout or default order changes.

## Validation

Run `python -m unittest discover -s tests -v`, `pnpm --dir frontend test`, and `VITE_BASE_PATH=/pocky-football/ pnpm --dir frontend build`. New tests cover all completed rounds, first-pick and early-QB cases, actual JSN/Allen/McBride results, ties, missing benchmarks, D/ST/small-pool outcomes, missing scoring, provisional seasons, original order, attribution and non-mutation. UI tests render all six season pages, shared inline manager details, removed sections, exact protected table headers/order and missing-standout handling. Summary and Scoreboard regression tests remain in the full suite.
