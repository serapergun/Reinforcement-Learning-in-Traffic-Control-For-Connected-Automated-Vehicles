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

MARL addresses scalability limitations of monolithic network-wide controllers by associating agents with individual intersections or local regions. Recent work has emphasized communication and information sharing to mitigate partial observability, as well as graph-based and heterogeneous-intersection representations [6-8,12,14,15]. These studies show that coordination quality depends on spatial and temporal structure rather than merely on the number of participating agents.

Recent research has also challenged the assumption that universal cooperation must dominate independent control [13]. A 2026 mixed-motive traffic-control study further uses selective cooperation and role-dependent information sharing for joint parking-exit and signal control [27]. These developments motivate separating how cooperation is learned from the post-training question of which signal controllers should be authorized to intervene. The present study focuses on the latter: the policy is fixed and participation is varied counterfactually.

## 2.2 Credit assignment and Shapley-based cooperation

Credit assignment is difficult in cooperative MARL because network-level performance emerges from interacting local decisions. Counterfactual methods estimate the contribution of an agent relative to alternative actions [4], while traffic-specific counterfactual actor-critic methods use this principle to improve multi-intersection collaboration [11]. Shapley-informed methods provide contribution-aware rewards or congestion attribution: Shapley rewards have been used during cooperative traffic-signal learning [18], and recent congestion-attribution work uses Shapley analysis to identify high-contribution intersections for Top-k joint training and decision ordering [19].

Our use differs in timing and purpose. Shapley values are computed after training from a complete operational characteristic function produced by coalition-constrained replay. They measure the marginal value of permitting an intersection to participate in residual control across all coalition contexts. Shapley attribution is then explicitly separated from coalition stability through core and nucleolus analysis.

## 2.3 Residual control and deployment constraints

Traffic signal control is operations-critical, making unconstrained replacement of established signal logic difficult to justify. Safety-enhanced residual formulations such as SafeLight illustrate the broader principle of combining learned signal control with explicit operational constraints [20]. Residual RL provides an intermediate architecture in which a learned component modifies a baseline controller rather than replacing it. The present framework adopts this deployment principle: native actuated control remains the default, and coalition membership determines whether the learned supervisor may request a limited green extension. Coalition value therefore measures incremental benefit over an operational baseline.

## 2.4 Cooperative-game stability in transportation

Cooperative game theory distinguishes contribution attribution from stability. The Shapley value averages marginal contributions over coalition orders [21], while core concepts formalize coalition blocking/stability [22]. When the core is empty, least-core and nucleolus concepts quantify unavoidable dissatisfaction and progressively minimize the largest coalition excesses [23,24]. Transportation applications have used these concepts for fair or stable allocation in ridesharing and collaborative truckload transportation [25,26]. Here, traffic signals are the players and the characteristic function is generated from simulated network-control performance rather than monetary cost.

To our knowledge, fixed-policy coalition-constrained counterfactual replay combined with complete Shapley, core, and nucleolus analysis has received limited attention in MARL traffic signal control. This study therefore connects cooperative learning, operational participation selection, and cooperative-game stability at the post-training stage.

# 3. Methodology

## 3.1 Coalition-constrained residual MARL

Let \(N=\{A_1,\ldots,A_9\}\) denote the nine selected traffic signals, with \(n=|N|=9\). The learned controller is a residual MAPPO supervisor operating above the native actuated signal logic. At each eligible decision point, action 0 preserves native operation, action 1 requests a +3 s extension of the remaining green interval, and action 2 requests a +6 s extension. Native yellow, all-red, and subsequent-green transitions remain governed by the underlying signal program.

For coalition \(S\subseteq N\), only members of \(S\) may request residual interventions. Every non-member's action mask is restricted to action 0, while coalition members retain the environment-defined feasibility mask. Thus, \(v(S)\) measures network performance when exactly the members of \(S\) may apply the trained residual policy. The empty coalition \(\emptyset\) is the native-actuated baseline, and the grand coalition \(N\) permits residual intervention at all nine selected signals.

## 3.2 Counterfactual replay and characteristic value

Coalitions are compared using full-history replay from simulation time \(t=0\) under the same condition and random seed. For each seed, outcomes are normalized against that seed's own empty-coalition baseline.

