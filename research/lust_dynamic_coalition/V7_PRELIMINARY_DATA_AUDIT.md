# V7 preliminary evidence audit — actual GitHub artifacts, 2026-11-19

This is a **pre-result** audit, not a V7 MAPPO performance paper. Source files were taken from successful GitHub Actions runs 44533285635 and 44553818805 and independently inspected after downloading artifacts.

## V6 newly trained MAPPO pilot checkpoint

* GitHub Actions run **44533285635** completed `success`.
* Artifact ID: `14545077734`, `lust-v6-new-mappo-pilot`.
* Checkpoint path: `v6_retraining/stakeholder_mappo.pt`, **342,707 uncompressed bytes**.
* Recorded SHA-256: `d48c14379a92612b8c8d2417be2e7f276bf7b09f514a1e017412900b23a0cc4c`.
* Direct recomputation on extracted checkpoint bytes matched the recorded SHA-256.
* Exactly 14 training episodes, each 300 seconds of control time, were observed in `training_history.csv`.
* Condition coverage: AM=3, Lunch=3, PM=5, Off-peak=3.
* The 14 episodes covered **9 distinct coalition masks** out of 14 feasible masks; the full 14×4 condition-mask design was not trained.
* In training history, eligible action slots summed to **681** and applied interventions to **372** (fraction **0.5463**). These are in-sample training diagnostics, not causal effects.
* Short AM smoke evaluation at seed 9001, 300 seconds: 54 eligible slots, 54 +6s extensions, intervention fraction 1.0, `policy_saturation_warning=true`. Treat as a saturation warning; no comparison to independent native control is implied from this smoke record.
* Original historical MAPPO checkpoint is **not** recovered; all results from this newly trained checkpoint must be labeled separately.

## V7 independent native reference

* Run **44553818805** completed `success`.
* Artifact ID: `14545982149`, `lust-v7-native-am-seeds-9301-9302`.
* Scenario: pinned SUMO 0.27.0 and LuST v2.0, AM 08:00–08:15 control window, replay from simulation t=0, nine archived traffic lights.
* Native results directly inspected in `v7_native_baselines.csv`:

| Seed | mean_halting_vehicles | mean_waiting_time_lane_sum_s | CO2_kg_selected_approaches | arrived_vehicles_global |
|---|---:|---:|---:|---:|
| 9301 | 36.355555555555554 | 620.9555555555555 | 59.341665705803834 | 5901 |
| 9302 | 34.78888888888889 | 594.7111111111111 | 56.48679147543281 | 5847 |

These are observed **native** results only. The waiting metric is a lane-aggregate time indicator and should not be relabeled as individual vehicle waiting time. The arrival metric is global; CO2 is measured over selected approaches.

## V7 held-out paired experiment

* Workflow run **44557298980** began after both source artifacts passed.
* Conditions: AM only, 2 held-out seeds (9301, 9302), four strategies per seed, nominal total 8 real SUMO runs.
* Matched strategies: native, MO+VI, MO+VI+EC, TA+MO+VI+EC.
* At the time of this audit, the V7 job is still running and the paired results artifact is not yet available.
* Acceptance gates: source-run success, distinct (seed, coalition) rows, finite metrics, recalculated percentage differences, and exact native reproducibility within predefined tolerance versus the independent run.
* **No MAPPO improvement, statistical significance, or dynamic-coalition superiority claim is currently justified.** These new V7 runs are not the original manuscript’s 280 evaluations or V4 counterfactual dynamic coalition tests.

## Follow-up decision rule

Only after V7 closes and its artifact passes both audit gates, inspect intervention rate, interventions on eligible steps, changes in lane-level waiting and CO2, and global arrivals. Report unfavorable results and zero-intervention outcomes without selective omission. Two seeds support descriptive diagnostics only; a publication-quality study requires broader independent held-out coverage, richer training, and an explicit dynamic versus strongest static comparison.
