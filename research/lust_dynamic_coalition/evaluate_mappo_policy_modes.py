#!/usr/bin/env python3
"""Evaluate a trained guarded-residual MAPPO under multiple deployment rules.

This is a validation-only deployment-policy sweep. Threshold selection is made
on this validation run; any selected threshold must be frozen before held-out
multi-seed testing.
"""
import argparse,csv,json,os,sys
import numpy as np
import torch

sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from train_mappo_legacy_replay import Env,MAPPO,read_csv

def load_agent(path):
    obj=torch.load(path,map_location="cpu")
    agent=MAPPO(9,13,3,42)
    agent.actor.load_state_dict(obj["actor"]);agent.critic.load_state_dict(obj["critic"])
    agent.actor.eval();agent.critic.eval()
    return agent,obj.get("meta",{})

def probs(agent,obs,mask):
    x=torch.tensor(obs,dtype=torch.float32);m=torch.tensor(mask,dtype=torch.bool)
    with torch.no_grad():
        logits=agent.actor(x).masked_fill(~m,-1e9)
        return torch.softmax(logits,dim=-1).cpu().numpy()

def choose(agent,obs,mask,mode,tau,policy_seed):
    p=probs(agent,obs,mask)
    if mode=="argmax":
        a=np.argmax(p,axis=1)
    elif mode=="threshold":
        a=np.zeros(len(p),dtype=int)
        for i in range(len(p)):
            if mask[i,1] and (p[i,1]+p[i,2])>=tau:
                a[i]=1 if p[i,1]>=p[i,2] else 2
    elif mode=="stochastic":
        rng=np.random.default_rng(policy_seed)
        a=np.asarray([rng.choice(3,p=row/row.sum()) for row in p],dtype=int)
    else: raise ValueError(mode)
    return a,p

def run_native(traci,sumo,scenario,sel,begin_s,horizon,traffic_seed,state):
    env=Env(traci,scenario,sel,begin_s,horizon,traffic_seed,load_state=state)
    env.start(sumo)
    try:
        while env.tc.time_s()<env.end and env.tc.min_expected()>0:
            arrived=0.;co2=0.
            for _ in range(env.decision_dt):
                if env.tc.min_expected()<=0:break
                env.tc.step();arrived+=env.tc.arrived_number()
                for tl in env.tls:co2+=env.lane_stats(tl)["co2"]
            s=[env.lane_stats(t) for t in env.tls]
            env.metrics["halt"]+=sum(x["halt"] for x in s)
            env.metrics["waiting"]+=sum(x["waiting"] for x in s)
            env.metrics["arrived"]+=arrived;env.metrics["co2_mg"]+=co2;env.steps+=1
        return env.summary()
    finally:env.close()

def run_policy(traci,sumo,scenario,sel,begin_s,horizon,traffic_seed,state,agent,mode,tau,policy_seed):
    env=Env(traci,scenario,sel,begin_s,horizon,traffic_seed,load_state=state)
    obs=env.start(sumo);psum=np.zeros(3);pn=0;chosen=np.zeros(3,int)
    try:
        while True:
            mask=env.action_mask();a,p=choose(agent,obs,mask,mode,tau,policy_seed+env.steps)
            psum+=p.sum(0);pn+=len(p)
            for x in a:chosen[int(x)]+=1
            obs,r,done=env.step(a)
            if done:break
        s=env.summary()
        for i in range(3):s[f"prob_a{i}"]=float(psum[i]/max(pn,1));s[f"chosen_a{i}"]=int(chosen[i])
        return s
    finally:env.close()

