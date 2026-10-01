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


## Legacy SUMO 0.27 build and TraCI progress (2026-10-01)

The official SUMO 0.27.0 source can now be compiled on the Ubuntu 22.04 GitHub
runner with two narrowly scoped build-compatibility patches:

1. the historical Euler-spiral infinity sentinel `HUGE` is replaced by the
   standard `HUGE_VAL`;
2. the build helper `tools/build/typemap.py` uses `dict.items()` instead of
   the Python-2-only `dict.iteritems()`.

Neither patch touches the microscopic traffic model, car-following model,
lane-changing model, signal logic, routing behavior, or LuST input data.

A Python-3 TraCI smoke test against the compiled SUMO 0.27.0 binary succeeded.
The test observed:

- 201 traffic-light controllers;
- 24,575 lanes;
- correct 1-s simulation stepping (10 calls advanced the clock by exactly 10 s);
- readable traffic-light phase/state, next-switch and phase-duration values;
- readable lane vehicle count, halting count, mean speed, occupancy, waiting
  time and CO2;
- readable vehicle IDs/waiting time.

The first 2-hour standalone LuST smoke run also completed normally. SUMO 0.27
reported 2,229 inserted vehicles from 2,319 loaded by the forced 7,200-s stop,
157 vehicles still running, zero waiting vehicles, and no `Teleports:` line.
In SUMO 0.27 the teleports summary line is omitted when the count is zero, so
the compatibility parser has been corrected to interpret an omitted line as
zero rather than as missing data.

The complete official `due.actuated` reproduction has now passed the
predefined compatibility guards exactly. Under SUMO 0.27.0, the reproduced run
ended at 88,375 s with 284,349 inserted vehicles from 288,250 loaded records,
767 teleports, and zero vehicles running or waiting at termination. These values
match the LuST bundled reference summary exactly (0% relative error for inserted
vehicles and end time). The simulator-compatibility publication gate is
therefore PASSED for the SUMO 0.27.0 path.


## Publication gate PASSED: exact LuST v2.0 reproduction with SUMO 0.27.0

GitHub Actions run **36868507185** completed successfully using the official LuST
v2.0 commit `c4bd5bd3751d426d42a9a1749c815e47ea188549` and SUMO **0.27.0**.

The complete `due.actuated.sumocfg` run reproduced the historical LuST reference
**exactly**:

| Quantity | Reproduced | LuST reference | Difference |
|---|---:|---:|---:|
| Simulation end time | 88,375 s | 88,375 s | 0 |
| Loaded vehicles | 288,250 | 288,250 | 0 |
| Inserted vehicles | 284,349 | 284,349 | 0 |
| Teleports | 767 | 767 | 0 |
| Vehicles still running | 0 | 0 | 0 |
| Waiting vehicles | 0 | 0 | 0 |

The run ended because **all vehicles had left the simulation**. The teleport
breakdown was 7 collision, 224 jam, 378 yield, and 158 wrong-lane teleports.

This exact match resolves the earlier SUMO-version compatibility blocker.
All publication-facing LuST experiments must now be generated on this validated
SUMO 0.27.0 path. The previous SUMO 1.18.0 results remain development/debugging
results only.

A consolidated workflow, `LuST Legacy Publication Pipeline`, has been added to
execute the next publication sequence on the validated simulator path:

1. full-day congestion-based selection of nine actual LuST TLS agents;
2. 10-s, 24-h state dataset collection for the selected nine agents;
3. residual-GRU training and persistence-baseline comparison;
4. guarded residual MAPPO training and paired actuated-controller evaluation;
5. provenance and machine-readable publication gates.


## Full LuST v2.0 reproduction passed

The compatibility gate has now been passed with the pinned official LuST v2.0
commit `c4bd5bd3751d426d42a9a1749c815e47ea188549` and SUMO **0.27.0**.

The complete `due.actuated.sumocfg` run reproduced the bundled LuST reference
**exactly**:

| Quantity | Reproduced | LuST bundled reference |
|---|---:|---:|
| Simulation end time | 88,375 s | 88,375 s |
| Loaded vehicles | 288,250 | 288,250 |
| Inserted vehicles | 284,349 | 284,349 |
| Vehicles still running | 0 | 0 |
| Waiting vehicles | 0 | 0 |
| Teleports | 767 | 767 |
| Collision teleports | 7 | 7 (reported in reproduced log) |
| Jam teleports | 224 | 224 (reported in reproduced log) |
| Yield teleports | 378 | 378 (reported in reproduced log) |
| Wrong-lane teleports | 158 | 158 (reported in reproduced log) |

For the two primary numerical compatibility checks used by the workflow,
`inserted_rel_error = 0.0` and `end_rel_error = 0.0`.

This removes the simulator-version compatibility blocker. From this point
forward, publication-candidate LuST experiments must use the validated
SUMO-0.27 path (or separately re-establish an equally strict compatibility
gate for another simulator version). The earlier SUMO-1.18 experiments remain
engineering/debugging evidence only and must not be mixed into final empirical
tables.


## Validated nine-TLS selection (SUMO 0.27.0)

A separate full-day selection run using the validated simulator path completed
successfully. The selected connected nine-intersection subnetwork is:

| Alias | LuST TLS ID | Robust CI | Incoming lanes |
|---|---:|---:|---:|
| A1 | -17662 | 0.727922 | 8 |
| A2 | -13722 | 0.570303 | 8 |
| A3 | -26466 | 0.482289 | 8 |
| A4 | -28210 | 0.363008 | 6 |
| A5 | -16312 | 0.629143 | 5 |
| A6 | -17612 | 0.194458 | 8 |
| A7 | -18372 | 0.055226 | 8 |
| A8 | -1458 | 0.175220 | 8 |
| A9 | -14740 | 0.149201 | 6 |

The operating hours selected from the full-day congestion profile are:

- Off-peak: 02:00-03:00
- AM peak: 08:00-09:00
- Lunch: 13:00-14:00
- PM peak: 18:00-19:00

The PM window has the largest aggregate E2 halting-duration burden in the
defined peak windows (1,375,906 s), followed by AM (908,692 s) and Lunch
(621,307 s). Off-peak 02:00-03:00 has 6,626 s.

These TLS IDs and operating windows supersede the provisional SUMO 1.18
selection for all publication-oriented experiments.