Let \(q_S\), \(w_S\), \(c_S\), and \(a_S\) denote mean halting vehicles, mean lane-summed waiting time, CO2 emissions on selected approaches, and completed arrivals for coalition \(S\), respectively. With paired native baseline \(q_0,w_0,c_0,a_0\), the normalized performance changes are

\[
d_q(S)=\frac{q_0-q_S}{q_0},\qquad
d_w(S)=\frac{w_0-w_S}{w_0},
\tag{1}
\]

\[
d_c(S)=\frac{c_0-c_S}{c_0},\qquad
d_a(S)=\frac{a_S-a_0}{a_0}.
\tag{2}
\]

Positive \(d_q(S)\), \(d_w(S)\), and \(d_c(S)\) indicate desirable reductions, whereas positive \(d_a(S)\) indicates increased completed throughput. The balanced characteristic value is

\[
v(S)=0.35d_q(S)+0.30d_w(S)+0.20d_c(S)+0.15d_a(S).
\tag{3}
\]

By construction, \(v(\emptyset)=0\). The signed arrival component penalizes apparent congestion improvements obtained by suppressing completed traffic. Alternative scalarizations and explicit throughput constraints are evaluated separately.

## 3.3 Exact Shapley value

For the nine-player game, the exact Shapley value of player \(i\in N\) is

\[
\phi_i=
\sum_{S\subseteq N\setminus\{i\}}
\frac{|S|!\,(n-|S|-1)!}{n!}
\left[v(S\cup\{i\})-v(S)\right].
\tag{4}
\]

Because the complete \(2^9=512\) coalition space is evaluated, Eq. (4) is computed exactly rather than through coalition sampling. The efficiency property is verified numerically as

\[
\sum_{i\in N}\phi_i=v(N).
\tag{5}
\]

## 3.4 Core, least core, and nucleolus

For an efficient allocation \(x=(x_i)_{i\in N}\) satisfying Eq. (8), the excess of coalition \(S\) is defined as

\[
e(S,x)=v(S)-\sum_{i\in S}x_i.
\tag{6}
\]

The core is the set of efficient allocations for which

\[
e(S,x)\le 0,\qquad \forall S\subseteq N.
\tag{7}
\]

When the core is empty, the least-core allocation is obtained from

\[
\min_{x,\epsilon}\;\epsilon
\tag{8}
\]

subject to

\[
v(S)-\sum_{i\in S}x_i\le\epsilon,
\qquad \forall\,\emptyset\ne S\subsetneq N,
\tag{9}
\]

and the efficiency constraint

\[
\sum_{i\in N}x_i=v(N).
\tag{10}
\]

The nucleolus lexicographically minimizes the ordered vector of coalition excesses. In the balanced exact game studied here, the first least-core stage already determines a unique efficient allocation: the binding coalition constraints together with Eq. (10) have allocation rank nine. Consequently, no further lexicographic LP stage can alter the allocation, and this unique least-core solution is the nucleolus. Allocations are interpreted as normalized performance-credit or participation-value allocations, not monetary transfers.

## 3.5 Sensitivity and robustness

Six utility-weight scenarios are examined: balanced, queue-priority, waiting-priority, CO2-priority, throughput-priority, and equal weighting. A separate throughput-protection analysis restricts admissible coalitions according to a minimum arrival-change threshold \(d_a(S)\ge\tau_a\), including the strict no-throughput-loss case \(\tau_a=0\).

For stochastic robustness, a pre-specified critical coalition panel is evaluated on held-out seeds 9002-9005. Five-seed summaries combine these runs with the exact seed-9001 realization. For coalition \(S\), its seed-wise paired advantage over the grand coalition is \(\Delta_s(S)=v_s(S)-v_s(N)\). Paired differences are summarized by the mean \(\bar{\Delta}\), a 95% Student-\(t\) confidence interval, Cohen's \(d_z=\bar{\Delta}/s_{\Delta}\), a paired \(t\)-test, and an exact two-sided Wilcoxon signed-rank test. Given \(n=5\), interpretation emphasizes effect magnitude, interval estimates, and directional consistency rather than relying on a single significance threshold.

# 4. Experimental Setup

