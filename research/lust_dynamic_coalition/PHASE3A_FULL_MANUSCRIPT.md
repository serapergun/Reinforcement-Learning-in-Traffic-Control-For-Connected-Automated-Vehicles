# Selective Cooperation in Multi-Agent Traffic Signal Control: Exact Coalition Valuation, Shapley Attribution, and Nucleolus Stability under Residual MAPPO

## Abstract

Multi-agent reinforcement learning (MARL) enables coordinated traffic signal control, yet increasing the number of cooperating intersections does not necessarily improve network performance. This study formulates participation in a residual MARL traffic-signal controller as a cooperative game and asks which intersections should be allowed to intervene, how their contributions should be attributed, and whether full cooperation is stable. A validated residual MAPPO policy is evaluated on the Luxembourg SUMO Traffic (LuST) network while native actuated control is preserved as the default signal logic. Nine traffic signals are treated as players and all 512 coalitions are evaluated through paired deterministic full-history counterfactual replay during the AM peak. Coalition value combines normalized improvements in queue, waiting time, CO2 emissions, and completed arrivals. The highest-value coalition contains five signals and achieves v(S)=0.04551, approximately 5.99 times the grand-coalition value, while reducing mean halting vehicles and waiting time by 6.10% and 7.96%, respectively. Exact Shapley analysis reveals strongly heterogeneous marginal contributions. The core is empty, with a least-core radius of epsilon*=0.02271; the uniquely determined nucleolus reduces maximum coalition dissatisfaction by approximately 30.9% relative to the Shapley allocation. The empty-core result persists across six utility-weight scenarios. A throughput-protected three-signal coalition is further identified and, across five stochastic realizations, achieves positive utility in every seed and outperforms the grand coalition in all five paired comparisons. The results show that coalition composition is more important than coalition size and that selective residual cooperation can be more effective and robust than unrestricted full participation.

**Keywords:** multi-agent reinforcement learning; traffic signal control; cooperative game theory; Shapley value; nucleolus; residual reinforcement learning; SUMO; coalition formation

# 1. Introduction

Urban traffic signal control is a networked decision problem in which local timing decisions propagate through neighboring intersections and create downstream effects. MARL has consequently become an important framework for adaptive multi-intersection control, with recent research emphasizing decentralized communication, graph-based coordination, counterfactual credit assignment, and heterogeneous-intersection modeling. These developments improve coordination but also expose a fundamental difficulty: more cooperation is not necessarily better.

Most cooperative MARL traffic-signal-control methods address cooperation inside the learning architecture. Communication mechanisms determine which information is exchanged; centralized critics or counterfactual baselines improve credit assignment; graph models encode spatial dependencies; and Shapley-based rewards can encourage collaboration. Such methods principally address how agents should learn to cooperate. A complementary operational question is less explored: once a multi-agent controller has been trained, which intersections should actually be permitted to participate in learned intervention?

This distinction matters for deployment. Enabling every intersection to invoke a learned controller may increase intervention frequency and expose the network to unfavorable cross-intersection interactions. Conversely, a strategically selected subset may preserve native control elsewhere while retaining, or even increasing, network benefit. Residual reinforcement learning is particularly suitable for this question because the learned policy can operate as a supervisory correction while an established controller remains the default layer.

We formulate controller participation as a transferable-utility cooperative game. Nine selected traffic signals form the player set. For coalition S, only its members may invoke the validated residual MAPPO supervisor; non-members remain under native actuated control. The learned policy is held fixed, separating participation value from retraining. Each coalition is evaluated by paired deterministic SUMO counterfactual replay against the native-actuated baseline from the same realization. Because n=9, the complete characteristic function is obtained by enumerating all 2^9=512 coalitions.

This complete game supports questions that conventional MARL performance comparisons do not directly answer. Exact Shapley values quantify average marginal contribution over every coalition context. Core feasibility tests whether full cooperation can be supported by an efficient allocation. When the core is empty, the least core and nucleolus quantify unavoidable dissatisfaction and minimize the most dissatisfied coalitions.

