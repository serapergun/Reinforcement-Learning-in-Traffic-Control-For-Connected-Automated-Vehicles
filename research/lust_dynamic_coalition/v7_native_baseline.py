#!/usr/bin/env python3
"""Independent native-actuated LuST baseline for V7 held-out test seeds.

This produces only baseline data. No MAPPO superiority is inferred.
"""
import argparse,csv,hashlib,json,os,random,sys
from pathlib import Path

TLS = ["-17662","-13722","-26466","-28210","-16312","-17612","-18372","-1458","-14740"]
WINDOWS = {"Off-peak":2,"AM":8,"Lunch":13,"PM":18}

def main():
    p=argparse.ArgumentParser()
    for opt in ("sumo","sumo-tools","scenario","outdir"): p.add_argument("--"+opt,required=True)
    p.add_argument("--seeds",default="9301,9302")
    p.add_argument("--condition",choices=list(WINDOWS),default="AM")
    p.add_argument("--eval-s",type=int,default=900)
    a=p.parse_args()
    seeds=[int(z) for z in a.seeds.split(",") if z.strip()]
    if len(seeds)!=len(set(seeds)) or len(seeds)<1: p.error("Seeds must be unique")
    if a.eval_s<=0 or a.eval_s%10: p.error("Evaluation length must be positive multiple of 10")
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    sys.path.insert(0,str(Path(a.sumo_tools).resolve()))
    import traci
    from train_mappo_legacy_replay import native_eval
    selection=[{"agent_alias":f"A{i+1}","tls_id":tl} for i,tl in enumerate(TLS)]
    folder=Path(a.outdir); folder.mkdir(parents=True,exist_ok=True)
    metrics=[]
    for seed in seeds:
        result=native_eval(traci,a.sumo,a.scenario,selection,WINDOWS[a.condition]*3600,a.eval_s,seed)
        row={"condition":a.condition,"seed":seed,"coalition":"native","strategy":"native",**result}
        metrics.append(row)
        with (folder/"v7_native_baselines.csv").open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for x in metrics for k in x)))
            w.writeheader();w.writerows(metrics)
        print("NATIVE_SUMMARY",json.dumps(row,sort_keys=True),flush=True)
    provenance={
        "status":"real_SUMO_native_baseline_only","rows":len(metrics),"seeds":seeds,
        "condition":a.condition,"eval_s":a.eval_s,"control_start_s":WINDOWS[a.condition]*3600,
        "sumo_commit":"7eac6a1b2543aa902fa2eff8ae82548eaa4cce6b",
        "lust_commit":"c4bd5bd3751d426d42a9a1749c815e47ea188549",
        "selected_tls_ids":TLS,
        "selection_basis":"archived VALIDATION_STATUS.md, not expired selection artifact",
        "code_source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "checkpoint_used":False,
        "limitations":["No MAPPO or dynamic comparison","AM condition only",
                       "Selected-approach CO2 and global arrived vehicles have different scope"]
    }
    (folder/"provenance.json").write_text(json.dumps(provenance,indent=2))
    assert len(metrics)==len(seeds)
if __name__=="__main__": main()
