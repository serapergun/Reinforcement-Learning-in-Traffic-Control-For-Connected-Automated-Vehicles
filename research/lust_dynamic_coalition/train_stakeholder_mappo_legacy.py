#!/usr/bin/env python3
"""Coalition-mask-randomized stakeholder MAPPO on validated SUMO 0.27 residual control."""
import argparse,csv,json,os,random,sys,time
import numpy as np, torch
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from train_mappo_legacy_replay import Env,MAPPO,read_csv,write_csv
from stakeholder_observation import StakeholderObservation,feasible_coalitions,PLAYERS

def run(env,sumo,agent,coalition,train):
    raw=env.start(sumo); adapter=StakeholderObservation(env,coalition,env.seed); obs=adapter.observe(); traj=[]
    try:
        while True:
            mask=env.action_mask(); a,lp,v,_=agent.act(obs,mask,not train)
            _,r,done=env.step(a); nxt=adapter.observe()
            if train: traj.append({"obs":obs,"act":a,"lp":lp,"v":v,"r":r,"done":done,"mask":mask})
            obs=nxt
            if done: break
        return traj,env.summary()
    finally: env.close()

def main():
    ap=argparse.ArgumentParser()
    for x in ("sumo","sumo-tools","scenario","selection","windows","outdir"):ap.add_argument("--"+x,required=True)
    ap.add_argument("--episodes",type=int,default=28);ap.add_argument("--train-s",type=int,default=600)
    ap.add_argument("--eval-s",type=int,default=900);ap.add_argument("--seed",type=int,default=42)
    ap.add_argument("--eval-seed",type=int,default=9001);args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
    sys.path.insert(0,os.path.abspath(args.sumo_tools));import traci
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    sel=read_csv(args.selection);wins={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(args.windows)}
    conds=[c for c in ("Off-peak","AM","Lunch","PM") if c in wins]; cs=feasible_coalitions()
    agent=MAPPO(9,12,3,args.seed);hist=[]
    for ep in range(args.episodes):
        cond=conds[ep%len(conds)]; coalition=cs[ep%len(cs)]; seed=1100+ep
        env=Env(traci,args.scenario,sel,wins[cond]*3600,args.train_s,seed)
        traj,s=run(env,args.sumo,agent,coalition,True); up=agent.update(traj)
        row={"episode":ep+1,"condition":cond,"coalition":"+".join(coalition),"seed":seed,**s,**up};hist.append(row);print(row,flush=True)
    write_csv(os.path.join(args.outdir,"training_history.csv"),hist)
    torch.save({"actor":agent.actor.state_dict(),"critic":agent.critic.state_dict(),
      "meta":{"obs_dim":12,"players":PLAYERS,"training":"coalition-mask randomized","feasible_coalitions":14,
      "controller":"validated guarded residual native/+3s/+6s","saved_state_used":False}},os.path.join(args.outdir,"stakeholder_mappo.pt"))
    # Short real-SUMO regression: grand coalition must execute and produce finite metrics/interventions.
    coalition=tuple(PLAYERS);env=Env(traci,args.scenario,sel,wins["AM"]*3600,args.eval_s,args.eval_seed)
    _,s=run(env,args.sumo,agent,coalition,False)
    assert all(np.isfinite(float(s[k])) for k in ("mean_halting_vehicles","mean_waiting_time_lane_sum_s","CO2_kg_selected_approaches"))
    assert s["decision_steps"]>0
    json.dump({"condition":"AM","seed":args.eval_seed,"coalition":coalition,**s},open(os.path.join(args.outdir,"smoke.json"),"w"),indent=2)
if __name__=="__main__":main()
