# Paper architecture

## Candidate title

**Selective Cooperation in Multi-Agent Traffic Signal Control: Exact Coalition Valuation, Shapley Attribution, and Nucleolus Stability under Residual MAPPO**

Alternative:
**When Full Cooperation Is Not Optimal: Exact Cooperative-Game Analysis of Residual Multi-Agent Traffic Signal Control**

## Research gap

Recent MARL traffic-signal-control research has advanced cooperative control through communication, graph-based coordination, counterfactual credit assignment, heterogeneous-intersection modeling, and Shapley-informed rewards. A related recent line of work explicitly questions whether cooperation is always beneficial. However, these approaches generally optimize or analyze cooperation inside the learning architecture. They do not directly answer a complementary operational question: after a residual MARL controller has been trained, which subset of intersections should actually be permitted to cooperate/intervene, whether the grand coalition is stable, and how network benefit should be attributed when coalition effects are non-additive.

This study addresses that gap by treating controller participation itself as a transferable-utility cooperative game. The trained policy is held fixed, every coalition is evaluated by paired SUMO counterfactual replay, and the resulting complete characteristic function is analyzed using exact Shapley values, core feasibility, least-core optimization, and the nucleolus.

## Contributions

1. **Residual coalition formulation.** A coalition-constrained evaluation mechanism is introduced in which non-member intersections remain under native actuated control and only coalition members may invoke the validated residual MAPPO supervisor. This separates the value of participation from wholesale replacement of the underlying signal controller.

2. **Exact operational cooperative game.** For nine selected LuST traffic signals, all 2^9=512 coalitions are evaluated under paired full-history replay, producing an exact characteristic function rather than an additive or sampled coalition approximation.

3. **Contribution and stability analysis.** Exact Shapley values quantify average marginal contribution, while core feasibility, least-core radius, and the nucleolus expose whether full cooperation is self-enforcing and how worst-case coalition dissatisfaction can be reduced.

4. **Selective-cooperation finding.** The seed-9001 exact optimum is a five-signal coalition whose balanced value is approximately 5.99 times that of the grand coalition while using fewer residual interventions. A throughput-protected three-signal coalition provides a more conservative operating alternative.

5. **Sensitivity and held-out robustness.** The main stability pattern is tested across six utility scalarizations, and pre-specified critical coalitions are independently replayed on four held-out seeds. Selective coalitions outperform the grand coalition in all five focal realizations, while claims are explicitly bounded because complete enumeration is performed only for seed 9001.

## Draft abstract

Multi-agent reinforcement learning (MARL) enables coordinated traffic signal control, yet increasing the number of cooperating intersections does not necessarily improve network performance. This study formulates participation in a residual MARL traffic-signal controller as a cooperative game and asks which intersections should be allowed to intervene, how their contributions should be attributed, and whether full cooperation is stable. A validated residual MAPPO policy is evaluated on the LuST network using SUMO 0.27, while native actuated control is preserved as the default signal logic. Nine traffic signals are treated as players and all 512 coalitions are evaluated through paired deterministic full-history counterfactual replay during the AM peak. The characteristic value combines normalized improvements in queue, waiting time, CO2 emissions, and completed arrivals. The highest-value coalition contains five signals and achieves v=0.04551, approximately 5.99 times the grand-coalition value, while reducing mean halting vehicles and waiting time by 6.10% and 7.96%, respectively. Exact Shapley analysis reveals strongly heterogeneous marginal contributions. The core is empty, with a least-core radius of 0.02271; the uniquely determined nucleolus reduces maximum coalition dissatisfaction by approximately 30.9% relative to the Shapley allocation. The empty-core result persists across six utility-weight scenarios. A throughput-protected three-signal coalition is further identified and, across five stochastic realizations, it achieves positive utility in every seed and outperforms the grand coalition in all five paired comparisons. The results demonstrate that coalition composition is more important than coalition size and that selective residual cooperation can be both more effective and more robust than unrestricted full participation.

## Proposed manuscript structure

1. Introduction
   - Urban TSC and MARL motivation
   - Why coordination is not automatically beneficial
   - Gap: participation selection and post-training coalition stability
   - Contributions

2. Related Work
   - DRL/MARL traffic signal control
   - Cooperative and communication-aware MARL
   - Counterfactual credit assignment and Shapley-informed rewards
   - Safe/reference/residual control and deployment constraints
   - Cooperative-game allocation and stability concepts
   - Positioning of the present work

3. Methodology
   - LuST network and nine-player selection
   - Validated residual MAPPO controller
   - Coalition-constrained action masking
   - Deterministic counterfactual replay
   - Characteristic value
   - Exact Shapley computation
   - Core, least core, nucleolus
   - Utility and throughput sensitivity
   - Multi-seed robustness protocol

4. Experimental Setup
   - SUMO 0.27 and pinned LuST scenario
   - AM peak, 1800 s evaluation
   - Phase2b checkpoint and held-out seeds
   - Baseline and performance metrics
   - Reproducibility safeguards

5. Results
   - Exact 512-coalition landscape
   - Selective versus grand coalition
   - Shapley attribution
   - Core and nucleolus
   - Utility sensitivity
   - Throughput-protected operation
   - Multi-seed robustness

6. Discussion
   - Why coalition composition dominates size
   - Operational meaning of negative/positive marginal contributions
   - Empty core and incentives to deviate
   - Sparse intervention architecture
   - Deployment interpretation

7. Limitations
   - Exact game only for seed 9001 / AM peak
   - Targeted rather than exhaustive held-out coalition evaluation
   - Simulation-based evidence
   - Scalar utility preference dependence
   - No claim of uniform MAPPO superiority

8. Conclusion

## Literature positioning notes

- Use recent MARL-TSC literature to establish communication, heterogeneous-intersection coordination, and cooperative learning.
- Contrast Shapley-as-reward/credit-assignment approaches with the present post-training exact characteristic-function analysis.
- Cite recent evidence that independent or selective control can outperform indiscriminate cooperation as motivation, while emphasizing that the present work evaluates subset participation and cooperative-game stability rather than proposing another communication architecture.
- Use nucleolus literature from transportation/cost-allocation applications to motivate minimum-dissatisfaction allocation, without implying that those studies address traffic-signal control.
- Avoid an unsupported priority claim such as “the first study.” Prefer: “To our knowledge, the combination of fixed-policy coalition-constrained counterfactual replay with complete Shapley/core/nucleolus analysis has received limited attention in MARL traffic-signal control.”
