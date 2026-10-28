# Draft V3 offline audit

Completed picks: 896. Active summary managers: 10.

|Position|Picks|Old mean rank movement|Mean FPTS surplus|Benchmark available|
|---|---:|---:|---:|---:|
|QB|96|-5.21|-0.0|68|
|RB|261|-9.29|-0.0|196|
|WR|327|-13.23|0.0|234|
|TE|88|-7.05|-0.0|53|
|K|59|-8.31|0.0|21|
|D/ST|65|-6.36|0.0|24|

Benchmark exclusions: {'available': 596, 'beyond_drafted_position': 237, 'fractional_tie': 63}

## Methods and limits

Old positional draft order minus final position rank mixes a selected draft pool with a much larger final pool. Low-end rank gaps can be enormous despite tiny point differences. Raw overall points also favor QBs. Neither is the primary ranking now.

Primary: actual season FPTS minus the mean FPTS from the same positional draft slot in other completed seasons (all historical managers supply expectations; only latest-season active managers appear in Summary). This is a retrospective descriptive baseline, not a preseason projection. It retains injury and zero-point losses in points rather than magnifying low-end rank differences. No injury diagnosis is inferred. Different scoring environments and sparse late slots limit comparability. This is points-based position-relative value; linear remaining-pick capital is shown only as an allocation proxy, not treated as an economic price or composite score.

The experimental gain maps final positional rank to original positional draft capital exactly. Fractional midranks have no Nth selection and are unavailable; integral tied ranks use the exact Nth pick. Finishes outside the drafted positional pool have no benchmark. Undrafted players participate in final ranks but have no actual draft pick to evaluate. Incomplete seasons withhold all final gains. Missing scoring remains missing; genuine zero seasons remain included. Exclusions skew gains toward surviving picks, so gain is used for individual-season examples, never manager averages. Positive/negative gains are not points or causal draft skill.

Capital share uses total draft picks + 1 − overall pick; early concentration means rounds 1–3. First-selection timing counts each manager-season once. First-pick FPTS describes results, not causal evidence that drafting early helps. Rookie status uses existing explicit rookie-season metadata only. No new data was retrieved.

Round tables retain chronological order and average tied performance ranks. Sleepers gain at least the season team count in pick capital (one draft round), with no fabricated missing benchmarks. Sample counts accompany rankings; raw round ranks remain league-size dependent.

Validation: offline Python suite has one unrelated pre-existing Players summary rounding mismatch (7.57 versus 7.58); Draft tests pass after removal of obsolete normalized-score assertions. Frontend tests and production build are run separately. No Basketball Brawl files changed.

## Delivery scope

Changed the offline analyzer, regenerated football draft-analysis snapshot, DraftPage, responsive draft CSS, and draft tests. Rookie/non-rookie comparisons use positional-slot points expectations; timing comparisons show first-half versus second-half first selections with complete evidence. These are descriptive group comparisons, not correlations with final team standings. Mobile CSS and scroll containment are implemented; a real-device/browser viewport audit was not available. No deployment was performed. Existing documentation of the previous version is historical, not the current methodology.