The contributions are fivefold. First, we introduce a coalition-constrained residual-control formulation in which native actuated control remains active for non-members. Second, we evaluate the complete nine-player operational game rather than a sampled or additive coalition approximation. Third, exact Shapley attribution is combined with core, least-core, and nucleolus analysis to distinguish contribution from stability. Fourth, utility and throughput sensitivity explicitly test whether coalition choice is preference dependent. Fifth, a held-out multi-seed experiment evaluates whether the selective-versus-grand conclusion persists across independent traffic realizations.

# 2. Related Work

## 2.1 Cooperative MARL for traffic signal control

MARL addresses scalability limitations of monolithic network-wide controllers by associating agents with individual intersections or local regions. Recent work has emphasized communication and information sharing to mitigate partial observability, as well as graph-based and heterogeneous-intersection representations. These studies show that coordination quality depends on spatial and temporal structure rather than merely on the number of participating agents.

Recent research has also challenged the assumption that universal cooperation must dominate independent control. This motivates separating the question of how cooperation is learned from the question of where learned cooperation should be enabled. The present study focuses on the latter: the policy is fixed and participation is varied counterfactually.

## 2.2 Credit assignment and Shapley-based cooperation

Credit assignment is difficult in cooperative MARL because network-level performance emerges from interacting local decisions. Counterfactual methods estimate the contribution of an agent relative to alternative actions, while Shapley-informed methods provide contribution-aware rewards or congestion attribution. In multi-intersection traffic control, Shapley rewards have been used during training to encourage collaboration, and recent congestion-attribution work uses Shapley analysis to identify high-contribution intersections for selective joint training.

Our use differs in timing and purpose. Shapley values are computed after training from a complete operational characteristic function produced by coalition-constrained replay. They measure the marginal value of permitting an intersection to participate in residual control across all coalition contexts. Shapley attribution is then explicitly separated from coalition stability through core and nucleolus analysis.

## 2.3 Residual control and deployment constraints

Traffic signal control is operations-critical, making unconstrained replacement of established signal logic difficult to justify. Residual RL provides an intermediate architecture in which a learned component modifies a baseline controller rather than replacing it. The present framework adopts this deployment principle: native actuated control remains the default, and coalition membership determines whether the learned supervisor may request a limited green extension. Coalition value therefore measures incremental benefit over an operational baseline.

## 2.4 Cooperative-game stability in transportation

Cooperative game theory distinguishes contribution attribution from stability. The Shapley value averages marginal contributions over coalition orders, while the core asks whether any coalition can improve on its assigned share. When the core is empty, least-core and nucleolus concepts quantify unavoidable dissatisfaction and progressively minimize the largest coalition excesses. Transportation applications have used these concepts primarily for cost allocation in ridesharing and collaborative logistics. Here, traffic signals are the players and the characteristic function is generated from simulated network-control performance rather than monetary cost.

To our knowledge, fixed-policy coalition-constrained counterfactual replay combined with complete Shapley, core, and nucleolus analysis has received limited attention in MARL traffic signal control. This study therefore connects cooperative learning, operational participation selection, and cooperative-game stability at the post-training stage.

# 3. Methodology

## 3.1 Coalition-constrained residual MARL

Let N={A1,...,A9} denote the nine selected traffic signals. The learned controller is a residual MAPPO supervisor operating above the native actuated signal logic. At each eligible decision point, action 0 preserves native operation, action 1 requests a +3 s extension of the remaining green interval, and action 2 requests a +6 s extension. Native yellow, all-red, and subsequent-green transitions remain governed by the underlying signal program.

For coalition S subseteq N, only members of S may request residual interventions. Every non-member's action mask is restricted to action 0, while coalition members retain the environment-defined feasibility mask. Thus v(S) measures network performance when exactly the members of S may apply the trained residual policy. The empty coalition is the native-actuated baseline, and the grand coalition permits residual intervention at all nine selected signals.

## 3.2 Counterfactual replay and characteristic value

Coalitions are compared using full-history replay from simulation time t=0 under the same condition and random seed. For each seed, outcomes are normalized against that seed's own empty-coalition baseline.

