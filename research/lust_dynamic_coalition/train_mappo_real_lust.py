#!/usr/bin/env python3
"""
Real LuST v2.0 MAPPO pilot for nine traffic-signal agents.

The controller uses a parameter-shared PPO actor and a centralized critic
(MAPPO/CTDE). Each TLS has two physically safe actions:
  0 = keep/extend the current green phase;
  1 = release the current green phase and let the native SUMO phase program
      advance through its defined yellow/all-red transition sequence.

No unsafe direct green-to-green jump is used.
"""
import argparse, csv, json, math, os, random, sys, time
from collections import defaultdict
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

try:
    import traci
except ImportError:
    sys.path.append(os.path.join(os.environ.get("SUMO_HOME","/usr/share/sumo"),"tools"))
    import traci

ROUTES=",".join([
    "buslines.rou.xml",
    "DUERoutes/local.actuated.0.rou.xml",
    "DUERoutes/local.actuated.1.rou.xml",
    "DUERoutes/local.actuated.2.rou.xml",
    "transit.rou.xml",
])

def read_selected(path):
    rows=[]
    with open(path,newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f): rows.append(r)
    rows=sorted(rows,key=lambda r:int(r["agent_alias"][1:]))
    return rows

def read_windows(path):
    out={}
    with open(path,newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["condition"]]=int(float(r["selected_hour"]))
    return out

def parse_net_incoming(net_path,tls_ids):
    import xml.etree.ElementTree as ET
    root=ET.parse(net_path).getroot()
    lane_ids=set()
    for e in root.findall("edge"):
        if e.get("function"): continue
        for l in e.findall("lane"): lane_ids.add(l.get("id"))
    inc=defaultdict(set)
    for c in root.findall("connection"):
        tl=c.get("tl")
        if tl not in tls_ids: continue
        lid=f"{c.get('from')}_{c.get('fromLane')}"
        if lid in lane_ids: inc[tl].add(lid)
    return {k:sorted(v) for k,v in inc.items()}

def make_cmd(scenario,begin_s,end_s,seed):
    return [
        "sumo","-c",os.path.join(scenario,"due.actuated.sumocfg"),
        "--route-files",ROUTES,
        "--additional-files","vtypes.add.xml,busstops.add.xml",
        "--begin",str(max(0,int(begin_s))),
        "--end",str(int(end_s)),
        "--seed",str(seed),
        "--xml-validation","never",
        "--no-step-log","true",
        "--time-to-teleport","600",
    ]

def phase_is_green(state):
    return ("G" in state or "g" in state) and "y" not in state and "Y" not in state

