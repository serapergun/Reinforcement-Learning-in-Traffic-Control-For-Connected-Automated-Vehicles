#!/usr/bin/env python3
"""SUMO 0.27 coalition smoke harness using the validated residual controller semantics."""
import argparse,csv,json,math,os,sys
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from train_mappo_legacy_replay import Env,MAPPO,rollout,read_csv

PLAYERS=("TA","MO","VI","EC")
def feasible_coalitions():
    out=[]
    for bits in range(1,16):
        c=tuple(PLAYERS[i] for i in range(4) if bits&(1<<i))
        if c==("EC",): continue
        out.append(c)
    return out

def persistence_queue(history):
    return float(history[-1]) if history else 0.0

class CoalitionEnv(Env):
    """Keep validated action/eligibility semantics; mask observation channels only."""
    def __init__(self,*a,coalition=(),**kw):
        super().__init__(*a,**kw); self.coalition=tuple(coalition); self.qhist={}
    @property
    def obs_dim(self): return 17
    def observe(self):
        base=super().observe(); out=[]; c=set(self.coalition)
        for i,tl in enumerate(self.tls):
            s=self.lane_stats(tl); hist=self.qhist.setdefault(tl,[])
            pred=persistence_queue(hist); hist.append(float(s["halt"])); hist[:]=hist[-6:]
            # Validated 13-D controller state, coalition-gated information + 4-bit mask.
            x=base[i].copy()
            if "TA" not in c: x[[0,1,3,4,5]]=0.0
            if "MO" not in c: x[2]=0.0
            # VI is represented conservatively by traffic availability; no fabricated telemetry.
            if "VI" not in c: x[10]=0.0
            ec=np.clip(pred/max(8*s["lanes"],1),0,3) if "EC" in c else 0.0
            mask=np.asarray([1.0 if p in c else 0.0 for p in PLAYERS],dtype=np.float32)
            # EC forecast replaces the otherwise coalition-gated phase-index slot only in the
            # appended coalition feature block; base controller semantics remain untouched.
            out.append(np.concatenate([x,np.asarray([ec],np.float32),mask[:3]]))
        return np.stack(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo",required=True);ap.add_argument("--sumo-tools",required=True)
    ap.add_argument("--scenario",required=True);ap.add_argument("--selection",required=True)
    ap.add_argument("--windows",required=True);ap.add_argument("--outdir",required=True)
    ap.add_argument("--condition",default="AM");ap.add_argument("--control-s",type=int,default=60)
    ap.add_argument("--seed",type=int,default=9299)
    args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
    sys.path.insert(0,os.path.abspath(args.sumo_tools));import traci
    sel=read_csv(args.selection); wins={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(args.windows)}
    assert args.condition in wins
    rows=[]
    for coalition in feasible_coalitions():
        env=CoalitionEnv(traci,args.scenario,sel,wins[args.condition]*3600,args.control_s,args.seed,coalition=coalition)
        agent=MAPPO(len(sel),env.obs_dim,3,args.seed)
        _,s=rollout(env,args.sumo,agent,False)
        rows.append({"coalition":"+".join(coalition),"seed":args.seed,"condition":args.condition,**s})
        print(rows[-1],flush=True)
    path=os.path.join(args.outdir,"coalition_smoke.csv")
    fields=[];seen=set()
    for r in rows:
        for k in r:
            if k not in seen:seen.add(k);fields.append(k)
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    expected={"+".join(c) for c in feasible_coalitions()}
    assert len(rows)==14 and {r["coalition"] for r in rows}==expected and "EC" not in expected
    for r in rows:
        for k in ("mean_halting_vehicles","mean_waiting_time_lane_sum_s","arrived_vehicles_global","CO2_kg_selected_approaches"):
            assert math.isfinite(float(r[k]))
    with open(os.path.join(args.outdir,"run_metadata.json"),"w") as f:
        json.dump({"players":PLAYERS,"feasible_coalitions":sorted(expected),"forecast":"persistence(queue_t -> queue_t+60 proxy)","saved_state_used":False,"controller_semantics":"validated guarded residual native/+3s/+6s"},f,indent=2)
if __name__=="__main__":main()
