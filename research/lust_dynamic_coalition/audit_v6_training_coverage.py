#!/usr/bin/env python3
"""Publication-safe audit of NEW V6 MAPPO pilot (no claim of converged policy)."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

PLAYERS = ("TA", "MO", "VI", "EC")
CONDITIONS = ("Off-peak", "AM", "Lunch", "PM")
FEASIBLE = {
    "+".join(c)
    for k in range(1, 5)
    for c in combinations(PLAYERS, k)
    if c != ("EC",)
}

def audit(folder):
    folder = Path(folder)
    hist = list(csv.DictReader((folder / "training_history.csv").open(newline="", encoding="utf-8")))
    prov = json.loads((folder / "provenance_v6.json").read_text())
    smoke = json.loads((folder / "smoke.json").read_text())
    checkpoint = (folder / "stakeholder_mappo.pt").read_bytes()
    sha = hashlib.sha256(checkpoint).hexdigest()
    if sha != prov.get("sha256"):
        raise ValueError("Checkpoint SHA256 does not match archived provenance")
    if not prov.get("checkpoint_present"):
        raise ValueError("Training provenance says no checkpoint")
    episodes = [int(r["episode"]) for r in hist]
    if episodes != list(range(1, len(hist) + 1)):
        raise ValueError("Episode indices have gaps or duplicates")
    combos = [(r["condition"], r["coalition"]) for r in hist]
    if any(c not in CONDITIONS or s not in FEASIBLE for c, s in combos):
        raise ValueError("Unknown training condition or coalition")
    if len(hist) != int(prov["episodes"]):
        raise ValueError("Training history length differs from provenance")
    seeds = [int(r["seed"]) for r in hist]
    if len(seeds) != len(set(seeds)):
        raise ValueError("Repeated training seed")
    eligible = int(smoke["mask_eligible_slots"])
    interventions = int(smoke["interventions"])
    eligible_a2 = int(smoke["eligible_action2"])
    if eligible < interventions or eligible < eligible_a2:
        raise ValueError("Inconsistent intervention/eligibility counters")
    if sum(int(smoke[f"eligible_action{i}"]) for i in range(3)) != eligible:
        raise ValueError("Eligible action histogram inconsistent")
    distinct = set(combos)
    covered_coalitions = set(s for _, s in distinct)
    result = {
        "status": "AUDITED_PILOT_NOT_PUBLICATION_READY",
        "checkpoint_sha256": sha,
        "model": "NEW V6 pilot; NOT recovered original checkpoint",
        "episode_count": len(hist),
        "distinct_coalitions": len(covered_coalitions),
        "feasible_coalitions": len(FEASIBLE),
        "seen_condition_coalition_pairs": len(distinct),
        "total_condition_coalition_pairs": len(CONDITIONS) * len(FEASIBLE),
        "coverage_fraction": len(distinct) / (len(CONDITIONS) * len(FEASIBLE)),
        "condition_episode_counts": dict(sorted(Counter(c for c, _ in combos).items())),
        "smoke_seed": smoke["seed"],
        "smoke_condition": smoke["condition"],
        "smoke_eligible_slots": eligible,
        "smoke_interventions": interventions,
        "smoke_plus6_actions": eligible_a2,
        "smoke_intervention_fraction": interventions / eligible if eligible else None,
        "smoke_saturation_warning": bool(smoke.get("policy_saturation_warning", False)),
        "limitations": [
            "14 short episodes do not show PPO convergence",
            "Only 14 of 56 possible coalition-condition training pairs represented",
            "A single grand-coalition smoke test cannot demonstrate general behavior",
            "All 54 eligible smoke slots used +6 second green extensions",
            "Independent V7 held-out evaluation required before any traffic performance comparison",
            "No evidence for original checkpoint equivalence or multi-condition robustness",
        ],
    }
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--training-dir", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = audit(a.training_dir)
    target = Path(a.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2))
if __name__ == "__main__":
    main()