class LuST9Env:
    def __init__(self,scenario,selected,begin_s,control_s=900,warmup_s=300,seed=42,label="mappo"):
        self.scenario=os.path.abspath(scenario)
        self.selected=selected
        self.tls=[r["tls_id"] for r in selected]
        self.alias={r["tls_id"]:r["agent_alias"] for r in selected}
        self.incoming=parse_net_incoming(os.path.join(self.scenario,"lust.net.xml"),set(self.tls))
        self.begin=max(0,begin_s-warmup_s)
        self.control_start=begin_s
        self.end=begin_s+control_s
        self.seed=seed
        self.label=label
        self.conn=None
        self.min_green=10.0
        self.decision_dt=10
        self.prev_wait=0.0
        self.metric_acc=defaultdict(float)
        self.steps=0

    @property
    def n_agents(self): return len(self.tls)
    @property
    def obs_dim(self): return 11
    @property
    def n_actions(self): return 2

    def start(self):
        traci.start(make_cmd(self.scenario,self.begin,self.end,self.seed),label=self.label)
        self.conn=traci.getConnection(self.label)
        while self.conn.simulation.getTime() < self.control_start and self.conn.simulation.getMinExpectedNumber()>0:
            self.conn.simulationStep()
        return self.observe()

    def close(self):
        if self.conn is not None:
            try:self.conn.close()
            except Exception:pass
            self.conn=None

    def lane_stats(self,tl):
        ls=self.incoming.get(tl,[])
        veh=sum(self.conn.lane.getLastStepVehicleNumber(l) for l in ls)
        halt=sum(self.conn.lane.getLastStepHaltingNumber(l) for l in ls)
        occ=[self.conn.lane.getLastStepOccupancy(l) for l in ls]
        weighted_speed=0.0; weight=0
        waiting=0.0; co2=0.0
        for l in ls:
            n=self.conn.lane.getLastStepVehicleNumber(l)
            sp=self.conn.lane.getLastStepMeanSpeed(l)
            if n>0 and sp>=0:
                weighted_speed+=n*sp; weight+=n
            try:waiting+=self.conn.lane.getWaitingTime(l)
            except Exception:pass
            try:co2+=self.conn.lane.getCO2Emission(l)
            except Exception:pass
        return {
            "veh":veh,"halt":halt,
            "speed":weighted_speed/max(weight,1),
            "occ":sum(occ)/max(len(occ),1),
            "waiting":waiting,"co2":co2,"lanes":len(ls)
        }

    def observe(self):
        obs=[]
        for tl in self.tls:
            s=self.lane_stats(tl)
            phase=self.conn.trafficlight.getPhase(tl)
            logic=self.conn.trafficlight.getAllProgramLogics(tl)[0]
            nph=max(len(logic.phases),1)
            state=logic.phases[phase].state if phase < len(logic.phases) else ""
            try:spent=self.conn.trafficlight.getSpentDuration(tl)
            except Exception:spent=0.0
            L=max(s["lanes"],1)
            o=np.array([
                np.clip(s["veh"]/max(12*L,1),0,3),
                np.clip(s["halt"]/max(8*L,1),0,3),
                np.clip(s["speed"]/15.0,0,3),
                np.clip(s["occ"]/100.0,0,1.5),
                np.clip(s["waiting"]/max(300*L,1),0,5),
                phase/max(nph-1,1),
                1.0 if phase_is_green(state) else 0.0,
                np.clip(spent/60.0,0,3),
                1.0,1.0,1.0, # TA/MO/VI availability; EC appended below as 1 for GC
            ],dtype=np.float32)
            # replace final three+append to exact four stakeholder mask dimensions
            o=np.concatenate([o[:8],np.ones(3,dtype=np.float32)])
            # obs_dim is 11: 8 traffic/phase + 3 information channels for pilot GC
            obs.append(o)
        return np.stack(obs)

    def apply_actions(self,actions):
        for tl,a in zip(self.tls,actions):
            phase=self.conn.trafficlight.getPhase(tl)
            logic=self.conn.trafficlight.getAllProgramLogics(tl)[0]
            if phase>=len(logic.phases): continue
            state=logic.phases[phase].state
            try:spent=self.conn.trafficlight.getSpentDuration(tl)
            except Exception:spent=self.min_green
            # During yellow/all-red the native program is left untouched.
            if not phase_is_green(state): continue
            if int(a)==0:
                # Extend the current green until the next decision epoch.
                self.conn.trafficlight.setPhaseDuration(tl,float(self.decision_dt))
            elif spent>=self.min_green:
                # Release current green. SUMO then follows the native next phase,
                # preserving the program-defined yellow/all-red transition.
                self.conn.trafficlight.setPhaseDuration(tl,0.1)

    def step(self,actions):
        self.apply_actions(actions)
        arrived=0
        co2_sum=0.0
        for _ in range(self.decision_dt):
            if self.conn.simulation.getMinExpectedNumber()<=0: break
            self.conn.simulationStep()
            arrived+=self.conn.simulation.getArrivedNumber()
            for tl in self.tls:
                co2_sum+=self.lane_stats(tl)["co2"]
        obs=self.observe()
        stats=[self.lane_stats(tl) for tl in self.tls]
        halt=sum(s["halt"] for s in stats)
        waiting=sum(s["waiting"] for s in stats)
        veh=sum(s["veh"] for s in stats)
        lanes=sum(max(s["lanes"],1) for s in stats)
        q_norm=halt/max(8*lanes,1)
        w_norm=waiting/max(300*lanes,1)
        reward=-0.5*q_norm-0.5*w_norm
        self.metric_acc["halt"]+=halt
        self.metric_acc["waiting"]+=waiting
        self.metric_acc["veh"]+=veh
        self.metric_acc["arrived"]+=arrived
        self.metric_acc["co2_mg"]+=co2_sum
        self.metric_acc["reward"]+=reward
        self.steps+=1
        done=self.conn.simulation.getTime()>=self.end or self.conn.simulation.getMinExpectedNumber()<=0
        return obs,float(reward),done,{"halt":halt,"waiting":waiting,"arrived":arrived,"co2_mg":co2_sum}

    def summary(self):
        n=max(self.steps,1)
        return {
            "mean_halting_vehicles":self.metric_acc["halt"]/n,
            "mean_waiting_time_lane_sum_s":self.metric_acc["waiting"]/n,
            "mean_observed_vehicles":self.metric_acc["veh"]/n,
            "arrived_vehicles":self.metric_acc["arrived"],
            "CO2_kg_selected_approaches":self.metric_acc["co2_mg"]/1e6,
            "mean_reward":self.metric_acc["reward"]/n,
            "decision_steps":self.steps
        }

class Actor(nn.Module):
    def __init__(self,obs_dim,n_actions):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(obs_dim,128),nn.Tanh(),nn.Linear(128,128),nn.Tanh(),nn.Linear(128,n_actions))
    def forward(self,x): return self.net(x)