The experiments use the Luxembourg SUMO Traffic (LuST) scenario [1,2] with the legacy SUMO 0.27 execution stack retained by the present validated pipeline; SUMO provides the microscopic simulation environment [3]. The public LuST release was originally generated and validated with SUMO 0.26. Accordingly, use of SUMO 0.27 here is reported as a pinned compatibility choice of this experimental pipeline, not as the original LuST validation version. Scenario and simulator revisions are pinned for reproducibility. Nine selected signalized intersections form the player set, while background demand, routing, and native transition sequences remain unchanged.

The exact game uses the AM-peak condition, a 1800 s evaluation horizon, and seed 9001. AM peak was selected because preliminary screening showed meaningful residual intervention activity; Off-peak screening produced no informative interventions. All 512 coalitions are replayed from t=0. Saved-state initialization is not used because the legacy scenario exposed an incompatible bus car-following-model reload path.

The validated Phase2b residual MAPPO checkpoint is used without retraining. The automated evaluation retrieves validated upstream artifacts, verifies evaluator compilation and TraCI compatibility, checks coalition integrity, and stores raw and normalized coalition results. Four held-out seeds (9002-9005) use the same AM-peak horizon and controller checkpoint but evaluate only a critical coalition panel rather than all 512 coalitions.

# 5. Results

## 5.1 Exact coalition landscape

The complete seed-9001 game is strongly non-monotonic with coalition size. Mean coalition value is negative for every intermediate size from one through eight, while the grand coalition achieves only v(N)=0.0075955. The global maximum is A3+A4+A7+A8+A9 with v(S)=0.045507, approximately 5.99 times the grand-coalition value.

Relative to native actuated control, this five-player coalition reduces mean halting vehicles by 6.10%, waiting time by 7.96%, and CO2 by 0.50%, while completed arrivals decrease by 0.47%. It requires 26 residual interventions, compared with 54 for the grand coalition. The grand coalition yields only 1.64% queue reduction, 0.62% waiting-time reduction, and 0.37% CO2 reduction, with arrivals decreasing by 0.51%. Selective participation therefore produces substantially greater congestion benefit with fewer interventions.

**Table R1.** Performance of the native-actuated baseline, exact-best coalition, throughput-protected coalition, and grand coalition. Queue, waiting, and CO2 entries are reported as improvements relative to baseline; arrival change retains its natural sign.

| Case | Coalition | v(S) | Queue improvement (%) | Waiting improvement (%) | CO2 improvement (%) | Arrivals change (%) |
|---|---|---:|---:|---:|---:|---:|
| Native actuated baseline | empty | 0.00000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Exact best | A3+A4+A7+A8+A9 | 0.04551 | 6.10 | 7.96 | 0.50 | -0.47 |
| Throughput-protected | A1+A3+A4 | 0.03744 | 4.86 | 7.12 | -0.51 | +0.07 |
| Grand coalition | A1+A2+A3+A4+A5+A6+A7+A8+A9 | 0.00760 | 1.64 | 0.62 | 0.37 | -0.51 |

**Figure R1.** Balanced characteristic value versus coalition size for all 512 coalitions. The exact maximum and grand coalition are highlighted.

**Figure R1 source artifact:** `Figure_R1_coalition_value_vs_size.png` in the validated Phase3A publication package. Visual audit passed: all 512 coalition values are displayed by coalition size; the exact optimum and grand coalition are separately identified.

## 5.2 Exact contribution attribution

Exact Shapley values reveal substantial heterogeneity. A1 (0.02617) and A3 (0.02055) have the largest positive average marginal contributions, whereas A2 (-0.03185) and A5 (-0.01103) have the strongest negative contributions. These rankings cannot be inferred reliably from singleton behavior because pair and triple screening shows strong compensatory and antagonistic interactions.

**Table R2.** Singleton values, exact Shapley values, nucleolus allocations, and individual-rationality indicators for all nine players.

