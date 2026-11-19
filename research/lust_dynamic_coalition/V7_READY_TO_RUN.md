# V7 READY TO RUN — 2026-11-19

This marker triggers `.github/workflows/lust-v7-paired-evaluation.yml` only on the isolated V6/V7 research branch.

## Preflight evidence

- New (NOT original recovered) stakeholder MAPPO pilot workflow run **44533285635**: success.
- Checkpoint artifact: `lust-v6-new-mappo-pilot`, artifact ID 14545077734, `stakeholder_mappo.pt`.
- Checkpoint SHA256 from original training provenance:
  `d48c14379a92612b8c8d2417be2e7f276bf7b09f514a1e017412900b23a0cc4c`.
- Native independent AM baseline workflow run **44553818805**: success.
- Native baseline artifact: `lust-v7-native-am-seeds-9301-9302`, artifact ID 14545982149.
- Original pilot smoke warning: `policy_saturation_warning: true`, all 54 eligible slots received a +6s extension.
- Held-out seed pair: 9301 and 9302, AM condition, 900-second evaluation.
- Comparative coalitions: MO+VI, MO+VI+EC, TA+MO+VI+EC, plus native baseline.
- Cross-run native consistency and seed-wise paired statistics enforced by the V7 workflow.
- The test is **descriptive**; two seeds cannot establish significance or robust generalization.

## Native reference values (separate real-SUMO experiment)

| Seed | mean_waiting_time_lane_sum_s | mean_halting_vehicles | CO2_kg_selected_approaches | arrived_vehicles_global |
|---|---:|---:|---:|---:|
| 9301 | 620.9555555555555 | 36.355555555555554 | 59.341665705803834 | 5901 |
| 9302 | 594.7111111111111 | 34.78888888888889 | 56.48679147543281 | 5847 |

This file does not assert any MAPPO performance result. A successful output requires the actual full V7 workflow and all predefined source/provenance gates to pass.
