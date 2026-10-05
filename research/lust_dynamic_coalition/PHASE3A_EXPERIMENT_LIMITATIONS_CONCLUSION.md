# 4. Experimental Setup

## 4.1 LuST network and simulation environment

Experiments use the Luxembourg SUMO Traffic (LuST) scenario and the legacy SUMO 0.27 execution stack used by the validated training/evaluation pipeline. LuST provides a city-scale Luxembourg mobility scenario with a full-day demand profile, public-transport activity, road-network geometry, and actuated traffic-signal configurations. To preserve compatibility with the validated experimental pipeline, both the LuST scenario revision and SUMO revision are pinned during automated runs rather than replaced by a newer simulator version.

Nine signalized intersections are selected as the controlled player set. Each selected traffic signal is represented by one residual-control agent A1-A9. The cooperative-game experiment does not modify background demand, route generation, or the native signal-transition sequence. Instead, coalition membership controls only whether a selected signal may invoke the trained residual supervisor.

## 4.2 Residual MAPPO controller and baseline

The experimental controller is the validated Phase2b residual MAPPO checkpoint. Native actuated control is retained as the reference controller. At eligible decision points the learned supervisor selects among three actions: no intervention, a +3 s extension of the remaining green interval, or a +6 s extension. Yellow, all-red, and transition-to-next-green behavior remain governed by the native signal program.

This architecture is important for the experimental interpretation. A coalition does not replace the signal controllers of its members; it grants those members permission to apply limited learned corrections. Non-members are forced to the no-intervention action and therefore continue under native actuated behavior.

## 4.3 Evaluation condition and exact game

The exact cooperative-game experiment uses the AM-peak traffic condition, an 1800 s evaluation horizon, and seed 9001. The AM period was selected after preliminary evaluation because it provides substantial traffic demand and meaningful residual intervention activity; the Off-peak screening condition produced no informative intervention activity.

For nine players, the complete game contains 512 coalitions. Every coalition is replayed from simulation time zero under the same seeded traffic realization. The empty coalition supplies the paired native-actuated baseline. This design yields the complete characteristic function required for exact Shapley, core, least-core, and nucleolus calculations.

## 4.4 Performance measures

Four network measures are used to construct coalition value: mean halting vehicles, mean lane-summed waiting time, CO2 emissions on the selected approaches, and globally completed arrivals. Queue, waiting, and CO2 are converted to relative reductions against the paired native baseline, while arrivals are represented as a signed relative change. The balanced utility uses weights 0.35, 0.30, 0.20, and 0.15, respectively.

The signed arrival term serves as a throughput safeguard: a policy cannot obtain an unqualified positive score merely by reducing the number of vehicles reaching congested parts of the network. A separate throughput-constrained analysis is also performed because a scalar weighted utility cannot fully represent all operational preferences.

## 4.5 Robustness protocol

Four held-out seeds, 9002-9005, are used to evaluate a pre-specified critical coalition panel. The panel includes the seed-9001 exact optimum, the zero-throughput-loss candidate, a queue/CO2-priority candidate, stability-critical coalitions, the empty baseline, and the grand coalition. The same AM-peak horizon, controller checkpoint, scenario revision, and replay procedure are retained.

The held-out experiment is deliberately targeted rather than exhaustive. It tests whether the most important selective-versus-grand conclusions survive independent stochastic realizations without incurring four additional complete 512-coalition evaluations. Accordingly, held-out panel winners are reported as panel winners and not as global optima.

## 4.6 Reproducibility safeguards

The automated evaluation pins the LuST and SUMO revisions, downloads the validated Phase2/Phase2b artifacts, checks evaluator compilation and TraCI compatibility, executes deterministic full-history replay, validates expected coalition membership in output artifacts, and stores coalition-level raw and normalized results. Saved-state initialization is not used because the legacy scenario exposed an incompatible bus car-following-model reload path. Full-history replay avoids that incompatibility and preserves a common initialization protocol across coalitions.

# 7. Limitations

Several limitations define the scope of the conclusions.

First, complete 512-coalition enumeration is performed for the AM-peak seed-9001 realization. The four additional seeds evaluate a targeted critical panel rather than reconstructing the entire cooperative game. The multi-seed results therefore establish robustness of the tested selective-cooperation pattern but do not establish the exact global optimum, Shapley allocation, core status, or nucleolus separately for every seed.

Second, the cooperative game is evaluated for one traffic period. Off-peak screening generated negligible residual activity and was therefore unsuitable for meaningful coalition differentiation. Lunch and PM conditions are not part of the present exact-game analysis. Extending the critical-panel protocol to additional congested periods would strengthen claims about temporal generalization.

Third, the evidence is simulation-based. LuST provides a city-scale scenario and the residual architecture preserves native actuated signal logic, but the results do not constitute field deployment evidence. Sensor noise, communication delay, controller hardware constraints, incident conditions, and behavioral adaptation could alter coalition effects in an operational system.

Fourth, the balanced characteristic value is a preference-dependent scalarization. Queue, waiting time, emissions, and throughput need not have universal weights. Six alternative weighting scenarios and explicit throughput constraints reduce this concern, but they do not eliminate the need for stakeholder-specific objective calibration in deployment.

Fifth, coalition value is defined using network performance rather than monetary welfare. Shapley and nucleolus allocations should therefore be interpreted as normalized performance-credit allocations or participation-value indices unless an explicit economic conversion is introduced. They should not be described as monetary payments.

Finally, the study does not claim uniform superiority of residual MAPPO over native actuated control. Earlier held-out evaluation contains condition/seed combinations in which the learned supervisor does not improve every metric. The contribution of the present analysis is precisely to show that selective permission to intervene can be preferable to unrestricted learned intervention.

# 8. Conclusion

This study reframes cooperative multi-agent traffic signal control as a participation-selection problem. Rather than assuming that every intersection should cooperate whenever a MARL controller is available, a trained residual MAPPO policy is held fixed and the permission to intervene is varied across coalitions of nine traffic signals. Complete counterfactual enumeration of all 512 coalitions produces an exact operational cooperative game.

The results show that coalition composition is more consequential than coalition size. In the seed-9001 AM-peak game, the highest-value five-signal coalition achieves a balanced characteristic value of 0.04551, approximately 5.99 times the grand-coalition value, while reducing mean halting vehicles by 6.10% and waiting time by 7.96% with fewer residual interventions. Exact Shapley values reveal strongly heterogeneous marginal contributions, and the grand coalition is not core-stable. The least-core radius is 0.02271, and the uniquely determined nucleolus reduces maximum coalition dissatisfaction by approximately 30.9% relative to the Shapley allocation.

The principal conclusion is robust to alternative operational preferences. The core remains empty under six utility scalarizations, and the grand coalition is never the highest-value coalition. Under a strict non-negative-throughput constraint, A1+A3+A4 emerges as the preferred selective coalition. Across five stochastic realizations, this coalition and the seed-9001 exact optimum candidate both outperform the grand coalition in every paired comparison, although the held-out experiments are intentionally limited to a critical coalition panel.

These findings support a sparse supervisory view of MARL deployment: learned traffic-control interventions need not be enabled everywhere to obtain network benefit. A practical controller can preserve native actuated logic as the default and selectively authorize residual interventions at intersections whose joint contribution is favorable under the current operational objective. Future work should extend exact or approximate coalition analysis across multiple traffic periods and demand regimes, investigate online coalition adaptation, incorporate communication and sensing uncertainty, and connect performance-credit allocations to explicit incentive or governance mechanisms for real-world cooperative traffic management.