| Player | Singleton v | Shapley | Nucleolus | Shapley IR | Nucleolus IR |
|---|---:|---:|---:|:---:|:---:|
| A1 | 0.00185 | 0.02617 | 0.02451 | Yes | Yes |
| A2 | -0.08326 | -0.03185 | -0.02951 | Yes | Yes |
| A3 | 0.02027 | 0.02055 | 0.01701 | Yes | No |
| A4 | 0.01327 | 0.00305 | 0.00624 | No | No |
| A5 | 0.00545 | -0.01103 | -0.00704 | No | No |
| A6 | -0.01598 | -0.00167 | -0.00336 | Yes | Yes |
| A7 | -0.00506 | 0.00080 | 0.00212 | Yes | Yes |
| A8 | -0.01325 | -0.00093 | -0.01275 | Yes | Yes |
| A9 | -0.01163 | 0.00250 | 0.01038 | Yes | Yes |

## 5.3 Core stability and nucleolus

The exact balanced game has an empty core. The least-core radius is epsilon*=0.0227054, so no efficient allocation can eliminate all coalition incentives to deviate. The rank-nine binding system uniquely determines the nucleolus.

The maximum coalition excess under the Shapley allocation is 0.0328689. Under the nucleolus it falls to 0.0227054, a reduction of approximately 30.9%. The nucleolus therefore reduces worst-case dissatisfaction but does not make the game core-stable.

**Figure R2.** Exact Shapley and nucleolus allocations for A1-A9.

**Figure R2 source artifact:** `Figure_R2_shapley_vs_nucleolus.png` in the validated Phase3A publication package. Visual audit passed: paired Shapley/nucleolus allocations and the zero reference are legible for A1-A9.

## 5.4 Utility and throughput sensitivity

The empty-core result persists under all six scalarizations. A1 remains the highest-Shapley player and A2 the lowest in every scenario, and the grand coalition is never the highest-value coalition. The preferred coalition alternates only between A3+A4+A7+A8+A9 and A1+A2+A3+A4+A7.

**Table R3.** Utility-weight sensitivity of coalition selection, grand-coalition value, Shapley ranking, core feasibility, and least-core radius.

| Scenario | Best coalition | Best v | Grand v | Top Shapley | Bottom Shapley | Core feasible | Least-core epsilon |
|---|---|---:|---:|---|---|:---:|---:|
| Balanced | A3+A4+A7+A8+A9 | 0.04551 | 0.00760 | A1 | A2 | No | 0.02271 |
| Queue-priority | A1+A2+A3+A4+A7 | 0.04974 | 0.01033 | A1 | A2 | No | 0.02617 |
| Waiting-priority | A3+A4+A7+A8+A9 | 0.05624 | 0.00676 | A1 | A2 | No | 0.02727 |
| CO2-priority | A1+A2+A3+A4+A7 | 0.03065 | 0.00586 | A1 | A2 | No | 0.01634 |
| Throughput-priority | A3+A4+A7+A8+A9 | 0.02625 | 0.00234 | A1 | A2 | No | 0.01306 |
| Equal | A3+A4+A7+A8+A9 | 0.03521 | 0.00531 | A1 | A2 | No | 0.01755 |

Under the strict non-negative-arrival condition, only seven non-empty coalitions remain feasible. A1+A3+A4 is the best feasible coalition, with v(S)=0.037443. It reduces queue by 4.86% and waiting time by 7.12%, increases completed arrivals by approximately 0.075%, and worsens CO2 by approximately 0.51%. This explicitly exposes the throughput-emissions trade-off rather than hiding it inside the scalar utility.

## 5.5 Multi-seed robustness

Across five realizations, A1+A3+A4 achieves mean balanced utility 0.04396 ± 0.01236, mean queue improvement 5.52% ± 1.61%, mean waiting-time improvement 8.66% ± 2.15%, and mean arrival change +0.26% ± 0.35%. Its mean CO2 gain is negative, corresponding to an average CO2 worsening of approximately 0.87%; this trade-off is retained in the interpretation.

A1+A3+A4 exceeds the grand coalition in all five seeds. The paired utility advantage is +0.03490 (95% CI +0.02432 to +0.04549), Cohen's dz=4.10, paired t-test p=0.00079, and exact two-sided Wilcoxon p=0.0625. With only five pairs, the result is interpreted primarily through effect magnitude, confidence interval, and 5/5 directional consistency.

