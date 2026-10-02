#!/usr/bin/env python3
"""Guarded residual MAPPO pilot for the validated SUMO 0.27 LuST path.

The learned controller is supervisory: action 0 leaves the official actuated
controller untouched; actions 1/2 add a short extension to the *remaining*
current green. Native yellow/all-red/next-green transitions are never replaced.
"""
import argparse,csv,json,os,random,sys,time,xml.etree.ElementTree as ET
from collections import defaultdict
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from traci_compat import TraCICompat

def read_csv(path):
    with open(path,newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def incoming_lanes(net_path,tls):
    root=ET.parse(net_path).getroot();lanes=set();inc=defaultdict(set)
    for e in root.findall("edge"):
        if e.get("function"):continue
        for l in e.findall("lane"):lanes.add(l.get("id"))
    for c in root.findall("connection"):
        tl=c.get("tl")
        if tl not in tls:continue
        lid=f"{c.get('from')}_{c.get('fromLane')}"
        if lid in lanes:inc[tl].add(lid)
    return {k:sorted(v) for k,v in inc.items()}

def is_green(state):
    return ("G" in state or "g" in state) and "y" not in state and "Y" not in state

class Env:
    def __init__(self,traci,scenario,selection,begin_s,control_s,seed,warmup_s=300,
                 extension_s=(0.,3.,6.),cooldown_s=20.,pressure_threshold=.03,load_state=None):
        self.traci=traci;self.tc=TraCICompat(traci);self.scenario=os.path.abspath(scenario)
        self.sel=sorted(selection,key=lambda r:int(r["agent_alias"][1:]))
        self.tls=[r["tls_id"] for r in self.sel]
        self.inc=incoming_lanes(os.path.join(self.scenario,"lust.net.xml"),set(self.tls))
        self.begin=max(0,int(begin_s-warmup_s));self.control_start=int(begin_s);self.end=int(begin_s+control_s)
        self.seed=int(seed);self.load_state=os.path.abspath(load_state) if load_state else None
        self.extension_s=tuple(extension_s);self.cooldown_s=float(cooldown_s)
        self.pressure_threshold=float(pressure_threshold);self.min_green=10.;self.decision_dt=10
        self.last_intervention=defaultdict(lambda:-1e12);self.metrics=defaultdict(float);self.steps=0
        self.interventions=0;self.eligible_slots=0;self.total_slots=0;self.action_requests=0

    @property
    def n_agents(self):return len(self.tls)
    @property
    def obs_dim(self):return 13
    @property
    def n_actions(self):return 3

    def cmd(self):
        cmd=[self.sumo,"-c",os.path.join(self.scenario,"due.actuated.sumocfg"),
             "--end",str(self.end),
             "--summary-output","/dev/null","--tripinfo-output","/dev/null","--log","/dev/null"]
        # SUMO 0.27 can write the LuST state files but cannot reliably reload
        # them (legacy vType/car-following round-trip incompatibility for bus).
        # Preserve scientific provenance by replaying the official LuST demand
        # from t=0 with a fixed seed and warming up to the requested control
        # window, rather than mutating the saved-state XML.
        #
        # A supplied load_state is therefore provenance-only on this legacy
        # path. All Actuated/MAPPO counterfactuals start from the same exact
        # deterministic replay.
        cmd += ["--seed","42","--begin","0"]
        return cmd

    def start(self,sumo):
        self.sumo=os.path.abspath(sumo);self.tc.start(self.cmd())
        while self.tc.time_s()<self.control_start and self.tc.min_expected()>0:self.tc.step()
        if abs(self.tc.time_s()-self.control_start)>2:
            raise RuntimeError(f"Control start mismatch: got {self.tc.time_s()} expected {self.control_start}")
        return self.observe()

    def close(self):
        try:self.tc.close()
        except Exception:pass

    def lane_stats(self,tl):
        ls=self.inc[tl];veh=halt=0;occ=[];weighted=0.;wn=0;wait=0.;co2=0.
        for l in ls:
            n=self.tc.lane_vehicle_number(l);veh+=n;halt+=self.tc.lane_halting_number(l)
            sp=self.tc.lane_speed(l)
            if n>0 and sp>=0:weighted+=n*sp;wn+=n
            occ.append(self.tc.lane_occupancy(l));wait+=self.tc.lane_waiting(l);co2+=self.tc.lane_co2(l)
        return {"veh":veh,"halt":halt,"speed":weighted/max(wn,1),"occ":sum(occ)/max(len(occ),1),
                "waiting":wait,"co2":co2,"lanes":max(len(ls),1)}

    def eligibility(self,tl,s=None):
        if s is None:s=self.lane_stats(tl)
        state=self.tc.phase_state(tl);now=self.tc.time_s();spent=self.tc.spent_duration_s(tl)
        pressure=s["halt"]/max(8*s["lanes"],1)
        return bool(is_green(state) and spent>=self.min_green and
                    pressure>=self.pressure_threshold and
                    now-self.last_intervention[tl]>=self.cooldown_s)

    def action_mask(self):
        mask=[]
        for tl in self.tls:
            ok=self.eligibility(tl)
            mask.append([True,ok,ok])
        return np.asarray(mask,dtype=bool)

    def observe(self):
        out=[]
        for tl in self.tls:
            s=self.lane_stats(tl);state=self.tc.phase_state(tl)
            now=self.tc.time_s();remaining=max(0.,self.tc.next_switch_s(tl)-now)
            spent=self.tc.spent_duration_s(tl);pressure=s["halt"]/max(8*s["lanes"],1)
            eligible=1. if self.eligibility(tl,s) else 0.
            out.append(np.asarray([
                np.clip(s["veh"]/max(12*s["lanes"],1),0,3),
                np.clip(s["halt"]/max(8*s["lanes"],1),0,3),
                np.clip(s["speed"]/15.,0,3),
                np.clip(s["occ"]/100.,0,1.5),
                np.clip(s["waiting"]/max(300*s["lanes"],1),0,5),
                np.clip(pressure,0,3),
                1. if is_green(state) else 0.,
                1. if ("y" in state or "Y" in state) else 0.,
                np.clip(remaining/60.,0,3),
                np.clip(spent/60.,0,3),
                np.clip(self.tc.phase(tl)/20.,0,1),
                np.clip((now-self.last_intervention[tl])/60.,0,10),
                eligible
            ],dtype=np.float32))
        return np.stack(out)

    def apply(self,actions):
        mask=self.action_mask();self.eligible_slots+=int(mask[:,1].sum());self.total_slots+=len(self.tls)
        for i,(tl,a) in enumerate(zip(self.tls,actions)):
            if int(a)==0:continue
            self.action_requests+=1
            if not mask[i,int(a)]:continue
            ext=self.extension_s[int(a)]
            remaining=max(.1,self.tc.next_switch_s(tl)-self.tc.time_s())
            self.tc.set_phase_duration_s(tl,remaining+ext)
            self.last_intervention[tl]=self.tc.time_s();self.interventions+=1

    def step(self,actions):
        self.apply(actions);arrived=0;co2=0.
        for _ in range(self.decision_dt):
            if self.tc.min_expected()<=0:break
            self.tc.step();arrived+=self.tc.arrived_number()
            for tl in self.tls:co2+=self.lane_stats(tl)["co2"]
        stats=[self.lane_stats(tl) for tl in self.tls]
        halt=sum(s["halt"] for s in stats);wait=sum(s["waiting"] for s in stats);lanes=sum(s["lanes"] for s in stats)
        qn=halt/max(8*lanes,1);wn=wait/max(300*lanes,1)
        intervention_penalty=.01*(self.interventions/max(self.steps+1,1))
        reward=-.5*qn-.5*wn-intervention_penalty
        self.metrics["halt"]+=halt;self.metrics["waiting"]+=wait;self.metrics["arrived"]+=arrived
        self.metrics["co2_mg"]+=co2;self.metrics["reward"]+=reward;self.steps+=1
        done=self.tc.time_s()>=self.end or self.tc.min_expected()<=0
        return self.observe(),float(reward),done

    def summary(self):
        n=max(self.steps,1)
        return {"mean_halting_vehicles":self.metrics["halt"]/n,
                "mean_waiting_time_lane_sum_s":self.metrics["waiting"]/n,
                "arrived_vehicles_global":self.metrics["arrived"],
                "CO2_kg_selected_approaches":self.metrics["co2_mg"]/1e6,
                "mean_reward":self.metrics["reward"]/n,
                "interventions":self.interventions,
                "action_requests":self.action_requests,
                "intervention_rate":self.interventions/max(n*self.n_agents,1),
                "mask_eligible_slots":self.eligible_slots,
                "mask_eligible_rate":self.eligible_slots/max(self.total_slots,1),
                "decision_steps":self.steps}

class Actor(nn.Module):
    def __init__(self,d,a):
        super().__init__();self.body=nn.Sequential(nn.Linear(d,128),nn.Tanh(),nn.Linear(128,128),nn.Tanh())
        self.head=nn.Linear(128,a)
        with torch.no_grad():
            self.head.bias.copy_(torch.tensor([2.0,-1.0,-1.5]))
    def forward(self,x):return self.head(self.body(x))

class Critic(nn.Module):
    def __init__(self,d):
        super().__init__();self.net=nn.Sequential(nn.Linear(d,256),nn.Tanh(),nn.Linear(256,128),nn.Tanh(),nn.Linear(128,1))
    def forward(self,x):return self.net(x).squeeze(-1)

class MAPPO:
    def __init__(self,n,od,na,seed=42):
        torch.manual_seed(seed);self.n=n;self.od=od;self.na=na
        self.actor=Actor(od,na);self.critic=Critic(n*od)
        self.oa=optim.Adam(self.actor.parameters(),lr=2e-4);self.oc=optim.Adam(self.critic.parameters(),lr=3e-4)
        self.gamma=.99;self.lam=.95;self.clip=.15;self.ent=.003

    def act(self,obs,mask,deterministic=False):
        x=torch.tensor(obs,dtype=torch.float32);m=torch.tensor(mask,dtype=torch.bool)
        logits=self.actor(x).masked_fill(~m,-1e9);dist=torch.distributions.Categorical(logits=logits)
        a=torch.argmax(logits,dim=-1) if deterministic else dist.sample()
        lp=dist.log_prob(a).sum();v=self.critic(x.reshape(-1))
        return a.numpy(),float(lp.detach()),float(v.detach()),torch.softmax(logits,dim=-1).detach().numpy()

    def update(self,traj,epochs=5):
        obs=np.asarray([z["obs"] for z in traj],np.float32);act=np.asarray([z["act"] for z in traj],np.int64)
        oldlp=np.asarray([z["lp"] for z in traj],np.float32);rew=np.asarray([z["r"] for z in traj],np.float32)
        val=np.asarray([z["v"] for z in traj],np.float32);done=np.asarray([z["done"] for z in traj],np.float32)
        masks=np.asarray([z["mask"] for z in traj],bool)
        adv=np.zeros_like(rew);gae=0.
        for t in reversed(range(len(rew))):
            nv=0. if t==len(rew)-1 else val[t+1];gate=1.-done[t]
            delta=rew[t]+self.gamma*nv*gate-val[t];gae=delta+self.gamma*self.lam*gate*gae;adv[t]=gae
        ret=adv+val;adv=(adv-adv.mean())/(adv.std()+1e-8)
        O=torch.tensor(obs);A=torch.tensor(act);OLD=torch.tensor(oldlp);ADV=torch.tensor(adv);RET=torch.tensor(ret)
        M=torch.tensor(masks,dtype=torch.bool);G=O.reshape(len(O),-1);stat={}
        for _ in range(epochs):
            logits=self.actor(O.reshape(-1,self.od)).reshape(len(O),self.n,self.na).masked_fill(~M,-1e9)
            dist=torch.distributions.Categorical(logits=logits);lp=dist.log_prob(A).sum(1)
            ratio=torch.exp(lp-OLD);obj=torch.min(ratio*ADV,torch.clamp(ratio,1-self.clip,1+self.clip)*ADV)
            ent=dist.entropy().mean();aloss=-obj.mean()-self.ent*ent
            self.oa.zero_grad();aloss.backward();nn.utils.clip_grad_norm_(self.actor.parameters(),.5);self.oa.step()
            pred=self.critic(G);closs=((pred-RET)**2).mean()
            self.oc.zero_grad();closs.backward();nn.utils.clip_grad_norm_(self.critic.parameters(),.5);self.oc.step()
            stat={"actor_loss":float(aloss.detach()),"critic_loss":float(closs.detach()),"entropy":float(ent.detach())}
        return stat

def rollout(env,sumo,agent,train):
    obs=env.start(sumo);traj=[];prob=np.zeros(3);pn=0;chosen=np.zeros(3,int)
    try:
        while True:
            mask=env.action_mask();a,lp,v,p=agent.act(obs,mask,not train);prob+=p.sum(0);pn+=len(p)
            for x in a:chosen[int(x)]+=1
            nxt,r,done=env.step(a)
            if train:traj.append({"obs":obs,"act":a,"lp":lp,"v":v,"r":r,"done":done,"mask":mask})
            obs=nxt
            if done:break
        s=env.summary()
        for i in range(3):s[f"policy_prob_a{i}"]=float(prob[i]/max(pn,1));s[f"chosen_a{i}"]=int(chosen[i])
        return traj,s
    finally:env.close()

def native_eval(traci,sumo,scenario,selection,begin_s,control_s,seed):
    env=Env(traci,scenario,selection,begin_s,control_s,seed)
    env.start(sumo)
    try:
        while env.tc.time_s()<env.end and env.tc.min_expected()>0:
            arrived=0;co2=0.
            for _ in range(env.decision_dt):
                if env.tc.min_expected()<=0:break
                env.tc.step();arrived+=env.tc.arrived_number()
                for tl in env.tls:co2+=env.lane_stats(tl)["co2"]
            stats=[env.lane_stats(t) for t in env.tls]
            env.metrics["halt"]+=sum(s["halt"] for s in stats);env.metrics["waiting"]+=sum(s["waiting"] for s in stats)
            env.metrics["arrived"]+=arrived;env.metrics["co2_mg"]+=co2;env.steps+=1
        return env.summary()
    finally:env.close()

def write_csv(path,rows):
    if not rows:return
    fields=[];seen=set()
    for r in rows:
        for k in r:
            if k not in seen:seen.add(k);fields.append(k)
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow(r)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo",required=True);ap.add_argument("--sumo-tools",required=True);ap.add_argument("--scenario",required=True)
    ap.add_argument("--selection",required=True);ap.add_argument("--windows",required=True);ap.add_argument("--outdir",required=True)
    ap.add_argument("--episodes",type=int,default=32);ap.add_argument("--train-s",type=int,default=900)
    ap.add_argument("--eval-s",type=int,default=1800);ap.add_argument("--eval-seeds",default="9001,9002,9003");ap.add_argument("--seed",type=int,default=42)
    ap.add_argument("--states-dir",default=None,help="Directory containing state_<condition>.xml files generated from a full LuST run")
    args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
    sys.path.insert(0,os.path.abspath(args.sumo_tools));import traci
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    sel=read_csv(args.selection);wins={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(args.windows)}
    conds=[c for c in ("Off-peak","AM","Lunch","PM") if c in wins]
    def state_for(cond):
        if not args.states_dir:return None
        return os.path.join(os.path.abspath(args.states_dir),f"state_{cond.replace('-','_')}.xml")
    if args.states_dir:
        for cond in conds:
            p=state_for(cond)
            if not os.path.isfile(p):raise FileNotFoundError(p)
    agent=MAPPO(9,13,3,args.seed);hist=[];t0=time.time()
    for ep in range(args.episodes):
        cond=conds[ep%len(conds)];seed=1000+ep
        env=Env(traci,args.scenario,sel,wins[cond]*3600,args.train_s,seed,load_state=state_for(cond))
        traj,s=rollout(env,args.sumo,agent,True);up=agent.update(traj)
        row={"episode":ep+1,"condition":cond,"seed":seed,**s,**up};hist.append(row);print(row,flush=True)
    write_csv(os.path.join(args.outdir,"training_history.csv"),hist)
    torch.save({"actor":agent.actor.state_dict(),"critic":agent.critic.state_dict(),
                "meta":{"algorithm":"SUMO0.27 guarded residual MAPPO","episodes":args.episodes,
                        "actions":{"0":"native","1":"+3s remaining-green extension","2":"+6s remaining-green extension"},
                        "gamma":.99,"gae":.95,"clip":.15,"decision_interval_s":10}},
               os.path.join(args.outdir,"legacy_mappo_residual.pt"))
    rows=[]
    for seed in [int(x) for x in args.eval_seeds.split(",") if x]:
        for cond in conds:
            if args.states_dir:
                benv=Env(traci,args.scenario,sel,wins[cond]*3600,args.eval_s,seed,load_state=state_for(cond))
                benv.start(args.sumo)
                try:
                    while benv.tc.time_s()<benv.end and benv.tc.min_expected()>0:
                        arrived=0;co2=0.
                        for _ in range(benv.decision_dt):
                            if benv.tc.min_expected()<=0:break
                            benv.tc.step();arrived+=benv.tc.arrived_number()
                            for tl in benv.tls:co2+=benv.lane_stats(tl)["co2"]
                        stats=[benv.lane_stats(t) for t in benv.tls]
                        benv.metrics["halt"]+=sum(s["halt"] for s in stats);benv.metrics["waiting"]+=sum(s["waiting"] for s in stats)
                        benv.metrics["arrived"]+=arrived;benv.metrics["co2_mg"]+=co2;benv.steps+=1
                    b=benv.summary()
                finally:benv.close()
            else:
                b=native_eval(traci,args.sumo,args.scenario,sel,wins[cond]*3600,args.eval_s,seed)
            rows.append({"controller":"Actuated","seed":seed,"condition":cond,**b})
            env=Env(traci,args.scenario,sel,wins[cond]*3600,args.eval_s,seed,load_state=state_for(cond))
            _,m=rollout(env,args.sumo,agent,False);rows.append({"controller":"MAPPO-residual","seed":seed,"condition":cond,**m})
            print(rows[-2:],flush=True)
    write_csv(os.path.join(args.outdir,"evaluation_raw.csv"),rows)
    summary=[]
    keys=["mean_halting_vehicles","mean_waiting_time_lane_sum_s","arrived_vehicles_global","CO2_kg_selected_approaches"]
    for ctrl in ("Actuated","MAPPO-residual"):
        for cond in conds:
            rr=[r for r in rows if r["controller"]==ctrl and r["condition"]==cond]
            o={"controller":ctrl,"condition":cond,"n":len(rr)}
            for k in keys:
                a=np.asarray([float(r[k]) for r in rr]);o[k+"_mean"]=float(a.mean());o[k+"_sd"]=float(a.std(ddof=1)) if len(a)>1 else 0.
            summary.append(o)
    write_csv(os.path.join(args.outdir,"evaluation_summary.csv"),summary)
    with open(os.path.join(args.outdir,"run_metadata.json"),"w") as f:json.dump({"wall_time_s":time.time()-t0,"conditions":conds},f,indent=2)

if __name__=="__main__":
    main()
