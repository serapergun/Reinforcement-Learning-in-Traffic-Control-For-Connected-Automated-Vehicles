# Real LuST v2.0 baseline experiment

This branch is isolated from the default branch and is used only for the urban-mobility digital-twin / dynamic-coalition study.

The workflow downloads the official `lcodeca/LuSTScenario` **v2.0** release, installs SUMO on the GitHub Actions runner, executes the official DUE + actuated-TLS scenario, and derives the nine controlled traffic-signal agents from measured baseline congestion.

The selection metric is:
`CI = 0.30 Q_norm + 0.25 O_norm + 0.30 TL_norm + 0.15 F_norm`

where Q is E2 mean maximum jam length in vehicles, O is mean occupancy, TL is detector time-loss accumulation, and F is detector entries. A robust score combines AM/Lunch/PM as 0.40/0.20/0.40. A connectivity-aware greedy constraint is then applied to obtain nine spatially connected/high-congestion TLS agents.

No benchmark or synthetic result is inserted into the outputs. All CSV/figure values in the workflow artifact are parsed from the actual SUMO execution.
