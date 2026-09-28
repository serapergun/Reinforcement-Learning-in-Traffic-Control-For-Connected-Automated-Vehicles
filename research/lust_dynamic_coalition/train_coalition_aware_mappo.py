#!/usr/bin/env python3
"""
Coalition-aware MAPPO pilot on the official LuST v2.0 scenario.

Stakeholder observation channels
--------------------------------
TA: exact infrastructure traffic state (vehicle count, halting count, occupancy)
MO: probe/FCD mean speed and waiting time (reference penetration p_FCD=0.20)
VI: connected-vehicle count/speed/acceleration (reference availability p_V2X=0.75)
EC: 60-s queue forecast from the real-data GRU trained in Stage2

The policy also receives the four-bit coalition mask [TA, MO, VI, EC].
The infeasible singleton {EC} is excluded.
"""
import argparse, csv, hashlib, json, math, os, random, sys, time
from collections import defaultdict, deque
import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_mappo_real_lust import MAPPO, phase_is_green, parse_net_incoming, ROUTES

try:
    import traci
except ImportError:
    sys.path.append(os.path.join(os.environ.get("SUMO_HOME","/usr/share/sumo"),"tools"))
    import traci

PLAYERS=("TA","MO","VI","EC")

def feasible_coalitions():
    out=[]
    for bits in range(1,16):
        s={PLAYERS[i] for i in range(4) if bits&(1<<i)}
        if s=={"EC"}: continue
        out.append(tuple(p for p in PLAYERS if p in s))
    return out

def mask_of(coalition):
    return np.array([1.0 if p in coalition else 0.0 for p in PLAYERS],dtype=np.float32)

def stable_select(vehicle_id, penetration, salt):
    if penetration>=1: return True
    h=hashlib.sha1(f"{salt}:{vehicle_id}".encode()).digest()
    u=int.from_bytes(h[:8],"big")/float(2**64-1)
    return u < penetration