def write(path,rows):
    fields=[];seen=set()
    for r in rows:
        for k in r:
            if k not in seen:seen.add(k);fields.append(k)
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo",required=True);ap.add_argument("--sumo-tools",required=True);ap.add_argument("--scenario",required=True)
    ap.add_argument("--selection",required=True);ap.add_argument("--windows",required=True);ap.add_argument("--states-dir",required=True)
    ap.add_argument("--model",required=True);ap.add_argument("--outdir",required=True)
    ap.add_argument("--horizon",type=int,default=1800);ap.add_argument("--traffic-seed",type=int,default=42)
    ap.add_argument("--thresholds",default="0.25,0.35,0.45,0.55");ap.add_argument("--policy-seed",type=int,default=7301)
    args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
    sys.path.insert(0,os.path.abspath(args.sumo_tools));import traci
    sel=read_csv(args.selection);wins={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(args.windows)}
    conds=[c for c in ("Off-peak","AM","Lunch","PM") if c in wins]
    agent,meta=load_agent(args.model)
    rows=[]
    for cond in conds:
        state=os.path.join(os.path.abspath(args.states_dir),f"state_{cond.replace('-','_')}.sbx")
        if not os.path.isfile(state):raise FileNotFoundError(state)
        base=run_native(traci,args.sumo,args.scenario,sel,wins[cond]*3600,args.horizon,args.traffic_seed,state)
        rows.append({"deployment":"Actuated","condition":cond,"tau":"","traffic_seed":args.traffic_seed,**base})
        ar=run_policy(traci,args.sumo,args.scenario,sel,wins[cond]*3600,args.horizon,args.traffic_seed,state,agent,"argmax",0,args.policy_seed)
        rows.append({"deployment":"MAPPO-argmax","condition":cond,"tau":"","traffic_seed":args.traffic_seed,**ar})
        st=run_policy(traci,args.sumo,args.scenario,sel,wins[cond]*3600,args.horizon,args.traffic_seed,state,agent,"stochastic",0,args.policy_seed)
        rows.append({"deployment":"MAPPO-stochastic","condition":cond,"tau":"","traffic_seed":args.traffic_seed,**st})
        for tau in [float(x) for x in args.thresholds.split(",") if x.strip()]:
            s=run_policy(traci,args.sumo,args.scenario,sel,wins[cond]*3600,args.horizon,args.traffic_seed,state,agent,"threshold",tau,args.policy_seed)
            rows.append({"deployment":"MAPPO-threshold","condition":cond,"tau":tau,"traffic_seed":args.traffic_seed,**s})
        print(cond,flush=True)
    write(os.path.join(args.outdir,"policy_mode_validation.csv"),rows)

    scored=[]
    for r in rows:
        if r["deployment"]=="Actuated":continue
        b=next(x for x in rows if x["deployment"]=="Actuated" and x["condition"]==r["condition"])
        q=(float(b["mean_halting_vehicles"])-float(r["mean_halting_vehicles"]))/max(abs(float(b["mean_halting_vehicles"])),1e-9)
        w=(float(b["mean_waiting_time_lane_sum_s"])-float(r["mean_waiting_time_lane_sum_s"]))/max(abs(float(b["mean_waiting_time_lane_sum_s"])),1e-9)
        c=(float(b["CO2_kg_selected_approaches"])-float(r["CO2_kg_selected_approaches"]))/max(abs(float(b["CO2_kg_selected_approaches"])),1e-9)
        th=(float(r["arrived_vehicles_global"])-float(b["arrived_vehicles_global"]))/max(abs(float(b["arrived_vehicles_global"])),1e-9)
        score=.35*q+.35*w+.15*c+.15*th
        scored.append({"deployment":r["deployment"],"tau":r["tau"],"condition":r["condition"],
                       "queue_rel_improvement":q,"waiting_rel_improvement":w,"co2_rel_improvement":c,
                       "arrivals_rel_improvement":th,"validation_score":score,
                       "interventions":r.get("interventions",0),"eligible_rate":r.get("mask_eligible_rate",0)})
    write(os.path.join(args.outdir,"policy_mode_scores.csv"),scored)
    groups={}
    for r in scored:
        key=(r["deployment"],str(r["tau"]))
        groups.setdefault(key,[]).append(r)
    agg=[]
    for (dep,tau),rr in groups.items():
        agg.append({"deployment":dep,"tau":tau,"conditions":len(rr),
                    "mean_validation_score":float(np.mean([x["validation_score"] for x in rr])),
                    "mean_queue_rel_improvement":float(np.mean([x["queue_rel_improvement"] for x in rr])),
                    "mean_waiting_rel_improvement":float(np.mean([x["waiting_rel_improvement"] for x in rr])),
                    "mean_co2_rel_improvement":float(np.mean([x["co2_rel_improvement"] for x in rr])),
                    "mean_arrivals_rel_improvement":float(np.mean([x["arrivals_rel_improvement"] for x in rr])),
                    "total_interventions":int(sum(int(float(x["interventions"])) for x in rr))})
    agg=sorted(agg,key=lambda x:x["mean_validation_score"],reverse=True)
    write(os.path.join(args.outdir,"policy_mode_aggregate.csv"),agg)
    with open(os.path.join(args.outdir,"validation_metadata.json"),"w") as f:
        json.dump({"policy_model_meta":meta,"traffic_seed":args.traffic_seed,"policy_seed":args.policy_seed,
                   "horizon_s":args.horizon,"thresholds":args.thresholds,
                   "selection_rule":"validation-only; freeze chosen deployment rule before held-out multi-seed tests",
                   "ranking":agg},f,indent=2)
    print(json.dumps(agg,indent=2))

if __name__=="__main__":
    main()
