#!/usr/bin/env python3
"""Calibrate native-reference deployment margin for the frozen grand-coalition policy.\nThe hold-out seed is never used by the margin-selection rule.\n"""
import argparse,csv,json,os,sys,random
import numpy as np,torch
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from train_mappo_legacy_replay import Env,read_csv,native_eval,write_csv
from train_stakeholder_mappo_legacy import StakeholderMAPPO,run
from stakeholder_observation import PLAYERS

def main():
 ap=argparse.ArgumentParser()
 for x in ("sumo","sumo-tools","scenario","selection","windows","checkpoint","outdir"):ap.add_argument("--"+x,required=True)
 ap.add_argument("--margins",default="0.05,0.10,0.15,0.20")
 ap.add_argument("--cal-seeds",default="9001,9002,9003,9004")
 ap.add_argument("--holdout-seed",type=int,default=9005)
 ap.add_argument("--eval-s",type=int,default=900);args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
 sys.path.insert(0,os.path.abspath(args.sumo_tools));import traci
 sel=read_csv(args.selection);wins={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(args.windows)}
 ck=torch.load(args.checkpoint,map_location="cpu");agent=StakeholderMAPPO(9,14,3,42)
 agent.actor.load_state_dict(ck["actor"]);agent.critic.load_state_dict(ck["critic"]);agent.actor.eval();agent.critic.eval()
 margins=[float(x) for x in args.margins.split(",")];cal=[int(x) for x in args.cal_seeds.split(",")];begin=wins["AM"]*3600
 seeds=cal+[args.holdout_seed];native={}
 for seed in seeds:native[seed]=native_eval(traci,args.sumo,args.scenario,sel,begin,args.eval_s,seed)
 rows=[]
 for m in margins:
  for seed in seeds:
   random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
   _,s=run(Env(traci,args.scenario,sel,begin,args.eval_s,seed),args.sumo,agent,tuple(PLAYERS),False,deploy_margin=m)
   n=native[seed];e=float(s.get("mask_eligible_slots",0));r={"margin":m,"seed":seed,"split":"holdout" if seed==args.holdout_seed else "calibration",
   "intervention_fraction":float(s.get("interventions",0))/max(e,1.0),**s}
   for k in ("mean_halting_vehicles","mean_waiting_time_lane_sum_s","CO2_kg_selected_approaches","arrived_vehicles"):
    if k in s and k in n:
     den=float(n[k]);r["delta_pct_"+k]=(float(s[k])-den)/den*100 if abs(den)>1e-12 else float("nan")
   rows.append(r)
 write_csv(os.path.join(args.outdir,"margin_grid.csv"),rows)
 # Predeclared selection rule: among calibration margins with mean intervention <=0.80,
 # minimize equal-weight mean of halt/wait/CO2 percent deltas; ties choose larger margin.
 scores=[]
 for m in margins:
  rr=[r for r in rows if r["margin"]==m and r["split"]=="calibration"]
  inter=float(np.mean([r["intervention_fraction"] for r in rr]))
  score=float(np.mean([[r["delta_pct_mean_halting_vehicles"],r["delta_pct_mean_waiting_time_lane_sum_s"],r["delta_pct_CO2_kg_selected_approaches"]] for r in rr]))
  scores.append({"margin":m,"mean_intervention_fraction":inter,"traffic_score":score,"eligible":inter<=0.80})
 elig=[x for x in scores if x["eligible"]];assert elig,"No margin satisfies predeclared <=0.80 intervention gate"
 chosen=sorted(elig,key=lambda x:(x["traffic_score"],-x["margin"]))[0]["margin"]
 hold=[r for r in rows if r["margin"]==chosen and r["split"]=="holdout"][0]
 json.dump({"selection_rule":"calibration intervention<=0.80 then minimize equal-weight mean percent delta of halting/waiting/CO2; holdout excluded from selection",
 "margins":margins,"calibration_seeds":cal,"holdout_seed":args.holdout_seed,"scores":scores,"chosen_margin":chosen,"holdout":hold},open(os.path.join(args.outdir,"calibration.json"),"w"),indent=2)
 print(json.dumps({"scores":scores,"chosen_margin":chosen,"holdout":hold},indent=2))
if __name__=="__main__":main()