Let q_S, w_S, c_S, and a_S denote mean halting vehicles, mean lane-summed waiting time, CO2 emissions on selected approaches, and completed arrivals for coalition S. With paired baseline q_0,w_0,c_0,a_0,

d_q(S)=(q_0-q_S)/q_0,

d_w(S)=(w_0-w_S)/w_0,

d_c(S)=(c_0-c_S)/c_0,

d_a(S)=(a_S-a_0)/a_0.

Positive d_q, d_w, and d_c indicate desirable reductions; positive d_a indicates increased throughput. The balanced characteristic value is

v(S)=0.35 d_q(S)+0.30 d_w(S)+0.20 d_c(S)+0.15 d_a(S).  (1)

The signed arrival component prevents an apparent congestion improvement obtained simply by suppressing completed traffic. Alternative scalarizations and explicit throughput constraints are evaluated separately.

## 3.3 Exact Shapley value

For n=9, the exact Shapley value of player i is

phi_i = sum_{S subseteq N\{i}} [ |S|!(n-|S|-1)! / n! ] [v(S union {i})-v(S)].  (2)

Because all 512 coalitions are evaluated, no coalition sampling is required. Efficiency is verified numerically through sum_i phi_i=v(N).

## 3.4 Core, least core, and nucleolus

For an efficient allocation x satisfying sum_i x_i=v(N), coalition excess is

e(S,x)=v(S)-sum_{i in S}x_i.  (3)

The core requires e(S,x)<=0 for all coalitions. If the core is empty, the least-core problem minimizes the largest excess,

minimize epsilon,  (4)

subject to

v(S)-sum_{i in S}x_i <= epsilon, for all proper non-empty S,  (5)

sum_i x_i=v(N).  (6)

For the balanced exact game, nine coalition constraints are binding at the least-core optimum; together with efficiency, their incidence system has rank nine. The least-core solution is therefore unique and coincides with the nucleolus.

## 3.5 Sensitivity and robustness

Six utility-weight scenarios are examined: balanced, queue-priority, waiting-priority, CO2-priority, throughput-priority, and equal weighting. A separate throughput-protection analysis restricts coalitions according to minimum d_a(S), including the strict condition d_a(S)>=0.

For stochastic robustness, a pre-specified critical panel is evaluated on held-out seeds 9002-9005. Five-seed summaries combine these with the exact seed-9001 realization. Paired selective-versus-grand differences are summarized by mean difference, 95% t confidence interval, Cohen's dz, paired t-test, and exact two-sided Wilcoxon signed-rank test. Given n=5, interpretation emphasizes effect size, interval estimates, and directional consistency.

# 4. Experimental Setup

The experiments use the Luxembourg SUMO Traffic (LuST) scenario with the legacy SUMO 0.27 execution stack retained by the validated pipeline. Scenario and simulator revisions are pinned for reproducibility. Nine selected signalized intersections form the player set, while background demand, routing, and native transition sequences remain unchanged.

The exact game uses the AM-peak condition, a 1800 s evaluation horizon, and seed 9001. AM peak was selected because preliminary screening showed meaningful residual intervention activity; Off-peak screening produced no informative interventions. All 512 coalitions are replayed from t=0. Saved-state initialization is not used because the legacy scenario exposed an incompatible bus car-following-model reload path.

The validated Phase2b residual MAPPO checkpoint is used without retraining. The automated evaluation retrieves validated upstream artifacts, verifies evaluator compilation and TraCI compatibility, checks coalition integrity, and stores raw and normalized coalition results. Four held-out seeds (9002-9005) use the same AM-peak horizon and controller checkpoint but evaluate only a critical coalition panel rather than all 512 coalitions.

# 5. Results

## 5.1 Exact coalition landscape

The complete seed-9001 game is strongly non-monotonic with coalition size. Mean coalition value is negative for every intermediate size from one through eight, while the grand coalition achieves only v(N)=0.0075955. The global maximum is A3+A4+A7+A8+A9 with v(S)=0.045507, approximately 5.99 times the grand-coalition value.

