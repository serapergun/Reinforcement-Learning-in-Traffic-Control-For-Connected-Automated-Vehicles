#!/usr/bin/env python3
"""Collect the 10-s nine-TLS state dataset with SUMO 0.27-compatible TraCI."""
import argparse,csv,os,sys,xml.etree.ElementTree as ET
from collections import defaultdict

def parse_incoming(net_path,tls):
    root=ET.parse(net_path).getroot()
    lane_ids=set()
    for e in root.findall("edge"):
        if e.get("function"):continue
        for l in e.findall("lane"):lane_ids.add(l.get("id"))
    inc=defaultdict(set)
    for c in root.findall("connection"):
        tl=c.get("tl")
        if tl not in tls:continue
        lid=f"{c.get('from')}_{c.get('fromLane')}"
        if lid in lane_ids:inc[tl].add(lid)
    return {k:sorted(v) for k,v in inc.items()}

def load_selection(path):
    with open(path,newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    rows=sorted(rows,key=lambda r:int(r["agent_alias"][1:]))
    assert len(rows)==9 and len({r["tls_id"] for r in rows})==9
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo",required=True);ap.add_argument("--sumo-tools",required=True)
    ap.add_argument("--scenario",required=True);ap.add_argument("--selection",required=True)
    ap.add_argument("--output",required=True);ap.add_argument("--seed",type=int,default=42)
    args=ap.parse_args()
    sys.path.insert(0,os.path.abspath(args.sumo_tools))
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
    import traci
    from traci_compat import TraCICompat
    tc=TraCICompat(traci)

    scenario=os.path.abspath(args.scenario);sel=load_selection(args.selection)
    tls=[r["tls_id"] for r in sel];alias={r["tls_id"]:r["agent_alias"] for r in sel}
    incoming=parse_incoming(os.path.join(scenario,"lust.net.xml"),set(tls))
    assert all(incoming.get(t) for t in tls),[(t,len(incoming.get(t,[]))) for t in tls]

    cfg=os.path.join(scenario,"due.actuated.sumocfg")
    cmd=[os.path.abspath(args.sumo),"-c",cfg,
         "--begin","0","--end","86400","--seed",str(args.seed),
         "--summary-output","/dev/null","--tripinfo-output","/dev/null","--log","/dev/null"]
    print("RUNNING"," ".join(cmd),flush=True)
    tc.start(cmd)
    fields=["seed","time_s","hour","agent_alias","tls_id","phase","phase_state",
            "veh_count","halting_count","mean_speed_mps","mean_occupancy_pct",
            "waiting_time_s","co2_mg_s","incoming_lane_count"]
    os.makedirs(os.path.dirname(os.path.abspath(args.output)),exist_ok=True)
    rows=0
    try:
        with open(args.output,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
            while tc.min_expected()>0 and tc.time_s()<86400:
                tc.step();t=tc.time_s()
                if int(round(t))%10:continue
                for tl in tls:
                    ls=incoming[tl]
                    veh=halt=0;occ=[];weighted=0.;weight=0;wait=0.;co2=0.
                    for lane in ls:
                        n=tc.lane_vehicle_number(lane);veh+=n
                        halt+=tc.lane_halting_number(lane)
                        sp=tc.lane_speed(lane)
                        if n>0 and sp>=0:weighted+=n*sp;weight+=n
                        occ.append(tc.lane_occupancy(lane))
                        wait+=tc.lane_waiting(lane);co2+=tc.lane_co2(lane)
                    w.writerow({"seed":args.seed,"time_s":int(round(t)),"hour":int(t//3600),
                                "agent_alias":alias[tl],"tls_id":tl,"phase":tc.phase(tl),
                                "phase_state":tc.phase_state(tl),"veh_count":veh,"halting_count":halt,
                                "mean_speed_mps":weighted/max(weight,1),
                                "mean_occupancy_pct":sum(occ)/max(len(occ),1),
                                "waiting_time_s":wait,"co2_mg_s":co2,
                                "incoming_lane_count":len(ls)})
                    rows+=1
                if int(round(t))%3600==0:print(f"t={t:.0f}s rows={rows}",flush=True)
    finally:tc.close()

    assert rows==9*8640,f"expected 77760 rows, got {rows}"
    print(f"Wrote {rows} rows to {args.output}")

if __name__=="__main__":
    main()