def read_csv(path):
    with open(path,newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

class GRUModel(nn.Module):
    def __init__(self,d):
        super().__init__()
        self.gru=nn.GRU(d,64,batch_first=True)
        self.head=nn.Sequential(nn.Linear(64,32),nn.ReLU(),nn.Linear(32,1))
    def forward(self,x):
        z,_=self.gru(x)
        return self.head(z[:,-1]).squeeze(-1)

class QueueForecaster:
    def __init__(self,path):
        obj=torch.load(path,map_location="cpu")
        m=obj["metrics"]
        self.features=m["features"]
        self.mu=np.asarray(m["normalization_mean"],dtype=np.float32)
        self.sd=np.asarray(m["normalization_std"],dtype=np.float32)
        self.model=GRUModel(len(self.features))
        self.model.load_state_dict(obj["state_dict"]); self.model.eval()
        self.history=defaultdict(lambda: deque(maxlen=30))

    def reset(self): self.history=defaultdict(lambda: deque(maxlen=30))

    def append(self,tl,feature_dict):
        x=np.array([feature_dict[k] for k in self.features],dtype=np.float32)
        self.history[tl].append(x)

    def predict(self,tl):
        h=self.history[tl]
        if not h: return 0.0,0.0
        arr=list(h)
        while len(arr)<30: arr.insert(0,arr[0].copy())
        x=np.stack(arr[-30:])
        xn=(x-self.mu)/(self.sd+1e-6)
        t0=time.perf_counter_ns()
        with torch.no_grad():
            y=float(self.model(torch.tensor(xn[None],dtype=torch.float32)).item())
        dt_ms=(time.perf_counter_ns()-t0)/1e6
        return max(0.0,y),dt_ms

class CoalitionEnv:
    def __init__(self,scenario,selection,forecaster,coalition,begin_s,control_s,seed,label,
                 p_fcd=.20,p_v2x=.75,warmup_s=300):
        self.scenario=os.path.abspath(scenario); self.selection=selection
        self.tls=[r["tls_id"] for r in selection]
        self.alias={r["tls_id"]:r["agent_alias"] for r in selection}
        self.incoming=parse_net_incoming(os.path.join(self.scenario,"lust.net.xml"),set(self.tls))
        self.forecaster=forecaster; self.coalition=tuple(coalition); self.mask=mask_of(coalition)
        self.begin=max(0,int(begin_s-warmup_s)); self.control_start=int(begin_s); self.end=int(begin_s+control_s)
        self.seed=int(seed); self.label=label; self.p_fcd=p_fcd; self.p_v2x=p_v2x
        self.conn=None; self.decision_dt=10; self.min_green=10.0
        self.metrics=defaultdict(float); self.steps=0
        self.resource=defaultdict(float)

    @property
    def obs_dim(self): return 3+3+2+3+1+4

    def cmd(self):
        return ["sumo","-c",os.path.join(self.scenario,"due.actuated.sumocfg"),
                "--route-files",ROUTES,
                "--additional-files","vtypes.add.xml,busstops.add.xml",
                "--begin",str(self.begin),"--end",str(self.end),
                "--seed",str(self.seed),"--xml-validation","never",
                "--no-step-log","true","--time-to-teleport","600"]

    def start(self):
        self.forecaster.reset()
        traci.start(self.cmd(),label=self.label)
        self.conn=traci.getConnection(self.label)
        # Warmup with native actuated control while building coalition-conditioned GRU history.
        while self.conn.simulation.getTime()<self.control_start and self.conn.simulation.getMinExpectedNumber()>0:
            self.conn.simulationStep()
            t=self.conn.simulation.getTime()
            if int(round(t))%10==0:
                for tl in self.tls:
                    raw=self.raw_state(tl)
                    ch=self.channels(tl,raw,count_resources=False)
                    self.forecaster.append(tl,ch["gru_input"])
        return self.observe()

    def close(self):
        if self.conn:
            try:self.conn.close()
            except Exception:pass
            self.conn=None

    def current_logic(self,tl):
        program=self.conn.trafficlight.getProgram(tl)
        logics=self.conn.trafficlight.getAllProgramLogics(tl)
        for l in logics:
            if l.programID==program:return l
        return logics[0]

    def raw_state(self,tl):
        lanes=self.incoming.get(tl,[])
        vids=[]
        veh=halt=0; occ=[]; weighted_speed=0.; speed_n=0; waiting=0.; co2=0.
        for lane in lanes:
            ids=list(self.conn.lane.getLastStepVehicleIDs(lane)); vids.extend(ids)
            n=self.conn.lane.getLastStepVehicleNumber(lane); veh+=n
            halt+=self.conn.lane.getLastStepHaltingNumber(lane)
            occ.append(self.conn.lane.getLastStepOccupancy(lane))
            sp=self.conn.lane.getLastStepMeanSpeed(lane)
            if n>0 and sp>=0: weighted_speed+=n*sp; speed_n+=n
            try: waiting+=self.conn.lane.getWaitingTime(lane)
            except Exception:
                for vid in ids:
                    try: waiting+=self.conn.vehicle.getWaitingTime(vid)
                    except Exception: pass
            try: co2+=self.conn.lane.getCO2Emission(lane)
            except Exception: pass
        return {"veh":float(veh),"halt":float(halt),"occ":sum(occ)/max(len(occ),1),
                "speed":weighted_speed/max(speed_n,1),"waiting":waiting,"co2":co2,
                "vids":list(dict.fromkeys(vids)),"lanes":max(len(lanes),1)}

    def channels(self,tl,raw,count_resources=True):
        c=set(self.coalition); vids=raw["vids"]; salt=f"{self.seed}:{int(self.conn.simulation.getTime())}:{tl}"
        probe=[v for v in vids if stable_select(v,self.p_fcd,salt+":MO")]
        connv=[v for v in vids if stable_select(v,self.p_v2x,salt+":VI")]

        def vals(ids):
            if not ids:return (0.,0.,0.,0.)
            sp=[]; wt=[]; ac=[]; hal=0
            for v in ids:
                try:
                    s=max(0.,self.conn.vehicle.getSpeed(v)); sp.append(s)
                    wt.append(max(0.,self.conn.vehicle.getWaitingTime(v)))
                    ac.append(self.conn.vehicle.getAcceleration(v))
                    if s<0.1: hal+=1
                except Exception: pass
            return (float(np.mean(sp)) if sp else 0.,
                    float(np.mean(wt)) if wt else 0.,
                    float(np.mean(ac)) if ac else 0.,
                    float(hal))
        mo_speed,mo_wait,_,_=vals(probe)
        vi_speed,_,vi_acc,vi_halt=vals(connv)

        # Construct the GRU input from only coalition-available upstream channels.
        # Missing features are imputed at the training mean, which equals zero after normalization.
        feature={k:float(self.forecaster.mu[i]) for i,k in enumerate(self.forecaster.features)}
        if "TA" in c:
            feature["veh_count"]=raw["veh"]; feature["halting_count"]=raw["halt"]
            feature["mean_occupancy_pct"]=raw["occ"]
        if "MO" in c:
            feature["mean_speed_mps"]=mo_speed; feature["waiting_time_s"]=mo_wait
        if "VI" in c:
            # Horvitz-Thompson-like scaling of connected counts under known availability.
            est_count=len(connv)/max(self.p_v2x,1e-6)
            est_halt=vi_halt/max(self.p_v2x,1e-6)
            if "TA" not in c:
                feature["veh_count"]=est_count; feature["halting_count"]=est_halt
            if "MO" not in c:
                feature["mean_speed_mps"]=vi_speed

        ec_pred=0.; ec_ms=0.
        if "EC" in c:
            ec_pred,ec_ms=self.forecaster.predict(tl)

        if count_resources:
            # Payload accounting: float32 application payload, excluding transport headers.
            if "TA" in c: self.resource["data_bytes"]+=3*4; self.resource["messages"]+=1
            if "MO" in c: self.resource["data_bytes"]+=2*4; self.resource["messages"]+=1
            if "VI" in c:
                self.resource["data_bytes"]+=len(connv)*3*4; self.resource["messages"]+=len(connv)
            if "EC" in c:
                self.resource["data_bytes"]+=1*4; self.resource["messages"]+=1
                self.resource["compute_ms"]+=ec_ms

        return {
            "ta":(raw["veh"],raw["halt"],raw["occ"]) if "TA" in c else (0.,0.,0.),
            "mo":(mo_speed,mo_wait) if "MO" in c else (0.,0.),
            "vi":(len(connv)/max(len(vids),1),vi_speed,vi_acc) if "VI" in c else (0.,0.,0.),
            "ec":ec_pred if "EC" in c else 0.,
            "gru_input":feature
        }

    def observe(self):
        obs=[]
        for tl in self.tls:
            raw=self.raw_state(tl); ch=self.channels(tl,raw,True)
            phase=self.conn.trafficlight.getPhase(tl); logic=self.current_logic(tl)
            nph=max(len(logic.phases),1); state=logic.phases[phase].state if phase<len(logic.phases) else ""
            try:spent=self.conn.trafficlight.getSpentDuration(tl)
            except Exception:spent=0.
            L=raw["lanes"]
            ta=ch["ta"]; mo=ch["mo"]; vi=ch["vi"]
            o=np.array([
                phase/max(nph-1,1), 1.0 if phase_is_green(state) else 0.0, np.clip(spent/60.,0,3),
                np.clip(ta[0]/max(12*L,1),0,3),np.clip(ta[1]/max(8*L,1),0,3),np.clip(ta[2]/100.,0,1.5),
                np.clip(mo[0]/15.,0,3),np.clip(mo[1]/120.,0,5),
                np.clip(vi[0],0,1),np.clip(vi[1]/15.,0,3),np.clip((vi[2]+5.)/10.,0,1),
                np.clip(ch["ec"]/max(8*L,1),0,3),
                *self.mask.tolist()
            ],dtype=np.float32)
            obs.append(o)
            self.forecaster.append(tl,ch["gru_input"])
        return np.stack(obs)

    def apply(self,actions):
        for tl,a in zip(self.tls,actions):
            ph=self.conn.trafficlight.getPhase(tl); logic=self.current_logic(tl)
            if ph>=len(logic.phases):continue
            state=logic.phases[ph].state
            try:spent=self.conn.trafficlight.getSpentDuration(tl)
            except Exception:spent=self.min_green
            if not phase_is_green(state):continue
            if int(a)==0:self.conn.trafficlight.setPhaseDuration(tl,float(self.decision_dt))
            elif spent>=self.min_green:self.conn.trafficlight.setPhaseDuration(tl,0.1)

    def step(self,actions):
        self.apply(actions); arrived=0; co2=0.
        for _ in range(self.decision_dt):
            if self.conn.simulation.getMinExpectedNumber()<=0:break
            self.conn.simulationStep(); arrived+=self.conn.simulation.getArrivedNumber()
            for tl in self.tls:co2+=self.raw_state(tl)["co2"]
        raw=[self.raw_state(tl) for tl in self.tls]
        halt=sum(x["halt"] for x in raw); wait=sum(x["waiting"] for x in raw); lanes=sum(x["lanes"] for x in raw)
        reward=-.5*halt/max(8*lanes,1)-.5*wait/max(300*lanes,1)
        self.metrics["halt"]+=halt;self.metrics["waiting"]+=wait;self.metrics["arrived"]+=arrived
        self.metrics["co2_mg"]+=co2;self.metrics["reward"]+=reward;self.steps+=1
        done=self.conn.simulation.getTime()>=self.end or self.conn.simulation.getMinExpectedNumber()<=0
        return self.observe(),float(reward),done

    def summary(self):
        n=max(self.steps,1); sec=n*self.decision_dt
        return {
            "mean_halting_vehicles":self.metrics["halt"]/n,
            "mean_waiting_time_lane_sum_s":self.metrics["waiting"]/n,
            "arrived_vehicles":self.metrics["arrived"],
            "CO2_kg_selected_approaches":self.metrics["co2_mg"]/1e6,
            "mean_reward":self.metrics["reward"]/n,
            "payload_kB":self.resource["data_bytes"]/1024.,
            "message_count":self.resource["messages"],
            "mean_payload_bandwidth_Bps":self.resource["data_bytes"]/max(sec,1),
            "EC_compute_ms":self.resource["compute_ms"],
            "decision_steps":self.steps
        }

def rollout(env,agent,train):
    obs=env.start(); traj=[]
    try:
        while True:
            a,lp,v=agent.act(obs,deterministic=not train)
            nxt,r,done=env.step(a)
            if train:traj.append({"obs":obs,"act":a,"logp":lp,"val":v,"rew":r,"done":done})
            obs=nxt
            if done:break
        return traj,env.summary()
    finally:env.close()

def write_csv(path,rows):
    if not rows:return
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scenario",required=True);ap.add_argument("--selection",required=True)
    ap.add_argument("--windows",required=True);ap.add_argument("--gru",required=True);ap.add_argument("--outdir",required=True)
    ap.add_argument("--episodes",type=int,default=20);ap.add_argument("--train-control-s",type=int,default=600)
    ap.add_argument("--eval-control-s",type=int,default=600);ap.add_argument("--seed",type=int,default=42)
    ap.add_argument("--p-fcd",type=float,default=.20);ap.add_argument("--p-v2x",type=float,default=.75)
    args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    sel=sorted(read_csv(args.selection),key=lambda r:int(r["agent_alias"][1:]))
    wins={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(args.windows)}
    conds=[c for c in ("Off-peak","AM","Lunch","PM") if c in wins]
    coal=feasible_coalitions(); fore=QueueForecaster(args.gru)
    agent=MAPPO(len(sel),16,2,seed=args.seed)
    train_rows=[]
    for ep in range(args.episodes):
        # size-stratified cycling avoids overtraining large coalitions
        sizes=sorted(set(map(len,coal))); size=sizes[ep%len(sizes)]
        candidates=[s for s in coal if len(s)==size]
        coalition=candidates[(ep//len(sizes))%len(candidates)]
        cond=conds[ep%len(conds)]; seed=2000+ep
        env=CoalitionEnv(args.scenario,sel,fore,coalition,wins[cond]*3600,args.train_control_s,seed,f"ca-tr-{ep}",args.p_fcd,args.p_v2x)
        traj,s=rollout(env,agent,True); upd=agent.update(traj,epochs=5)
        row={"episode":ep+1,"condition":cond,"coalition":"+".join(coalition),"seed":seed,**s,**upd}
        train_rows.append(row);print(row,flush=True)
    meta={"algorithm":"coalition-aware parameter-shared MAPPO/CTDE","players":PLAYERS,
          "feasible_coalitions":["+".join(s) for s in coal],"episodes":args.episodes,
          "p_FCD":args.p_fcd,"p_V2X":args.p_v2x,"decision_interval_s":10,
          "training_conditions":conds,"observation_dim":16,
          "resource_accounting":"float32 application payload; VI telemetry counts 3 floats per connected vehicle; EC wall-clock inference ms"}
    agent.save(os.path.join(args.outdir,"coalition_aware_mappo.pt"),meta)
    write_csv(os.path.join(args.outdir,"training_history.csv"),train_rows)

    # Short all-coalition smoke evaluation: one common seed and each native condition.
    eval_rows=[]
    for cond in conds:
        for coalition in coal:
            env=CoalitionEnv(args.scenario,sel,fore,coalition,wins[cond]*3600,args.eval_control_s,7777,
                             f"ca-ev-{cond}-{'-'.join(coalition)}",args.p_fcd,args.p_v2x)
            _,s=rollout(env,agent,False)
            row={"condition":cond,"coalition":"+".join(coalition),"coalition_size":len(coalition),"seed":7777,**s}
            eval_rows.append(row);print(row,flush=True)
    write_csv(os.path.join(args.outdir,"all_coalition_pilot.csv"),eval_rows)
    with open(os.path.join(args.outdir,"run_metadata.json"),"w") as f:json.dump(meta,f,indent=2)

if __name__=="__main__":
    main()