Relative to native actuated control, this five-player coalition reduces mean halting vehicles by 6.10%, waiting time by 7.96%, and CO2 by 0.50%, while completed arrivals decrease by 0.47%. It requires 26 residual interventions, compared with 54 for the grand coalition. The grand coalition yields only 1.64% queue reduction, 0.62% waiting-time reduction, and 0.37% CO2 reduction, with arrivals decreasing by 0.51%. Selective participation therefore produces substantially greater congestion benefit with fewer interventions.

**Table R1.** Performance of the native-actuated baseline, exact-best coalition, throughput-protected coalition, and grand coalition. Queue, waiting, and CO2 entries are reported as improvements relative to baseline; arrival change retains its natural sign.

[Insert Table R1 here]

**Figure R1.** Balanced characteristic value versus coalition size for all 512 coalitions. The exact maximum and grand coalition are highlighted.

[Insert Figure R1 here]

## 5.2 Exact contribution attribution

Exact Shapley values reveal substantial heterogeneity. A1 (0.02617) and A3 (0.02055) have the largest positive average marginal contributions, whereas A2 (-0.03185) and A5 (-0.01103) have the strongest negative contributions. These rankings cannot be inferred reliably from singleton behavior because pair and triple screening shows strong compensatory and antagonistic interactions.

**Table R2.** Singleton values, exact Shapley values, nucleolus allocations, and individual-rationality indicators for all nine players.

[Insert Table R2 here]

## 5.3 Core stability and nucleolus

The exact balanced game has an empty core. The least-core radius is epsilon*=0.0227054, so no efficient allocation can eliminate all coalition incentives to deviate. The rank-nine binding system uniquely determines the nucleolus.

The maximum coalition excess under the Shapley allocation is 0.0328689. Under the nucleolus it falls to 0.0227054, a reduction of approximately 30.9%. The nucleolus therefore reduces worst-case dissatisfaction but does not make the game core-stable.

**Figure R2.** Exact Shapley and nucleolus allocations for A1-A9.

[Insert Figure R2 here]

## 5.4 Utility and throughput sensitivity

The empty-core result persists under all six scalarizations. A1 remains the highest-Shapley player and A2 the lowest in every scenario, and the grand coalition is never the highest-value coalition. The preferred coalition alternates only between A3+A4+A7+A8+A9 and A1+A2+A3+A4+A7.

**Table R3.** Utility-weight sensitivity of coalition selection, grand-coalition value, Shapley ranking, core feasibility, and least-core radius.

[Insert Table R3 here]

Under the strict non-negative-arrival condition, only seven non-empty coalitions remain feasible. A1+A3+A4 is the best feasible coalition, with v(S)=0.037443. It reduces queue by 4.86% and waiting time by 7.12%, increases completed arrivals by approximately 0.075%, and worsens CO2 by approximately 0.51%. This explicitly exposes the throughput-emissions trade-off rather than hiding it inside the scalar utility.

## 5.5 Multi-seed robustness

Across five realizations, A1+A3+A4 achieves mean balanced utility 0.04396 ± 0.01236, mean queue improvement 5.52% ± 1.61%, mean waiting-time improvement 8.66% ± 2.15%, and mean arrival change +0.26% ± 0.35%. Its mean CO2 gain is negative, corresponding to an average CO2 worsening of approximately 0.87%; this trade-off is retained in the interpretation.

A1+A3+A4 exceeds the grand coalition in all five seeds. The paired utility advantage is +0.03490 (95% CI +0.02432 to +0.04549), Cohen's dz=4.10, paired t-test p=0.00079, and exact two-sided Wilcoxon p=0.0625. With only five pairs, the result is interpreted primarily through effect magnitude, confidence interval, and 5/5 directional consistency.

The seed-9001 exact optimum A3+A4+A7+A8+A9 also exceeds the grand coalition in all five realizations, with mean paired advantage +0.02945 (95% CI +0.01285 to +0.04606; dz=2.20). A1+A3+A4 is the highest-utility coalition among the tested critical panel in three of the four held-out seeds; A3+A4+A8+A9 is highest in seed 9004. This is a panel-win result, not a global-optimum claim.

**Table R4.** Five-seed robustness of focal selective coalitions and the grand coalition.

[Insert Table R4 here]