The seed-9001 exact optimum A3+A4+A7+A8+A9 also exceeds the grand coalition in all five realizations, with mean paired advantage +0.02945 (95% CI +0.01285 to +0.04606; dz=2.20). A1+A3+A4 is the highest-utility coalition among the tested critical panel in three of the four held-out seeds; A3+A4+A8+A9 is highest in seed 9004. This is a panel-win result, not a global-optimum claim.

**Table R4.** Five-seed robustness of focal selective coalitions and the grand coalition.

| Coalition | Mean v | SD | Min | Max | Positive seeds |
|---|---:|---:|---:|---:|---:|
| A1+A3+A4 | 0.04396 | 0.01236 | 0.02586 | 0.05527 | 5/5 |
| A3+A4+A7+A8+A9 | 0.03851 | 0.00613 | 0.02914 | 0.04551 | 5/5 |
| Grand coalition | 0.00906 | 0.01007 | -0.00578 | 0.02024 | 4/5 |

**Figure R3.** Seed-wise balanced utility for A1+A3+A4, A3+A4+A7+A8+A9, and the grand coalition.

**Figure R3 source artifact:** `Figure_R3_seedwise_utility.png` in the validated Phase3A publication package. Visual audit passed: seed-wise utilities for both focal selective coalitions and the grand coalition are shown, including the negative grand-coalition outcome for seed 9004.

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

# References

[1] L. Codeca, R. Frank, and T. Engel, “Luxembourg SUMO Traffic (LuST) Scenario: 24 Hours of Mobility for Vehicular Networking Research,” IEEE VNC, 2015, pp. 1–8. doi: 10.1109/VNC.2015.7385539.

[2] L. Codeca, R. Frank, S. Faye, and T. Engel, “Luxembourg SUMO Traffic (LuST) Scenario: Traffic Demand Evaluation,” IEEE Intelligent Transportation Systems Magazine, vol. 9, no. 2, pp. 52–63, 2017. doi: 10.1109/MITS.2017.2666585.

[3] D. Krajzewicz, “Traffic Simulation with SUMO—Simulation of Urban Mobility,” in Fundamentals of Traffic Simulation, Springer, 2010, pp. 269–294. doi: 10.1007/978-1-4419-6142-6_7.

[4] J. N. Foerster, G. Farquhar, T. Afouras, N. Nardelli, and S. Whiteson, “Counterfactual Multi-Agent Policy Gradients,” AAAI, vol. 32, no. 1, pp. 2974–2982, 2018. doi: 10.1609/AAAI.V32I1.11794.

[5] C. Yu et al., “The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games,” NeurIPS, 2022.

[6] T. Chu, J. Wang, L. Codeca, and Z. Li, “Multi-Agent Deep Reinforcement Learning for Large-Scale Traffic Signal Control,” IEEE Transactions on Intelligent Transportation Systems, vol. 21, no. 3, pp. 1086–1095, 2020. doi: 10.1109/TITS.2019.2901791.

[7] H. Wei et al., “CoLight: Learning Network-level Cooperation for Traffic Signal Control,” CIKM, 2019, pp. 1913–1922. doi: 10.1145/3357384.3357902.

[8] Z. Li, H. Yu, G. Zhang, S. Dong, and C.-Z. Xu, “Network-wide traffic signal control optimization using a multi-agent deep reinforcement learning,” Transportation Research Part C, vol. 125, 103059, 2021. doi: 10.1016/j.trc.2021.103059.

[9] M. Miletić, E. Ivanjko, M. Gregurić, and K. Kušić, “A review of reinforcement learning applications in adaptive traffic signal control,” IET Intelligent Transport Systems, vol. 16, no. 10, pp. 1269–1285, 2022. doi: 10.1049/itr2.12208.

[10] X. Zang et al., “MetaLight: Value-Based Meta-Reinforcement Learning for Traffic Signal Control,” AAAI, vol. 34, no. 1, 2020. doi: 10.1609/aaai.v34i01.5467.

[11] X. (Ben) Song, B. Zhou, and D. Ma, “Cooperative traffic signal control through a counterfactual multi-agent deep actor critic approach,” Transportation Research Part C, vol. 160, 104528, 2024. doi: 10.1016/j.trc.2024.104528.