class Critic(nn.Module):
    def __init__(self,global_dim):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(global_dim,256),nn.Tanh(),nn.Linear(256,128),nn.Tanh(),nn.Linear(128,1))
    def forward(self,x): return self.net(x).squeeze(-1)

class MAPPO:
    def __init__(self,n_agents,obs_dim,n_actions,seed=42,lr=3e-4):
        torch.manual_seed(seed)
        self.n_agents=n_agents; self.obs_dim=obs_dim; self.n_actions=n_actions
        self.actor=Actor(obs_dim,n_actions)
        self.critic=Critic(n_agents*obs_dim)
        self.opt_a=optim.Adam(self.actor.parameters(),lr=lr)
        self.opt_c=optim.Adam(self.critic.parameters(),lr=lr)
        self.gamma=.99; self.lam=.95; self.clip=.2; self.ent=.01

    def act(self,obs,deterministic=False):
        x=torch.tensor(obs,dtype=torch.float32)
        dist=torch.distributions.Categorical(logits=self.actor(x))
        a=torch.argmax(dist.logits,dim=-1) if deterministic else dist.sample()
        lp=dist.log_prob(a).sum()
        gv=self.critic(torch.tensor(obs.reshape(-1),dtype=torch.float32))
        return a.numpy(),float(lp.detach()),float(gv.detach())

    def value(self,obs):
        with torch.no_grad(): return float(self.critic(torch.tensor(obs.reshape(-1),dtype=torch.float32)))

    def update(self,traj,epochs=5):
        obs=np.asarray([x["obs"] for x in traj],np.float32)
        act=np.asarray([x["act"] for x in traj],np.int64)
        oldlp=np.asarray([x["logp"] for x in traj],np.float32)
        rew=np.asarray([x["rew"] for x in traj],np.float32)
        val=np.asarray([x["val"] for x in traj],np.float32)
        done=np.asarray([x["done"] for x in traj],np.float32)
        next_val=0.0
        adv=np.zeros_like(rew)
        gae=0.0
        for t in reversed(range(len(rew))):
            nv=next_val if t==len(rew)-1 else val[t+1]
            mask=1.0-done[t]
            delta=rew[t]+self.gamma*nv*mask-val[t]
            gae=delta+self.gamma*self.lam*mask*gae
            adv[t]=gae
        ret=adv+val
        adv=(adv-adv.mean())/(adv.std()+1e-8)

        O=torch.tensor(obs); A=torch.tensor(act)
        OLD=torch.tensor(oldlp); ADV=torch.tensor(adv); RET=torch.tensor(ret)
        G=O.reshape(len(O),-1)
        stats={}
        for _ in range(epochs):
            logits=self.actor(O.reshape(-1,self.obs_dim)).reshape(len(O),self.n_agents,self.n_actions)
            dist=torch.distributions.Categorical(logits=logits)
            lp=dist.log_prob(A).sum(dim=1)
            ratio=torch.exp(lp-OLD)
            pg1=ratio*ADV; pg2=torch.clamp(ratio,1-self.clip,1+self.clip)*ADV
            ent=dist.entropy().mean()
            aloss=-torch.min(pg1,pg2).mean()-self.ent*ent
            self.opt_a.zero_grad(); aloss.backward(); nn.utils.clip_grad_norm_(self.actor.parameters(),0.5); self.opt_a.step()

            pred=self.critic(G)
            closs=((pred-RET)**2).mean()
            self.opt_c.zero_grad(); closs.backward(); nn.utils.clip_grad_norm_(self.critic.parameters(),0.5); self.opt_c.step()
            stats={"actor_loss":float(aloss.detach()),"critic_loss":float(closs.detach()),"entropy":float(ent.detach())}
        return stats

    def save(self,path,meta):
        torch.save({"actor":self.actor.state_dict(),"critic":self.critic.state_dict(),"meta":meta},path)

def run_policy(env,agent,train=True):
    obs=env.start(); traj=[]
    try:
        while True:
            act,lp,val=agent.act(obs,deterministic=not train)
            nxt,r,done,info=env.step(act)
            if train: traj.append({"obs":obs,"act":act,"logp":lp,"val":val,"rew":r,"done":done})
            obs=nxt
            if done: break
        summ=env.summary()
    finally:
        env.close()
    return traj,summ

