#!/usr/bin/env python3
"""Frozen-checkpoint stakeholder coalition evaluation on legacy LuST/SUMO 0.27."""
import argparse,csv,json,os,sys,random
import numpy as np, torch
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from train_mappo_legacy_replay import Env,read_csv,native_eval,write_csv
from train_stakeholder_mappo_legacy import StakeholderMAPPO,run
from stakeholder_observation import feasible_coalitions

def main():
    ap=argparse.ArgumentParser()
    for x in ("sumo","sumo-tools","scenario","selection","windows","checkpoint","outdir"): ap.add_argument("--"+x,required=True)
    ap.add_argument("--condition",choices=["Off-peak","AM","Lunch","PM"],required=True)
    ap.add_argument("--eval-s",type=int,default=900)
    ap.add_argument("--seeds",default="9001,9002,9003,9004,9005")
    ap.add_argument("--deploy-margin",type=float,default=0.05)
    args=ap.parse_args(); os.makedirs(args.outdir,exist_ok=True)
    sys.path.insert(0,os.path.abspath(args.sumo_tools)); import traci
    sel=read_csv(args.selection); wins={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(args.windows)}
    seeds=[int(x) for x in args.seeds.split(",") if x.strip()]
    ck=torch.load(args.checkpoint,map_location="cpu")
    meta=ck.get("meta",{})
    assert int(meta.get("obs_dim",-1))==14
    assert abs(float(meta.get("deterministic_deploy_margin",-1))-args.deploy_margin)<1e-12
    agent=StakeholderMAPPO(9,14,3,42); agent.actor.load_state_dict(ck["actor"]); agent.critic.load_state_dict(ck["critic"])
    agent.actor.eval(); agent.critic.eval()
    coalitions=feasible_coalitions(); assert len(coalitions)==14
    begin=wins[args.condition]*3600
    native={}
    for seed in seeds:
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        native[seed]=native_eval(traci,args.sumo,args.scenario,sel,begin,args.eval_s,seed)
    rows=[]
    for coalition in coalitions:
        cname="+".join(coalition)
        for seed in seeds:
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            env=Env(traci,args.scenario,sel,begin,args.eval_s,seed)
            _,s=run(env,args.sumo,agent,coalition,False,deploy_margin=args.deploy_margin)
            n=native[seed]
            row={"condition":args.condition,"coalition":cname,"seed":seed,**s}
            for k in ("mean_halting_vehicles","mean_waiting_time_lane_sum_s","arrived_vehicles","CO2_kg_selected_approaches"):
                if k in s and k in n:
                    row["native_"+k]=n[k]
                    den=float(n[k]); row["delta_pct_"+k]=(float(s[k])-den)/den*100.0 if abs(den)>1e-12 else float("nan")
            eligible=float(s.get("mask_eligible_slots",0))
            row["eligible_intervention_fraction"]=float(s.get("interventions",0))/max(eligible,1.0)
            rows.append(row)
    assert len(rows)==14*len(seeds)
    assert len({(r["coalition"],r["seed"]) for r in rows})==len(rows)
    finite=("mean_halting_vehicles","mean_waiting_time_lane_sum_s","CO2_kg_selected_approaches")
    assert all(np.isfinite(float(r[k])) for r in rows for k in finite)
    write_csv(os.path.join(args.outdir,"coalition_results.csv"),rows)
    write_csv(os.path.join(args.outdir,"native_baselines.csv"),[{"condition":args.condition,"seed":s,**native[s]} for s in seeds])
    prov={"condition":args.condition,"seeds":seeds,"coalitions":14,"evaluations":len(rows),"native_runs":len(seeds),
          "eval_s":args.eval_s,"deploy_margin":args.deploy_margin,"checkpoint_meta":meta,
          "saved_state_used":False,"crn_paired":True}
    json.dump(prov,open(os.path.join(args.outdir,"provenance.json"),"w"),indent=2)
    print(json.dumps(prov,indent=2))
if __name__=="__main__": main()
