# V6 and V7 — Verified Empirical Evidence Register

**Audit date:** 2026-11-19. This register is scoped to the *new* V6 pilot checkpoint, not the missing checkpoint used by the older stakeholder manuscript.

## Direct artifact provenance

| Record | GitHub Actions run | Artifact |
|---|---:|---|
| New MAPPO pilot training | 44533285635 | `lust-v6-new-mappo-pilot` |
| Independent AM native baselines | 44553818805 | `lust-v7-native-am-seeds-9301-9302` |
| Independent training-coverage audit | 44561380253 | `lust-v6-training-evidence-audit` |

- New checkpoint: `v6_retraining/stakeholder_mappo.pt`
- SHA256: `d48c14379a92612b8c8d2417be2e7f276bf7b09f514a1e017412900b23a0cc4c`
- Pinned SUMO commit: `7eac6a1b2543aa902fa2eff8ae82548eaa4cce6b`
- Pinned LuST commit: `c4bd5bd3751d426d42a9a1749c815e47ea188549`

## Pilot training scope

The archived `training_history.csv` contains 14 episodes, each with a distinct condition–coalition pair, and 9 unique coalition masks. The full feasible grid consists of 14 coalitions × 4 conditions = 56 combinations. **Training coverage is 14/56 = 25%.**

| Condition | Episodes |
|---|---:|
| Off-peak | 3 |
| AM | 3 |
| Lunch | 3 |
| PM | 5 |

A short pilot with incomplete combination coverage cannot be described as converged or as validated across all coalition–condition pairs.

## Saturated grand-coalition smoke behavior

The one archived AM smoke test (seed 9001, 300 s) reports:
- `mask_eligible_slots = 54`
- `interventions = 54`
- `eligible_action2 = 54` (+6-second green extension)
- `eligible_action0 = 0` and `eligible_action1 = 0`
- `policy_saturation_warning = true`

This is an intervention-saturation diagnostic for **one** short evaluation, not evidence of improved or degraded control. Independent held-out tests must check whether this persists.

## Independently measured native baseline for V7 (real SUMO)

AM, 08:00, 900-second evaluation per seed:

| Seed | mean_halting_vehicles | mean_waiting_time_lane_sum_s | CO2_kg_selected_approaches | arrived_vehicles_global |
|---:|---:|---:|---:|---:|
| 9301 | 36.35555556 | 620.95555556 | 59.34166571 | 5901 |
| 9302 | 34.78888889 | 594.71111111 | 56.48679148 | 5847 |

These are **native-actuated** measurements and not MAPPO outcomes. CO2 covers the selected incoming approaches; arrived vehicles are counted over the wider network.

## Interpretation boundaries

1. No claim that the 14-episode checkpoint matches the original historical checkpoint.
2. V7 held-out AM comparison is descriptive with only 2 seeds; no significance tests.
3. Native rows from the V7 comparison must independently reproduce the baseline table above before performance claims are made.
4. If held-out MAPPO produces no interventions or saturated interventions, report those findings without selective omission.
5. No claims of dynamic-coalition superiority, source cost savings, or game-theoretic core stability arise from these measurements.
6. Any additional results from workflow `44557298980` require final success status, full artifact retrieval, and cross-check against both native baseline runs.

This register was authored from the archived GitHub artifacts and their independent audit, not from illustrative manuscript numbers.
