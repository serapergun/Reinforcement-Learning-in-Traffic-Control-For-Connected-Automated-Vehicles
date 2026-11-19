# LuST V6/V7: independently audited archived artifacts (2026-11-19)

## Evidence
- Newly trained V6 pilot workflow [44533285635](https://github.com/serapergun/Reinforcement-Learning-in-Traffic-Control-For-Connected-Automated-Vehicles/actions/runs/44533285635) concluded **success**. Artifact **14545077734** / `lust-v6-new-mappo-pilot` was downloaded and its CSV, smoke JSON and provenance parsed independently.
- Checkpoint `stakeholder_mappo.pt` SHA-256 independently recomputed as `d48c14379a92612b8c8d2417be2e7f276bf7b09f514a1e017412900b23a0cc4c` matching the recorded hash.
- The checkpoint is a **new 14-episode V6 pilot**, **not** a recovered copy of the 2026 original actor.
- Native held-out workflow [44553818805](https://github.com/serapergun/Reinforcement-Learning-in-Traffic-Control-For-Connected-Automated-Vehicles/actions/runs/44553818805) concluded **success**; artifact **14545982149** / `lust-v7-native-am-seeds-9301-9302` was downloaded and its raw CSV inspected.
- SUMO commit: `7eac6a1b2543aa902fa2eff8ae82548eaa4cce6b`. LuST scenario: `c4bd5bd3751d426d42a9a1749c815e47ea188549`.

## Training coverage from training_history.csv
- 14 total training episodes; 9 unique stakeholder coalitions out of 14 available.
- 14 unique condition–coalition pairs out of 56 possible.
- Condition counts: AM 3, PM 5, Lunch 3, Off-peak 3.
- 681 eligible action slots across recorded episodes; chosen action-0 309, +3-second extension 140, +6-second extension 232; interventions 372. These are training observations, **not** held-out efficacy measurements.
- The 300-s AM grand-coalition pilot smoke file reports 54 eligible slots and **54 accepted +6-second extensions**, yielding an eligible intervention fraction of **1.0** and `policy_saturation_warning=true`. This is a **control saturation diagnostic**; no superiority or reliability conclusion follows.

## Real independent native AM results
Protocol: control window 08:00–08:15 (900 s), same official scenario replayed from t=0 for each seed; native actuated controller, no MAPPO checkpoint.

| Metric | Seed 9301 | Seed 9302 |
|---|---:|---:|
| Mean halting vehicles, selected approaches | 36.3555555556 | 34.7888888889 |
| Mean lane-aggregate waiting summary (s) | 620.9555555556 | 594.7111111111 |
| CO2 (kg), selected approaches | 59.3416657058 | 56.4867914754 |
| Arrived vehicles, global network | 5901 | 5847 |

Do not interpret lane-aggregate waiting as per-vehicle mean waiting or assume that global arrivals and approach-only CO2 have identical spatial scope.

## Remaining publication gates
- MAPPO held-out paired evaluation [44557298980](https://github.com/serapergun/Reinforcement-Learning-in-Traffic-Control-For-Connected-Automated-Vehicles/actions/runs/44557298980) must finish successfully and publish all eight seed/strategy rows.
- Its in-run native results must reproduce the separately archived native data for the same period and seeds, subject to the pre-registered numerical tolerance.
- Intervention counts, CO2, arrivals, and waiting must be compared per seed; never claim statistical significance from only two seeds.
- Policy training convergence, four-period robustness, dynamic coalition selection and coalition resource savings remain **unverified**.
