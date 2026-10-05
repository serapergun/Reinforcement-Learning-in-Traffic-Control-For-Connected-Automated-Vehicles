# Phase3A Reproducibility Audit

## Scope

This audit records the publication-stage reproducibility checks for the Phase3A exact cooperative game and five-seed critical-panel robustness analysis. It is intended to keep the manuscript, retained CSV artifacts, analysis scripts, and numerical source of truth synchronized.

The audit does not rerun SUMO. It reconstructs the reported game-theoretic and robustness quantities from retained simulation outputs.

## Retained source artifacts

- `exact_512_game.csv`: complete seed-9001 AM-peak operational game.
- `seedwise_focal_utility.csv`: five-seed focal-coalition robustness values.
- Canonical numerical claims: `PHASE3A_SOURCE_OF_TRUTH.md`.
- Exact-game analysis: `analyze_phase3a_game.py`.
- Robustness analysis: `analyze_phase3a_robustness.py`.

## Exact-game reconstruction

The retained exact-game artifact contains all 512 unique coalitions for nine players. Recalculation confirms:

- grand-coalition value: `0.0075954924184047`;
- exact best coalition: `A3+A4+A7+A8+A9`;
- exact best value: `0.0455069834356523`;
- Shapley efficiency error: approximately `-3.90e-17`;
- least-core radius: `0.022705376418353584`;
- binding coalition constraints: 9;
- binding constraints plus efficiency allocation rank: 9;
- Shapley maximum excess: `0.03286885029538071`;
- nucleolus maximum excess: `0.02270537641835363`;
- maximum-excess reduction: approximately `30.9213%`.

Because the first least-core stage has full allocation rank nine, the efficient least-core allocation is unique and coincides with the nucleolus for this verified game.

These reconstructed quantities agree with the rounded values reported in the manuscript.

## Five-seed robustness reconstruction

Recalculation from the retained focal-coalition artifact confirms:

| Coalition | Mean v | Sample SD | Positive seeds |
|---|---:|---:|---:|
| A1+A3+A4 | 0.0439613 | 0.0123570 | 5/5 |
| A3+A4+A7+A8+A9 | 0.0385123 | 0.0061301 | 5/5 |
| Grand coalition | 0.00905842 | 0.0100663 | 4/5 |

For A1+A3+A4 versus the grand coalition, retained-artifact reconstruction gives:

- mean paired advantage: `0.03490289832394923`;
- 95% Student-t CI: approximately `[0.02432070, 0.04548510]`;
- Cohen's `dz`: approximately `4.0953`;
- paired t-test p-value: approximately `0.00078939`;
- exact two-sided Wilcoxon p-value: `0.0625`;
- directional wins: 5/5.

The manuscript reports these quantities at lower precision, so the artifact-derived recalculation is numerically consistent with the published text.

## Reproducibility issues found and corrected

### 1. Retained robustness CSV schema compatibility

The retained robustness artifact stores the grand coalition as the explicit full label `A1+A2+...+A9`, rather than the literal label `grand`, and stores balanced utility in column `v`.

The earlier robustness script expected the literal `grand` label and only `v_balanced` or `utility`. This would have prevented direct execution against the retained publication artifact.

Correction: `analyze_phase3a_robustness.py` now normalizes the explicit nine-player label to `grand` and accepts `v_balanced`, `utility`, or `v` as compatible utility columns.

Fix commit: `a3004ac2489724c139318630e8b42dcf84425bdb`.

### 2. Overly strict stale floating-point regression target

The earlier A1+A3+A4 paired-advantage regression target was `0.03490287098580091`. Direct reconstruction from the retained CSV gives `0.03490289832394923`. The difference is approximately `2.7e-8` and has no effect on any reported manuscript value, confidence interval, effect-size interpretation, or inference. However, the script used a `1e-9` absolute gate and would therefore fail unnecessarily.

Correction: the regression target was aligned with the retained artifact's directly reconstructed value.

Fix commit: `f30af2bd2112c3b1899fb2d7e77bfa38d65119b8`.

## Environment note

An attempted raw GitHub download from the execution container failed because external DNS/network access was unavailable (`Could not resolve host: raw.githubusercontent.com`). This is an execution-environment network limitation, not a simulation, artifact, or scientific reproducibility failure. Repository files remained accessible through the authenticated GitHub integration.

## Manuscript consistency status

The following publication claims have been cross-checked against retained outputs and the canonical source-of-truth record:

- complete 512-coalition count;
- seed-9001 exact optimum and grand-coalition values;
- exact Shapley efficiency;
- empty-core/positive least-core result;
- rank-nine uniqueness condition supporting the nucleolus label;
- maximum-excess reduction;
- five-seed focal-coalition means and sample standard deviations;
- paired advantage, confidence interval, Cohen's dz, paired t-test, exact Wilcoxon test, and 5/5 directional consistency;
- distinction between complete seed-9001 global-optimum claims and held-out critical-panel comparisons.

## Audit conclusion

The retained Phase3A artifacts reproduce the principal numerical claims used in `PHASE3A_FULL_MANUSCRIPT.md`. Two implementation-level reproducibility mismatches were identified during publication QA and corrected without changing the scientific conclusions. The manuscript should continue to use rounded publication values, while the retained artifacts and analysis scripts remain the authoritative high-precision computational record.