[12] Y. Bie, Y. Ji, and D. Ma, “Multi-agent Deep Reinforcement Learning collaborative Traffic Signal Control method considering intersection heterogeneity,” Transportation Research Part C, vol. 164, 104663, 2024. doi: 10.1016/j.trc.2024.104663.

[13] Y. Ren et al., “Is cooperative always better? Multi-Agent Reinforcement Learning with explicit neighborhood backtracking for network-wide traffic signal control,” Transportation Research Part C, vol. 179, 105265, 2025. doi: 10.1016/j.trc.2025.105265.

[14] R. Bokade, X. Jin, and C. Amato, “Multi-Agent Reinforcement Learning Based on Representational Communication for Large-Scale Traffic Signal Control,” IEEE Access, vol. 11, pp. 47646–47658, 2023. doi: 10.1109/ACCESS.2023.3275883.

[15] R. Zhu et al., “Auto-learning communication reinforcement learning for multi-intersection traffic light control,” Knowledge-Based Systems, vol. 275, 110696, 2023. doi: 10.1016/j.knosys.2023.110696.

[16] S. Yang, “Hierarchical graph multi-agent reinforcement learning for traffic signal control,” Information Sciences, vol. 634, pp. 55–72, 2023. doi: 10.1016/j.ins.2023.03.087.

[17] S. Abidi, P. Mathieu, and A. Nongaillard, “Analyzing communication policies in cooperative multi-agent reinforcement learning for traffic signal control: A simulation-based study,” Simulation Modelling Practice and Theory, vol. 141, 103100, 2025. doi: 10.1016/j.simpat.2025.103100.

[18] J. Liu, S. Qin, M. Su, Y. Luo, Y. Wang, and S. Yang, “Multiple intersections traffic signal control based on cooperative multi-agent reinforcement learning,” Information Sciences, vol. 647, 119484, 2023. doi: 10.1016/j.ins.2023.119484.

[19] Q. Che, Q. Wang, Y. Wang, X. Liu, W. Wang, and M. Song, “Shapley value-based congestion attribution: A practical multiagent reinforcement learning for traffic signal control,” Journal of Nanjing University (Natural Sciences), vol. 62, no. 1, pp. 59–68, 2026. doi: 10.13232/j.cnki.jnju.2026.01.006.

[20] W. Du, J. Ye, J. Gu, J. Li, H. Wei, and G. Wang, “SafeLight: A Reinforcement Learning Method toward Collision-Free Traffic Signal Control,” AAAI, vol. 37, no. 12, pp. 14801–14810, 2023. doi: 10.1609/aaai.v37i12.26729.

[21] L. S. Shapley, “A Value for n-Person Games,” in Contributions to the Theory of Games II, Princeton University Press, 1953, pp. 307–317.

[22] L. S. Shapley, “On balanced sets and cores,” Naval Research Logistics Quarterly, vol. 14, no. 4, pp. 453–460, 1967. doi: 10.1002/nav.3800140404.

[23] D. Schmeidler, “The Nucleolus of a Characteristic Function Game,” SIAM Journal on Applied Mathematics, vol. 17, no. 6, pp. 1163–1170, 1969. doi: 10.1137/0117107.

[24] E. Kohlberg, “On the Nucleolus of a Characteristic Function Game,” SIAM Journal on Applied Mathematics, vol. 20, no. 1, pp. 62–66, 1971. doi: 10.1137/0120009.

[25] T. Lu and L. Quadrifoglio, “Fair cost allocation for ridesharing services—modeling, mathematical programming and an algorithm to find the nucleolus,” Transportation Research Part B, vol. 121, pp. 41–55, 2019. doi: 10.1016/j.trb.2019.01.001.

[26] N. Öner and G. Kuyzu, “Core stable coalition selection in collaborative truckload transportation procurement,” Transportation Research Part E, vol. 154, 102447, 2021. doi: 10.1016/j.tre.2021.102447.

[27] Y. Du, W. Shen, C. Liu, S. Wang, J. Wang, and J. Ke, “A multi-agent deep reinforcement learning framework for coordinated urban traffic signal and parking lot exit control,” Transportation Research Part C, vol. 192, 105856, 2026. doi: 10.1016/j.trc.2026.105856.
