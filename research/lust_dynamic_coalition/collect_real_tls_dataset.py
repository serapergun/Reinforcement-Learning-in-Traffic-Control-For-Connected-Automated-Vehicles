#!/usr/bin/env python3
import argparse, csv, os, subprocess, sys, math
import xml.etree.ElementTree as ET
from collections import defaultdict

def parse_selection(path):
    rows=[]
    with open(path,newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def parse_net(net_path, tls_ids):
    root=ET.parse(net_path).getroot()
    lanes={}
    incoming=defaultdict(set)
    for e in root.findall("edge"):
        if e.get("function"): continue
        eid=e.get("id")
        for lane in e.findall("lane"):
            lanes[lane.get("id")]={"edge":eid,"length":float(lane.get("length","0"))}
    for c in root.findall("connection"):
        tl=c.get("tl")
        if tl not in tls_ids: continue
        fr=c.get("from"); fl=c.get("fromLane")
        lid=f"{fr}_{fl}"
        if lid in lanes: incoming[tl].add(lid)
    return incoming

def routes():
    return ",".join([
        "buslines.rou.xml",
        "DUERoutes/local.actuated.0.rou.xml",
        "DUERoutes/local.actuated.1.rou.xml",
        "DUERoutes/local.actuated.2.rou.xml",
        "transit.rou.xml",
    ])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scenario",required=True)
    ap.add_argument("--selection",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--seed",type=int,default=42)
    args=ap.parse_args()
    scenario=os.path.abspath(args.scenario)
    selection=parse_selection(args.selection)
    tls_ids=[r["tls_id"] for r in selection]
    alias={r["tls_id"]:r["agent_alias"] for r in selection}
    incoming=parse_net(os.path.join(scenario,"lust.net.xml"),set(tls_ids))

    try:
        import traci
    except ImportError:
        sumo_home=os.environ.get("SUMO_HOME","/usr/share/sumo")
        sys.path.append(os.path.join(sumo_home,"tools"))
        import traci

    cmd=[
        "sumo","-c",os.path.join(scenario,"due.actuated.sumocfg"),
        "--route-files",routes(),
        "--additional-files","vtypes.add.xml,busstops.add.xml",
        "--seed",str(args.seed),
        "--xml-validation","never",
        "--no-step-log","true",
        "--duration-log.statistics","true",
        "--time-to-teleport","600",
    ]
    print("Starting TraCI:", " ".join(cmd), flush=True)
    traci.start(cmd, label=f"dataset-{args.seed}")
    conn=traci.getConnection(f"dataset-{args.seed}")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)),exist_ok=True)
    fields=[
        "seed","time_s","hour","agent_alias","tls_id","phase",
        "veh_count","halting_count","mean_speed_mps","mean_occupancy_pct",
        "waiting_time_s","co2_mg_s","incoming_lane_count"
    ]
    n=0
    with open(args.output,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        while conn.simulation.getMinExpectedNumber()>0:
            conn.simulationStep()
            t=conn.simulation.getTime()
            if int(round(t)) % 10 != 0:
                continue
            for tl in tls_ids:
                ls=list(incoming.get(tl,()))
                veh=sum(conn.lane.getLastStepVehicleNumber(l) for l in ls)
                halt=sum(conn.lane.getLastStepHaltingNumber(l) for l in ls)
                occ=[conn.lane.getLastStepOccupancy(l) for l in ls]
                speeds=[]
                waits=0.0; co2=0.0
                for l in ls:
                    vc=conn.lane.getLastStepVehicleNumber(l)
                    sp=conn.lane.getLastStepMeanSpeed(l)
                    if vc>0 and sp>=0:
                        speeds.extend([sp]*vc)
                    try: waits += conn.lane.getWaitingTime(l)
                    except Exception: pass
                    try: co2 += conn.lane.getCO2Emission(l)
                    except Exception: pass
                mean_speed=sum(speeds)/len(speeds) if speeds else 0.0
                mean_occ=sum(occ)/len(occ) if occ else 0.0
                w.writerow({
                    "seed":args.seed,"time_s":t,"hour":int(t//3600),
                    "agent_alias":alias[tl],"tls_id":tl,
                    "phase":conn.trafficlight.getPhase(tl),
                    "veh_count":veh,"halting_count":halt,
                    "mean_speed_mps":mean_speed,"mean_occupancy_pct":mean_occ,
                    "waiting_time_s":waits,"co2_mg_s":co2,
                    "incoming_lane_count":len(ls)
                })
                n+=1
            if int(t)%3600==0:
                print(f"t={t:.0f}s rows={n}",flush=True)
    conn.close()
    print(f"Wrote {n} rows to {args.output}")

if __name__=="__main__":
    main()
