#!/usr/bin/env python3
"""Stakeholder-coalition evaluator for the validated LuST/SUMO-0.27 residual controller.
Players: TA, MO, VI, EC. EC uses the validated 60-s persistence forecast q(t+60)=q(t).
This stage is evaluation/counterfactual analysis; it does not fabricate a new trained policy.
"""
import argparse,csv,json,math,os,sys,time
PLAYERS=("TA","MO","VI","EC")
def coalitions():
    z=[]
    for bits in range(1,16):
        c=tuple(p for i,p in enumerate(PLAYERS) if bits&(1<<i))
        if c!=("EC",): z.append(c)
    return z
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir",required=True);ap.add_argument("--seed",type=int,required=True)
    ap.add_argument("--condition",required=True);ap.add_argument("--smoke-csv",required=True)
    args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
    # Full SUMO stakeholder implementation is intentionally gated on the already validated
    # stakeholder smoke artifact. This preflight prevents launching expensive jobs with a
    # malformed 4-player game.
    rows=list(csv.DictReader(open(args.smoke_csv)))
    labels={r["coalition"] for r in rows}; expected={"+".join(c) for c in coalitions()}
    assert labels==expected,(labels^expected)
    assert "EC" not in labels and len(labels)==14
    out=[]
    for c in coalitions():
        out.append({"seed":args.seed,"condition":args.condition,"coalition":"+".join(c),
                    "TA":int("TA" in c),"MO":int("MO" in c),"VI":int("VI" in c),"EC":int("EC" in c),
                    "forecast_horizon_s":60,"forecast_model":"persistence" if "EC" in c else "none",
                    "status":"preflight_validated"})
    with open(os.path.join(args.outdir,"stakeholder_matrix.csv"),"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=out[0].keys());w.writeheader();w.writerows(out)
    json.dump({"players":PLAYERS,"feasible_coalitions":14,"excluded":["EC"],"persistence_definition":"halting_count(t+60s)=halting_count(t)",
               "seed":args.seed,"condition":args.condition,"note":"preflight only; no performance claim"},open(os.path.join(args.outdir,"metadata.json"),"w"),indent=2)
if __name__=="__main__":main()
