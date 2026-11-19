# V6 new checkpoint — empirical training coverage and saturation audit

**Source:** Actual downloaded GitHub Actions artifact `lust-v6-new-mappo-pilot` from successful run [44533285635](https://github.com/serapergun/Reinforcement-Learning-in-Traffic-Control-For-Connected-Automated-Vehicles/actions/runs/44533285635).

**Source checkpoint SHA-256:** `d48c14379a92612b8c8d2417be2e7f276bf7b09f514a1e017412900b23a0cc4c`. The SHA was independently recomputed from the archived `stakeholder_mappo.pt` and matches `provenance_v6.json`.

## Directly observed training facts

| Diagnostic | Real artifact result |
| --- | ---: |
| PPO training episodes | 14 |
| Distinct feasible stakeholder coalitions observed | **9 of 14** |
| Distinct condition × coalition combinations | **14 of 56** |
| Condition episodes — Off-peak / AM / Lunch / PM | 3 / 3 / 3 / 5 |
| Eligible intervention slots in training | 681 |
| Training interventions | 372 |
| Stochastic training intervention fraction | 54.6256% |
| Eligible-action counts (native / +3s / +6s) | 309 / 140 / 232 |
| Pilot smoke evaluation eligible slots | 54 |
| Pilot smoke interventions | **54 of 54 (100%)** |
| Pilot smoke action distribution (native / +3s / +6s) | **0 / 0 / 54** |
| Pilot smoke warning | `policy_saturation_warning=true` |

The held-out AM coalitions tested in V7—MO+VI, MO+VI+EC, TA+MO+VI+EC—were **not** explicitly trained as AM condition–coalition pairs in the short pilot (although these coalitions were observed under other conditions).

## Interpretation and publication boundaries

1. The original frozen checkpoint was not recovered. This is a newly trained 14-episode development pilot. It is not a converged or independently validated MAPPO controller.
2. The extreme deterministic smoke intervention behavior is a **saturation warning** and may lead to adverse outcomes; it cannot support claims of adaptive selectivity or resource savings.
3. V7 must report paired native comparisons, interventions per eligible slot, action selection, and no-op cases without selectively suppressing adverse results.
4. Training exposure covered only 25% of the predefined condition × coalition combinations. Evaluations of unobserved pairs probe generalization and may fail.
5. V7's two new seeds are descriptive only: inferential significance, robust dominance, Nucleolus/core stability and dynamic policy performance cannot be established.
6. Historical native and LuST source artifacts are stored in their original experimental run archives; this note does not alter historical inputs or reported results.

**Audit provenance:** Direct re-computation from downloaded `training_history.csv`, `smoke.json`, `provenance_v6.json`, and `stakeholder_mappo.pt` on 2026-11-19. No new SUMO runs were needed for these checks.