def run_actuated(env):
    obs=env.start()
    try:
        while True:
            # no TraCI signal intervention; step native actuated controller
            arrived=0; co2=0
            for _ in range(env.decision_dt):
                if env.conn.simulation.getMinExpectedNumber()<=0: break
                env.conn.simulationStep()
                arrived+=env.conn.simulation.getArrivedNumber()
                for tl in env.tls: co2+=env.lane_stats(tl)["co2"]
            stats=[env.lane_stats(tl) for tl in env.tls]
            env.metric_acc["halt"]+=sum(s["halt"] for s in stats)
            env.metric_acc["waiting"]+=sum(s["waiting"] for s in stats)
            env.metric_acc["veh"]+=sum(s["veh"] for s in stats)
            env.metric_acc["arrived"]+=arrived
            env.metric_acc["co2_mg"]+=co2
            env.steps+=1
            if env.conn.simulation.getTime()>=env.end or env.conn.simulation.getMinExpectedNumber()<=0: break
        return env.summary()
    finally: env.close()

def write_rows(path,rows):
    if not rows:return
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scenario",required=True)
    ap.add_argument("--selection",required=True)
    ap.add_argument("--windows",required=True)
    ap.add_argument("--outdir",required=True)
    ap.add_argument("--episodes",type=int,default=48)
    ap.add_argument("--train-control-s",type=int,default=900)
    ap.add_argument("--eval-control-s",type=int,default=3600)
    ap.add_argument("--eval-seeds",default="9001,9002,9003")
    ap.add_argument("--seed",type=int,default=42)
    args=ap.parse_args()
    os.makedirs(args.outdir,exist_ok=True)
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    selected=read_selected(args.selection); windows=read_windows(args.windows)
    conditions=[c for c in ["Off-peak","AM","Lunch","PM"] if c in windows]
    agent=MAPPO(len(selected),11,2,seed=args.seed)
    train_rows=[]
    t0=time.time()
    for ep in range(args.episodes):
        cond=conditions[ep%len(conditions)]
        h=windows[cond]
        seed=1000+ep
        env=LuST9Env(args.scenario,selected,h*3600,control_s=args.train_control_s,warmup_s=300,seed=seed,label=f"train-{ep}")
        traj,summ=run_policy(env,agent,train=True)
        upd=agent.update(traj,epochs=5)
        row={"episode":ep+1,"condition":cond,"hour":h,"seed":seed,**summ,**upd}
        train_rows.append(row);print(row,flush=True)
    meta={"algorithm":"parameter-shared MAPPO with centralized critic","episodes":args.episodes,
          "gamma":.99,"gae_lambda":.95,"ppo_clip":.2,"actor_lr":3e-4,"critic_lr":3e-4,
          "decision_interval_s":10,"min_green_s":10,
          "action_0":"extend current green","action_1":"release current green to native safe transition",
          "training_conditions":conditions,"wall_time_s":time.time()-t0}
    agent.save(os.path.join(args.outdir,"mappo_lust9.pt"),meta)
    write_rows(os.path.join(args.outdir,"training_history.csv"),train_rows)

    eval_rows=[]
    for seed in [int(x) for x in args.eval_seeds.split(",") if x.strip()]:
        for cond in conditions:
            h=windows[cond]
            b=LuST9Env(args.scenario,selected,h*3600,control_s=args.eval_control_s,warmup_s=300,seed=seed,label=f"base-{seed}-{cond}")
            bs=run_actuated(b);eval_rows.append({"controller":"Actuated","seed":seed,"condition":cond,"hour":h,**bs})
            m=LuST9Env(args.scenario,selected,h*3600,control_s=args.eval_control_s,warmup_s=300,seed=seed,label=f"mappo-{seed}-{cond}")
            _,ms=run_policy(m,agent,train=False);eval_rows.append({"controller":"MAPPO","seed":seed,"condition":cond,"hour":h,**ms})
            print(eval_rows[-2:],flush=True)
    write_rows(os.path.join(args.outdir,"evaluation_raw.csv"),eval_rows)

    # aggregate mean/std
    agg=[]
    keys=["mean_halting_vehicles","mean_waiting_time_lane_sum_s","arrived_vehicles","CO2_kg_selected_approaches","mean_reward"]
    for ctrl in ["Actuated","MAPPO"]:
        for cond in conditions:
            rr=[r for r in eval_rows if r["controller"]==ctrl and r["condition"]==cond]
            o={"controller":ctrl,"condition":cond,"n_seeds":len(rr)}
            for k in keys:
                vals=np.array([float(r[k]) for r in rr])
                o[k+"_mean"]=float(vals.mean());o[k+"_sd"]=float(vals.std(ddof=1)) if len(vals)>1 else 0.0
            agg.append(o)
    write_rows(os.path.join(args.outdir,"evaluation_summary.csv"),agg)
    with open(os.path.join(args.outdir,"run_metadata.json"),"w") as f:json.dump(meta,f,indent=2)
    print(json.dumps({"metadata":meta,"summary":agg},indent=2))

if __name__=="__main__":
    main()
