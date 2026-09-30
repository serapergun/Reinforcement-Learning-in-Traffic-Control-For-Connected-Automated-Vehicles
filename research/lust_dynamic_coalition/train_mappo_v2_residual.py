#!/usr/bin/env python3
"""
LuST v2.0 residual MAPPO-v2 for nine traffic-signal agents.

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
    scenario=os.path.abspath(scenario)
    routes=",".join(os.path.join(scenario,p) for p in ROUTES.split(","))
    additional=",".join(os.path.join(scenario,p) for p in ["vtypes.add.xml","busstops.add.xml"])
    return [
        "sumo","-c",os.path.join(scenario,"due.actuated.sumocfg"),
        "--route-files",routes,
        "--additional-files",additional,
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
    def obs_dim(self): return 12
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
                # EC persistence forecast: q(t+60) := q(t), selected after GRU-v2 failed
                # to improve on persistence in the validated forecasting benchmark.
                np.clip(s["halt"]/max(8*L,1),0,3),
                1.0,1.0,1.0,1.0,
            ],dtype=np.float32)
            # 8 local traffic/phase features + 1 EC persistence forecast + 4 stakeholder bits.
            obs.append(o)
        return np.stack(obs)

    def apply_actions(self,actions):
        """Residual safe control: action 0 leaves native actuated logic untouched."""
        for tl,a in zip(self.tls,actions):
            if int(a)==0:
                continue
            phase=self.conn.trafficlight.getPhase(tl)
            logic=self.conn.trafficlight.getAllProgramLogics(tl)[0]
            if phase>=len(logic.phases):
                continue
            state=logic.phases[phase].state
            if not phase_is_green(state):
                continue
            # Only extend an existing green. Never force a phase release or direct transition.
            self.conn.trafficlight.setPhaseDuration(tl,float(self.decision_dt))

