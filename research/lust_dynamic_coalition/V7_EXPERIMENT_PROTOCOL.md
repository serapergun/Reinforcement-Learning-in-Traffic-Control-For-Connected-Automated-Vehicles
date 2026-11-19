# V7 Experimental Protocol — frozen before held-out results

## Purpose
This is an **engineering/pilot replication** of stakeholder-conditioned MAPPO behavior on LuST v2.0 with SUMO 0.27.0. It is not a recovery of the original frozen stakeholder checkpoint. A newly trained checkpoint must be labeled **V6 new pilot** in every figure, report, and table.

## Pinned components
- Branch: `lust-v6-reproducibility-20261119`; historical source base: `38f8ee1ca42ddae5fc42be4882200844bb504c90`
- LuST: `c4bd5bd3751d426d42a9a1749c815e47ea188549`
- SUMO: `7eac6a1b2543aa902fa2eff8ae82548eaa4cce6b` (0.27.0)
- Junctions: A1=-17662, A2=-13722, A3=-26466, A4=-28210, A5=-16312, A6=-17612, A7=-18372, A8=-1458, A9=-14740
- Evaluation: AM at 08:00; 900-second control window; evaluation starts from t=0 replay with full prior demand
- Held-out test seeds: **9301, 9302**. Neither seed may be used for V6 training or model selection.
- Deployment decision margin: 0.15 (different from new training checkpoint's recorded training deployment margin of 0.05)

## Planned paired comparisons
Per seed, run:
1. Native LuST actuated baseline
2. Frozen new MAPPO actor with MO+VI
3. Frozen new MAPPO actor with MO+VI+EC
4. Frozen new MAPPO actor with TA+MO+VI+EC

The same seed and period form one paired block. These 8 runs are **not** the original manuscript's 280 coalition evaluations. This pilot does not test online coalition switching or Shapley/Nucleolus.

## Primary/secondary outcomes
- Primary diagnostic: relative difference in the **lane-aggregate waiting-time summary** `mean_waiting_time_lane_sum_s`, not mean passenger travel delay.
- Secondary: `mean_halting_vehicles`, `CO2_kg_selected_approaches`, and `arrived_vehicles_global`.
- Process measures: `interventions`, `action_requests`, `mask_eligible_slots`, `decision_steps`.
- Important scope discrepancy: arrival count is network-global, whereas CO2 is summed only for selected incoming approaches. Do not combine as a single spatially homogeneous objective without an explicit definition.

For each seed and metric, calculate:
`100 * (MAPPO_metric - Native_metric) / Native_metric`.
Negative is favorable for waiting/halting/CO2; positive is favorable for arrivals. A zero native denominator yields undefined %, not artificial 0%.

## Gates
1. New checkpoint artifact from workflow #44533285635 must exist and its provenance must explicitly mark a **newly trained**, non-recovered checkpoint.
2. Independent native baseline workflow #44553818805 must pass for both seeds, with its source CSV retained.
3. V7 evaluation must output exactly four strategies per seed and no duplicate (seed, strategy) pairs.
4. All displayed metrics must be finite; the recorded relative changes must match recomputation from raw rows.
5. V7's native rows must match independent native measurements for identical seeds/condition within the predeclared relative tolerance (1e-6) and absolute tolerance (1e-7). Any mismatch blocks reporting pending root-cause analysis.
6. SHA256 model, simulator, and selection input hashes must be archived. Truncated, partial, or failed runs are reported as failures and never silently discarded.

## Inference boundaries and anticipated failure modes
- Two paired seeds yield descriptive trends only; do **not** report statistical significance or universal superiority.
- AM-only results do not generalize to off-peak, lunch, or PM.
- If no intervention is made, record the exact no-op as an informative negative result rather than selective evidence of policy effectiveness.
- A pilot trained for 14 short episodes cannot establish a converged PPO policy.
- The long SUMO replay to each morning/PM traffic window and repeated TraCI lane/vehicle queries can dominate wall time. A CI timeout is a computational execution failure, not evidence of policy quality.
- Do not compare recovered old checkpoint and new pilot numerically as if they shared weights/optimization trajectories.
- This pilot cannot support claims of 31.8% resource savings, 97.3% retained benefit, robust coalition stability, or a learned counterfactual dynamic selector.

## Next experiment (only after pilot gate)
A larger, seed-separated four-condition trial, explicit resource cost instrumentation, and truly closed-loop dynamic-vs-best-fixed comparison. Pre-register the complete seed list and reserve an independent test set before model calibration.
