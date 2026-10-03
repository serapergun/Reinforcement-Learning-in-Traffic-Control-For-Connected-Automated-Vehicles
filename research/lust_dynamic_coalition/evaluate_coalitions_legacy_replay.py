#!/usr/bin/env python3
"""Phase 3A coalition counterfactual evaluator for validated LuST/SUMO 0.27 MAPPO."""
import argparse,csv,json,os,sys,time
import numpy as np
import torch
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from train_mappo_legacy_replay import Env,MAPPO,read_csv,native_eval,write_csv

def parse_coalitions(spec,n):
    out=[]
    for token in spec.split(";"):
        token=token.strip()
        if token in ("","empty","none"): members=()
        elif token=="grand": members=tuple(range(n))
        else:
            members=tuple(sorted({int(x[1:])-1 if x.upper().startswith("A") else int(x) for x in token.split(",")}))
        if any(i<0 or i>=n for i in members): raise ValueError("Bad coalition "+token)
        if members not in out: out.append(members)
    return out

def coalition_rollout(env,sumo,agent,members):
    obs=env.start(sumo); chosen=np.zeros(3,int); eligible_by=np.zeros(env.n_agents,int); interventions_by=np.zeros(env.n_agents,int)
    member=set(members)
    try:
        while True:
            base=env.action_mask()
            for i in range(env.n_agents): eligible_by[i]+=int(base[i,1])
            mask=base.copy()
            for i in range(env.n_agents):
                if i not in member: mask[i,1:]=False
            a,_,_,_=agent.act(obs,mask,True)
            before=env.interventions
            for x in a: chosen[int(x)]+=1
            # identify actual intervention agents from eligibility/action before apply
            for i,x in enumerate(a):
                if int(x)>0 and mask[i,int(x)]: interventions_by[i]+=1
            obs,_,done=env.step(a)
            if done: break
        s=env.summary()
        for i in range(3): s[f"chosen_a{i}"]=int(chosen[i])
        for i in range(env.n_agents):
            s[f"A{i+1}_eligible_slots"]=int(eligible_by[i]); s[f"A{i+1}_interventions"]=int(interventions_by[i])
        return s
    finally: env.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo",required=True);ap.add_argument("--sumo-tools",required=True);ap.add_argument("--scenario",required=True)
    ap.add_argument("--selection",required=True);ap.add_argument("--windows",required=True);ap.add_argument("--checkpoint",required=True)
    ap.add_argument("--outdir",required=True);ap.add_argument("--condition",default="Off-peak");ap.add_argument("--eval-s",type=int,default=300)
    ap.add_argument("--seeds",default="9001");ap.add_argument("--coalitions",default="empty;A1;A2;A1,A2;grand")
    args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
    sys.path.insert(0,os.path.abspath(args.sumo_tools));import traci
    sel=read_csv(args.selection); assert len(sel)==9
    wins={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(args.windows)}
    if args.condition not in wins: raise KeyError(args.condition)
    agent=MAPPO(9,13,3,42)
    ck=torch.load(args.checkpoint,map_location="cpu")
    agent.actor.load_state_dict(ck["actor"]);agent.critic.load_state_dict(ck["critic"]);agent.actor.eval();agent.critic.eval()
    coalitions=parse_coalitions(args.coalitions,9); rows=[]; t0=time.time()
    for seed in [int(x) for x in args.seeds.split(",") if x]:
        baseline=native_eval(traci,args.sumo,args.scenario,sel,wins[args.condition]*3600,args.eval_s,seed)
        for members in coalitions:
            if not members: s=dict(baseline); label="empty"
            else:
                env=Env(traci,args.scenario,sel,wins[args.condition]*3600,args.eval_s,seed)
                s=coalition_rollout(env,args.sumo,agent,members); label="grand" if len(members)==9 else "+".join(f"A{i+1}" for i in members)
            rows.append({"seed":seed,"condition":args.condition,"coalition":label,"coalition_size":len(members),
                         "members":"|".join(f"A{i+1}" for i in members),**s})
            print(rows[-1],flush=True)
    write_csv(os.path.join(args.outdir,"coalition_raw.csv"),rows)
    # Paired value components relative to the exact same seed/condition native baseline.
    valued=[]
    for r in rows:
        b=next(x for x in rows if x["seed"]==r["seed"] and x["coalition"]=="empty")
        q0=max(float(b["mean_halting_vehicles"]),1e-9);w0=max(float(b["mean_waiting_time_lane_sum_s"]),1e-9)
        c0=max(float(b["CO2_kg_selected_approaches"]),1e-9);a0=max(float(b["arrived_vehicles_global"]),1.0)
        dq=(q0-float(r["mean_halting_vehicles"]))/q0
        dw=(w0-float(r["mean_waiting_time_lane_sum_s"]))/w0
        dc=(c0-float(r["CO2_kg_selected_approaches"]))/c0
        da=(float(r["arrived_vehicles_global"])-a0)/a0
        # Throughput is a signed component, preventing queue gains via suppressed arrivals.
        v=.35*dq+.30*dw+.20*dc+.15*da
        valued.append({**r,"queue_gain":dq,"waiting_gain":dw,"co2_gain":dc,"arrival_gain":da,"v_balanced":v})
    write_csv(os.path.join(args.outdir,"coalition_values.csv"),valued)
    with open(os.path.join(args.outdir,"metadata.json"),"w") as f:
        json.dump({"saved_state_used":False,"initialization":"full-history deterministic replay from t=0",
                   "checkpoint":os.path.basename(args.checkpoint),"condition":args.condition,"seeds":args.seeds,
                   "coalitions":[list(x) for x in coalitions],"utility_weights":{"queue":.35,"waiting":.30,"co2":.20,"arrivals":.15},
                   "wall_time_s":time.time()-t0},f,indent=2)
if __name__=="__main__":main()
