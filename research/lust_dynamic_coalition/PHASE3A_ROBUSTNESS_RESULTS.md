# Phase3A critical-coalition multi-seed robustness

Validated workflow run: 37313195601 (commit 2ee9dcf54290e51686b671cae65c8369ecd0c9e1).

## Scope
AM peak, 1800 s evaluation, held-out seeds 9002-9005. The panel tests empty baseline, seed-9001 exact-game optimum candidate A3+A4+A7+A8+A9, zero-throughput-loss candidate A1+A3+A4, queue/CO2-priority candidate A1+A2+A3+A4+A7, two stability-critical coalitions, and the grand coalition. Seed 9001 values come from the exact 512-coalition game.

## Five-seed focal summary
| Coalition | Utility mean±SD | Queue improvement | Waiting improvement | Arrival change |
|---|---:|---:|---:|---:|
| A1+A3+A4 | 0.04396±0.01236 | 5.52%±1.61 | 8.66%±2.15 | +0.26%±0.35 |
| A3+A4+A7+A8+A9 | 0.03851±0.0061 | 5.38%±0.76 | 6.67%±1.44 | +0.05%±0.61 |
| Grand | 0.00906±0.01007 | 1.55%±1.57 | 0.92%±1.89 | +0.19%±0.53 |

A1+A3+A4 beats the grand coalition in all five seeds. Paired utility difference = +0.03490, 95% CI [+0.02432,+0.04549], Cohen dz=4.10, paired t-test p=0.00079. Exact two-sided Wilcoxon p=0.0625; with n=5, inference should emphasize effect size, confidence interval, and directional consistency rather than dichotomous significance.

A3+A4+A7+A8+A9 also beats the grand coalition in all five seeds; paired utility difference = +0.02945, 95% CI [+0.01285,+0.04606], Cohen dz=2.20.

## Held-out panel ranking
A1+A3+A4 is the highest-utility tested coalition in seeds 9002, 9003, and 9005. A3+A4+A8+A9 is highest in seed 9004 (v=0.05118). Therefore A1+A3+A4 has a 3/4 held-out panel-win rate. This must not be described as a global-optimum rate because the held-out seeds evaluate only the critical panel, not all 512 coalitions.

## Interpretation
Selective cooperation is robustly preferable to unrestricted full participation in this experiment. The grand coalition is not the seed-9001 exact optimum and is less stable across held-out realizations; its balanced utility becomes negative in seed 9004. A1+A3+A4 is the strongest robust operating candidate in the tested panel because it combines high queue/waiting reductions with favorable mean throughput behavior.

## Reporting guardrails
Do not claim that MAPPO is uniformly superior. Do not call A1+A3+A4 the global optimum across seeds. Exact Shapley, core, least-core and nucleolus results refer to the complete seed-9001 512-coalition game. The 9002-9005 runs are a targeted robustness panel and cannot produce exact cooperative-game allocations for those seeds.

## Exact-game allocation validation
For the complete seed-9001 512-coalition game, v(N)=0.007595492418404752 and the exact Shapley values sum to the grand-coalition value within approximately 3.3e-17. The core is infeasible. The least-core radius is epsilon*=0.022705376418353573. At this optimum, nine coalition constraints are binding; together with the efficiency equation their incidence system has rank 9 for the nine-player game. Hence the first least-core stage uniquely determines the allocation, so the reported least-core vector is also the nucleolus for this game.

The nucleolus reduces maximum coalition dissatisfaction from 0.0328688503 under the Shapley allocation to 0.0227053764, a reduction of about 30.9%. This does not make the grand coalition stable in the core sense: epsilon*>0 remains direct evidence of an empty core under the balanced scalar utility.
