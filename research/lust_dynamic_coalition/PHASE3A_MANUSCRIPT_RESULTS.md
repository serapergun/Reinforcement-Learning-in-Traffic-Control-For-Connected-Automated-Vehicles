# Phase3A manuscript-ready Results and Discussion

## Exact coalition-game results

The complete nine-player game was evaluated by deterministic full-history replay for all 512 coalitions under the AM-peak condition. The balanced characteristic value was non-monotonic with coalition size: mean coalition value remained negative for every intermediate coalition size from one to eight players, whereas the grand coalition achieved only v(N)=0.0075955. The highest value in the exact game was obtained by A3+A4+A7+A8+A9 (v=0.045507), approximately 5.99 times the value of the grand coalition. Relative to native actuated control, this five-player coalition reduced mean halting vehicles by 6.10% and waiting time by 7.96%, while CO2 decreased by 0.50%. Arrivals decreased by 0.47%, which motivates the explicit throughput-constrained sensitivity analysis reported below. The grand coalition produced substantially smaller queue and waiting-time improvements (1.64% and 0.62%, respectively) despite requiring 54 residual interventions compared with 26 for the best five-player coalition. These results show that increasing coalition membership does not monotonically improve network performance and that selective cooperation can outperform unrestricted participation.

The exact Shapley allocation further confirms strong heterogeneity in marginal contribution. A1 (0.02617) and A3 (0.02055) provide the largest positive average marginal contributions, whereas A2 (-0.03185) and A5 (-0.01103) have the largest negative contributions. This pattern cannot be inferred from singleton performance alone. In particular, earlier singleton/pair/triple screening revealed substantial compensatory and antagonistic interactions, motivating exact enumeration rather than an additive approximation.

## Core stability and nucleolus

The exact game has an empty core. The least-core radius is epsilon*=0.0227054, indicating that no efficient allocation can simultaneously eliminate all coalition incentives to deviate under the balanced utility. Nine coalition constraints are binding at the least-core optimum; together with the efficiency equation, the corresponding system has rank nine. Consequently, the first least-core stage uniquely determines the allocation and the resulting vector is the nucleolus of this nine-player game.

Compared with the Shapley allocation, the nucleolus reduces the maximum coalition excess from 0.0328689 to 0.0227054, a reduction of approximately 30.9%. This distinction is important: the nucleolus improves the worst coalition dissatisfaction but does not transform the game into a core-stable one. Thus, full cooperation is not self-enforcing under the evaluated scalar utility, even when the allocation is chosen to lexicographically minimize coalition dissatisfaction.

## Utility and throughput sensitivity

The empty-core result is not an artifact of a single weighting choice. Across balanced, queue-priority, waiting-priority, CO2-priority, throughput-priority, and equal-weight scalarizations, the core remained empty and the grand coalition was never the highest-value coalition. A1 retained the highest Shapley value and A2 the lowest in all six scenarios. The preferred coalition alternated only between A3+A4+A7+A8+A9 and A1+A2+A3+A4+A7, demonstrating that the broad selective-cooperation conclusion is robust even though the precise optimum depends on operational priorities.

A separate throughput-protection analysis provides a more conservative operating choice. When non-negative arrival gain is imposed, only seven non-empty coalitions remain feasible and A1+A3+A4 becomes the best feasible coalition. In the seed-9001 exact game, it improves queue and waiting performance by approximately 4.86% and 7.12%, respectively, while arrivals increase by approximately 0.075%. Its CO2 outcome is approximately 0.51% worse than the baseline, illustrating the trade-off between throughput protection and emissions rather than concealing it.

## Multi-seed robustness

The critical coalitions were subsequently evaluated on four independent held-out seeds (9002-9005), and combined with the seed-9001 exact-game realization for five-seed robustness assessment. A1+A3+A4 achieved a mean balanced utility of 0.04396+-0.01236, with mean queue and waiting-time improvements of 5.52%+-1.61% and 8.66%+-2.15%, respectively. Mean arrival change was +0.26%+-0.35%. The coalition produced positive utility in all five seeds and exceeded the grand coalition in every realization. The paired utility advantage over the grand coalition was +0.03490 (95% CI: +0.02432 to +0.04549), with Cohen's dz=4.10. A paired t-test yielded p=0.00079. Because only five paired realizations are available, inferential interpretation is deliberately conservative: the exact two-sided Wilcoxon test yields p=0.0625, and the evidence is therefore emphasized through effect magnitude, confidence interval, and 5/5 directional consistency rather than a binary significance claim.

The seed-9001 exact optimum candidate A3+A4+A7+A8+A9 was also superior to the grand coalition in all five realizations, with a mean paired utility advantage of +0.02945 (95% CI: +0.01285 to +0.04606; Cohen's dz=2.20). A1+A3+A4 was the highest-utility coalition among the tested critical panel in three of the four held-out seeds, while A3+A4+A8+A9 ranked first in seed 9004 (v=0.05118). This 3/4 result is a panel-win rate rather than a global-optimum rate because the held-out seeds did not re-evaluate the complete 512-coalition game.

## Discussion

Taken together, the results identify coalition composition, rather than coalition size, as the central determinant of cooperative control performance. The exact game contains strong non-additive interactions: agents that are unfavorable in isolation may become useful in combination, whereas individually beneficial agents may interact antagonistically. This explains why the grand coalition is neither optimal nor core-stable and why marginal-contribution allocation alone cannot resolve coalition dissatisfaction.

The practical implication is a sparse supervisory architecture in which native actuated control remains the default and residual MARL interventions are activated only for selected traffic-signal coalitions. The strongest selective coalitions deliver larger queue and delay reductions with fewer interventions than unrestricted nine-signal cooperation. At the same time, the throughput and CO2 sensitivity analyses show that coalition selection should be conditioned on the operating objective rather than represented as a universally optimal fixed subset.

The robustness experiment supports generalization of the selective-cooperation conclusion across independent stochastic traffic realizations, but it does not establish a global optimum for every held-out seed. Exact Shapley values, core feasibility, and the nucleolus are therefore reported only for the complete seed-9001 game. Extending exact 512-coalition enumeration to additional traffic periods or seeds would provide a stronger basis for distributional cooperative-game allocations, but the present evidence already demonstrates that full participation is neither necessary nor consistently preferable in the evaluated LuST AM-peak setting.

## Recommended result presentation

Table R1: exact 512-coalition game summary (baseline, best coalition, throughput-protected coalition, grand coalition).

Table R2: exact Shapley and nucleolus allocations by player, including singleton value and individual-rationality indicators.

Table R3: utility-weight sensitivity and least-core epsilon across six scalarizations.

Table R4: five-seed robustness summary with mean+-SD and selective-versus-grand paired statistics.

Figure R1: coalition value versus coalition size for all 512 coalitions, highlighting the grand coalition and global maximum.

Figure R2: Shapley versus nucleolus allocation by traffic signal.

Figure R3: seed-wise balanced utility for A1+A3+A4, A3+A4+A7+A8+A9, and the grand coalition.
