# Frozen margin 0.15 — AM coalition diagnostic (2026-10-08)

Source: GitHub Actions run 37651229931, artifact 11514815744, commit 23c83958f8647877a545af27990936754a954615. SUMO 0.27, 900s, 5 paired CRN seeds 9001–9005, 14 feasible coalitions.

## Stop gate

Grand coalition TA+MO+VI+EC: mean eligible intervention fraction 0.142; mean paired halting delta -5.04%; waiting delta -6.64%; CO2 delta +0.32%. The original saturation was corrected for this coalition, but CO2 did not improve.

MO+VI+EC: mean eligible intervention fraction 0.856; mean paired halting delta +15.73%; waiting delta +28.27%; CO2 delta +6.48%. This coalition is unsafe under the globally selected 0.15 margin. Do not run or publish a full four-window comparison as if this controller were uniformly calibrated.

Most other coalitions (12 of 14) either choose native exclusively (11) or show modest intervention (MO+VI ~0.111); this indicates near-degenerate coalition-conditioned policy behavior, not demonstrated robust coalition adaptation.

## Likely mechanism to test

In `train_stakeholder_mappo_legacy.py`, deployment accepts an extension when `p(best_extension)-p(native) >= margin`. This is a probability-gap heuristic and has no per-coalition intervention cap or traffic-outcome guarantee. Different coalition masks can produce very different action probabilities. Training uses only 28 episodes against 56 coalition-condition combinations, so coverage of combinations is incomplete. These are hypotheses, not proven causal diagnoses.

## Next preregistered validation

1. On new calibration seeds disjoint from 9001–9005, evaluate a coalition-specific margin grid and explicitly require intervention <= 0.80 for every coalition; report all 14 coalitions, not only the grand coalition.
2. Keep a separate untouched hold-out seed set; reject the policy if any coalition shows substantial traffic regression or saturation.
3. Report nonintervening coalitions as native-equivalent; do not claim coalition performance improvements for them.
4. Only after passing these gates proceed to Lunch, PM and Off-peak. Preserve original run/artifact provenance.
