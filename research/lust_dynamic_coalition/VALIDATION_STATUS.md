# LuST Experimental Validation Status

## Current publication gate

The official LuST v2.0 scenario is pinned to commit:

`c4bd5bd3751d426d42a9a1749c815e47ea188549`

The LuST v2.0 release states that the scenario was tested with **SUMO 0.26**. The bundled
`docs/LuSTFiles.md` reports its reference simulations under **SUMO 0.27.0**.

Therefore, simulator-version compatibility is treated as a first-class validation
requirement. Results obtained with a materially newer SUMO build are not considered
publication-valid until their traffic-flow behavior is shown to be consistent with the
LuST reference run.

## Observed modern-SUMO mismatch

GitHub Actions baseline run **36567745991** used **SUMO 1.18.0** with the official LuST
v2.0 network and route files. The run itself completed without a fatal SUMO error, but
its network-level traffic behavior is not compatible with the historical LuST reference:

| Quantity | SUMO 1.18.0 run | LuST reference (docs, SUMO 0.27.0) |
|---|---:|---:|
| Loaded vehicles | 288,250 | 288,250 |
| Inserted vehicles | 217,927 | 284,349 |
| Vehicles still running at stop | 78,583 | 0 |
| Waiting vehicles at stop | 211 | 0 |
| Teleports | 150,839 | 767 |
| Stop/end time | 86,400 s (forced end) | 88,375 s (all vehicles left) |

The modern run produced **150,839 teleports**, including large jam/yield/wrong-lane
components, and only 217,927 of 288,250 loaded vehicles were inserted by the forced
24-hour stop. This is a severe compatibility discrepancy rather than ordinary seed noise.

### Consequence

- The SUMO 1.18.0 baseline, GRU, and MAPPO runs are retained as **engineering/debugging
  experiments only**.
- Their values must **not** replace the manuscript's illustrative placeholders as final
  LuST empirical results.
- The selected nine TLS IDs may be retained provisionally for software development, but
  final selection and all publication statistics must be regenerated after simulator
  compatibility is resolved.
- No claim such as “validated LuST traffic” or “real LuST performance improvement” should
  be made from the SUMO 1.18.0 runs.

## Legacy compatibility experiment

Workflow: `LuST Legacy SUMO 0.27 Validation`

Purpose:

1. build SUMO **0.27.0** from official tag `v0_27_0`;
2. run an initial compatibility smoke test;
3. reproduce the official LuST `due.actuated.sumocfg` full run;
4. compare inserted vehicles, teleports, termination state, and end time with the
   historical reference in `docs/LuSTFiles.md`.

The full experiment is accepted for publication use only if:
- all 288,250 demand records are loaded;
- no vehicles remain running/waiting at final termination;
- inserted count is within 1% of the documented 284,349 value;
- teleports remain below a conservative 5,000 threshold;
- end time is within 5% of 88,375 s.

These are compatibility guards, not performance-optimization targets.

## ML/RL validation notes

The completed GRU-v2 residual experiment on the SUMO 1.18.0 dataset did **not** beat the
persistence baseline globally:

- Persistence MAE: 3.8561
- Persistence RMSE: 6.9357
- GRU-v2 MAE: 4.1746
- GRU-v2 RMSE: 7.0265

Thus EC prediction should not be presented as an empirical improvement from that run.
The Digital-Twin predictor must be revalidated on the simulator-compatible dataset.

The first completed 5-seed MAPPO experiment on SUMO 1.18.0 also degraded queueing and
waiting metrics relative to native actuated control. Subsequent residual/supervisory
MAPPO versions are therefore treated only as controller-development experiments until
the simulator compatibility gate is passed.