**Figure R3.** Seed-wise balanced utility for A1+A3+A4, A3+A4+A7+A8+A9, and the grand coalition.

[Insert Figure R3 here]

# 6. Discussion

The exact coalition landscape shows that coalition composition, rather than coalition size, is the central determinant of cooperative control performance. Strong non-additivity explains why an agent can be unfavorable in isolation but beneficial in a particular coalition, or why individually favorable agents can interact antagonistically. Singleton ranking is therefore insufficient for participation selection.

The results also distinguish attribution from stability. Shapley values identify average marginal contribution, but a Shapley allocation does not guarantee that no subgroup has an incentive to deviate. The empty core confirms that full cooperation is not self-enforcing under the evaluated performance utility. The nucleolus reduces the largest dissatisfaction by approximately 30.9%, but positive epsilon* correctly signals that some instability remains unavoidable.

Operationally, the findings support a sparse supervisory architecture. Native actuated control remains the default, while residual learned intervention is enabled only at a selected subset of signals. The seed-9001 exact optimum uses fewer than half as many interventions as the grand coalition while producing much larger queue and delay improvements. However, coalition choice remains objective dependent: the globally highest balanced value accepts a small throughput reduction, whereas the throughput-protected coalition preserves arrivals at the expense of slightly higher CO2.

The held-out results indicate that selective cooperation is not merely a seed-9001 artifact. Both focal selective coalitions outperform the grand coalition in every tested realization. At the same time, the difference between the two selective candidates is not statistically decisive across five seeds, reinforcing the interpretation that coalition selection should adapt to operating priorities rather than rely on a universal fixed subset.

# 7. Limitations

Complete 512-coalition enumeration is performed only for the AM-peak seed-9001 realization. Held-out seeds evaluate a targeted panel, so exact Shapley, core, nucleolus, and global-optimum claims are restricted to seed 9001. Lunch and PM conditions are not part of the present exact-game analysis; extending the critical-panel protocol to these periods would strengthen temporal generalization.

The evidence is simulation-based. Although LuST is a city-scale scenario and the residual architecture preserves native signal logic, field deployment may introduce sensor noise, communication delay, incidents, hardware constraints, and behavioral adaptation.

The balanced utility is preference dependent. Six alternative scalarizations and throughput constraints test sensitivity, but real deployment would require stakeholder-specific calibration. Furthermore, Shapley and nucleolus values are normalized performance-credit allocations, not monetary payments.

Finally, this study does not claim uniform superiority of residual MAPPO over native actuated control. The contribution is instead to demonstrate that selectively authorizing learned interventions can be preferable to unrestricted participation.

# 8. Conclusion

This study reframes cooperative MARL traffic signal control as a participation-selection and stability problem. A trained residual MAPPO policy is held fixed while intervention permission is varied across nine traffic signals, yielding an exact 512-coalition operational game.

The highest-value seed-9001 coalition contains five signals and achieves v(S)=0.04551, approximately 5.99 times the grand-coalition value, with 6.10% lower queue and 7.96% lower waiting time and fewer residual interventions. Exact Shapley analysis reveals heterogeneous contributions; the core is empty; and the unique nucleolus reduces maximum coalition dissatisfaction by approximately 30.9% relative to Shapley. These findings remain qualitatively robust across six utility scalarizations.

A throughput-protected three-signal coalition provides a conservative alternative and, across five stochastic realizations, both focal selective coalitions outperform the grand coalition in every paired comparison. The results therefore support selective residual authorization rather than universal learned intervention. Future work should extend coalition analysis across traffic periods and demand regimes, investigate online coalition adaptation, incorporate sensing and communication uncertainty, and connect performance-credit allocations to explicit incentive and governance mechanisms.

## References to be finalized

The final bibliography should include, at minimum: the LuST scenario/traffic-demand validation papers; foundational MAPPO and counterfactual multi-agent credit-assignment work; recent cooperative/communication-aware MARL traffic-signal-control studies; Shapley-reward and Shapley-congestion-attribution TSC studies; residual/safe RL traffic-control studies; and transportation nucleolus/core allocation studies. Every in-text citation should be mapped to a verified DOI/publisher record before submission.
