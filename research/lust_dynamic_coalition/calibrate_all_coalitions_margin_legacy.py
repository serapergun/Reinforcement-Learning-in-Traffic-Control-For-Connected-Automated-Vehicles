#!/usr/bin/env python3
"""Frozen policy: all-coalition AM margin calibration with disjoint holdout seeds.
GitHub Actions executes the complete margin grid and retains failures as diagnostics.
"""
import argparse,json,os,random,sys
import numpy as np,torch
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from train_mappo_legacy_replay import Env,read_csv,native_eval,write_csv
from train_stakeholder_mappo_legacy import StakeholderMAPPO,run
from stakeholder_observation import feasible_coalitions

def main():
 p=argparse.ArgumentParser()
 for a in ("sumo","sumo-tools","scenario","selection","windows","checkpoint","outdir"):p.add_argument("--"+a,required=True)
 p.add_argument("--margins",default="0.10,0.15,0.20,0.25,0.30")
 p.add_argument("--cal-seeds",default="9101,9102")
 p.add_argument("--holdout-seeds",default="9201,9202")
 p.add_argument("--eval-s",type=int,default=900)
 a=p.parse_args();os.makedirs(a.outdir,exist_ok=True)
 sys.path.insert(0,os.path.abspath(a.sumo_tools));import traci
 cal=[int(s) for s in a.cal_seeds.split(",")];hold=[int(s) for s in a.holdout_seeds.split(",")]
 assert cal and hold and not set(cal)&set(hold) and not (set(cal)|set(hold))&set(range(9001,9006))
 margins=[float(s) for s in a.margins.split(",")]
 assert len(margins)==len(set(margins)) and all(0<=m<=1 for m in margins)
 sel=read_csv(a.selection);windows={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(a.windows)}
 ck=torch.load(a.checkpoint,map_location="cpu");agent=StakeholderMAPPO(9,14,3,42)
 agent.actor.load_state_dict(ck["actor"]);agent.critic.load_state_dict(ck["critic"])
 agent.actor.eval();agent.critic.eval()
 coalitions=feasible_coalitions();assert len(coalitions)==14
 begin=windows["AM"]*3600
 native={}
 for seed in cal+hold:
  random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
  native[seed]=native_eval(traci,a.sumo,a.scenario,sel,begin,a.eval_s,seed)
 rows=[]
 def evaluate(coalition,seed,margin,split):
  random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
  _,s=run(Env(traci,a.scenario,sel,begin,a.eval_s,seed),a.sumo,agent,coalition,False,deploy_margin=margin)
  n=native[seed];r={"coalition":"+".join(coalition),"seed":seed,"margin":margin,"split":split,
   "intervention_fraction":float(s.get("interventions",0))/max(float(s.get("mask_eligible_slots",0)),1.0)}
  for k in ("mean_halting_vehicles","mean_waiting_time_lane_sum_s","CO2_kg_selected_approaches"):
   r["delta_pct_"+k]=100*(float(s[k])-float(n[k]))/float(n[k]) if abs(float(n[k]))>1e-12 else float("nan")
  return r
 scores=[];selected={}
 for coalition in coalitions:
  name="+".join(coalition)
  rr=[evaluate(coalition,seed,m,"calibration") for m in margins for seed in cal]
  rows.extend(rr)
  cand=[]
  for m in margins:
   subset=[r for r in rr if r["margin"]==m]
   inter=float(np.mean([r["intervention_fraction"] for r in subset]))
   score=float(np.mean([[r["delta_pct_mean_halting_vehicles"],r["delta_pct_mean_waiting_time_lane_sum_s"],r["delta_pct_CO2_kg_selected_approaches"]] for r in subset]))
   cand.append({"coalition":name,"margin":m,"intervention":inter,"traffic_score":score,"eligible":bool(inter<=0.80 and np.isfinite(score))})
  scores.extend(cand)
  eligible=[r for r in cand if r["eligible"]]
  selected[name]=sorted(eligible,key=lambda r:(r["traffic_score"],-r["margin"]))[0]["margin"] if eligible else None
  if selected[name] is not None:
   rows.extend(evaluate(coalition,seed,selected[name],"holdout") for seed in hold)
 write_csv(os.path.join(a.outdir,"coalition_margin_grid.csv"),rows)
 write_csv(os.path.join(a.outdir,"coalition_margin_scores.csv"),scores)
 report={"calibration_seeds":cal,"holdout_seeds":hold,"margins":margins,"selected":selected,
  "rule":"calibration intervention <=0.80; minimize mean of three percent deltas; holdout never used in selection",
  "holdout_gate":"all selected coalitions must have intervention <=0.80 on every holdout seed and no positive mean of halting/waiting/CO2 percentage deltas"}
 gate={}
 for name,m in selected.items():
  h=[r for r in rows if r["coalition"]==name and r["split"]=="holdout"]
  gate[name]=bool(m is not None and len(h)==len(hold) and all(r["intervention_fraction"]<=0.80 for r in h) and
   all(float(np.mean([r["delta_pct_"+k] for r in h]))<=0 for k in ("mean_halting_vehicles","mean_waiting_time_lane_sum_s","CO2_kg_selected_approaches")))
 report["holdout_pass"]=gate;report["all_pass"]=all(gate.values())
 with open(os.path.join(a.outdir,"coalition_margin_report.json"),"w") as f:json.dump(report,f,indent=2)
 assert len(scores)==14*len(margins)
 print(json.dumps(report,indent=2),flush=True)
if __name__=="__main__":main()
