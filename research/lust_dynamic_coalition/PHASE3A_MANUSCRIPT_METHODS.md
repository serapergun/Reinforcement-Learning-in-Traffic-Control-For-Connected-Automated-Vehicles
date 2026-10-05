# Phase3A manuscript-ready Methodology

## Coalition-constrained residual MARL evaluation

The cooperative-control experiment uses nine selected traffic signals as the player set N={A1,...,A9}. The learned controller is a residual MAPPO supervisor operating on top of the native LuST/SUMO actuated signal logic rather than replacing the underlying controller. At each decision point, action 0 preserves native actuated operation, action 1 requests a +3 s extension of the remaining green interval, and action 2 requests a +6 s extension. Native yellow, all-red, and subsequent-green transitions remain governed by the underlying traffic-signal program. This residual formulation limits the learned policy to feasible supervisory interventions and preserves the validated native controller as the default behavior.

For a coalition S subseteq N, only agents belonging to S are permitted to request residual interventions. The action mask of every non-member is restricted to action 0, while coalition members retain the environment-defined feasibility mask. Therefore v(S) measures the network outcome when exactly the members of S are allowed to apply the trained residual policy and all other signals remain under native actuated control. The empty coalition is identical to the native-actuated baseline and the grand coalition permits residual control at all nine selected signals.

## Deterministic counterfactual replay

Coalitions are compared by full-history replay from simulation time t=0 using the same traffic condition and random seed. Saved-state initialization is not used because the legacy SUMO 0.27 scenario produced an incompatible bus car-following-model reload path. Each coalition is therefore evaluated from the beginning of the same seeded realization. For each seed, all coalition outcomes are normalized against that seed's own native-actuated empty-coalition result, providing a paired counterfactual comparison.

The exact cooperative game is constructed for the AM-peak operating condition with an 1800 s evaluation horizon and seed 9001. With nine players, all 2^9=512 coalitions are enumerated. The complete game is used for exact Shapley, core, least-core, and nucleolus analysis. Four additional held-out seeds (9002-9005) are evaluated only for a pre-specified critical coalition panel and are used as a targeted robustness test; they are not treated as complete cooperative games.

## Characteristic value

For coalition S, let q_S, w_S, c_S, and a_S denote mean halting vehicles, mean lane-summed waiting time, CO2 emissions on the selected approaches, and completed arrivals, respectively. Let the corresponding native-actuated values for the same seed be q_0, w_0, c_0, and a_0. The normalized gains are

dq(S)=(q_0-q_S)/q_0,

dw(S)=(w_0-w_S)/w_0,

dc(S)=(c_0-c_S)/c_0,

da(S)=(a_S-a_0)/a_0.

Thus positive dq, dw, and dc indicate reductions in congestion, delay, and emissions, whereas positive da indicates increased throughput. The balanced characteristic value is

v(S)=0.35 dq(S)+0.30 dw(S)+0.20 dc(S)+0.15 da(S).

The signed throughput component penalizes apparent congestion improvements that arise by suppressing completed arrivals. Because the balanced weights represent one operational preference rather than a universal welfare function, the cooperative-game conclusions are also evaluated under queue-priority, waiting-priority, CO2-priority, throughput-priority, and equal-weight scalarizations.

## Exact Shapley allocation

For n=9 players, the Shapley value of player i is computed from the complete characteristic function as

phi_i = sum_{S subseteq N\{i}} |S|!(n-|S|-1)!/n! [v(S union {i})-v(S)].

All 512 coalition values are available, so no sampling or marginal-contribution approximation is required. Efficiency is checked numerically by verifying sum_i phi_i=v(N).

## Core, excess, least core, and nucleolus

For an efficient allocation x with sum_i x_i=v(N), coalition excess is defined as

e(S,x)=v(S)-sum_{i in S}x_i.

The core requires e(S,x)<=0 for every coalition S. Core feasibility is tested using the complete 512-coalition characteristic function. When the core is empty, the least-core problem minimizes the largest excess:

minimize epsilon

subject to v(S)-sum_{i in S}x_i <= epsilon for all proper non-empty S,

and sum_i x_i=v(N).

For the balanced seed-9001 game, the optimal least-core radius is positive. Nine coalition inequalities are binding at the optimum and, together with efficiency, their incidence system has rank nine. The first least-core stage therefore uniquely determines the allocation; consequently this unique least-core allocation is also the nucleolus of the game. The maximum excess under the nucleolus is compared with the corresponding maximum excess under the Shapley allocation to quantify the reduction in worst-case coalition dissatisfaction.

## Throughput-protection analysis

To distinguish utility-optimal control from throughput-preserving operation, coalitions are additionally filtered using a minimum arrival-gain constraint. The strictest reported case requires da(S)>=0. Among coalitions satisfying this constraint, the coalition with the highest balanced value is selected. Additional thresholds permit progressively larger arrival reductions and reveal how the preferred coalition changes as throughput protection is relaxed.

## Multi-seed robustness and statistical analysis

The seed-9001 exact optimum candidate, the zero-throughput-loss candidate, alternative utility-priority candidate, stability-critical coalitions, the empty baseline, and the grand coalition are re-evaluated independently for seeds 9002-9005 using the same AM-peak 1800 s protocol. Each controlled result is paired with the native-actuated baseline from the same seed.

Five-seed summaries combine the exact-game seed 9001 realization with the four held-out realizations. Results are reported using mean and standard deviation, seed-wise directional consistency, and paired selective-versus-grand differences. For the focal comparison, a 95% confidence interval and Cohen's dz are reported alongside a paired t-test. Because n=5 is small, the exact two-sided Wilcoxon signed-rank result is also reported and statistical interpretation emphasizes effect size, interval estimates, and consistency across seeds rather than dichotomous significance testing.

## Reproducibility boundaries

Exact cooperative-game quantities (Shapley values, core feasibility, least-core radius, and nucleolus) refer only to the complete seed-9001 512-coalition game. The held-out seeds evaluate a targeted critical panel and therefore support robustness claims for the tested coalitions but cannot establish the global optimum or exact cooperative-game allocation for each held-out realization. Off-peak screening produced no meaningful intervention activity and is not used to claim a control benefit. All reported Phase3A conclusions are based on deterministic SUMO 0.27 full-history replay and the validated residual MAPPO checkpoint.
