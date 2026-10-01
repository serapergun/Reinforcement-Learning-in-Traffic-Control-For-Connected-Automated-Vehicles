#!/usr/bin/env python3
"""Prepare reproducible full-history LuST branch states with SUMO 0.27.0.

Each seed is simulated from t=0 under the official native actuated controller.
For every selected operating condition, a SUMO state is saved 300 s before the
control window. Downstream RL/reference branches load the exact same file, so
peak-hour experiments retain the real network history instead of starting an
empty network at the target hour.
"""
import argparse,csv,hashlib,json,os,sys

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def read_windows(path):
    with open(path,newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    return {r["condition"]:int(float(r["selected_hour"])) for r in rows}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo",required=True)
    ap.add_argument("--sumo-tools",required=True)
    ap.add_argument("--scenario",required=True)
    ap.add_argument("--windows",required=True)
    ap.add_argument("--outdir",required=True)
    ap.add_argument("--seeds",default="4101,4102,9001,9002,9003")
    ap.add_argument("--prehistory-s",type=int,default=300)
    args=ap.parse_args()

    sys.path.insert(0,os.path.abspath(args.sumo_tools))
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
    import traci
    from traci_compat import TraCICompat
    tc=TraCICompat(traci)

    os.makedirs(args.outdir,exist_ok=True)
    scenario=os.path.abspath(args.scenario)
    windows=read_windows(args.windows)
    targets={c:max(0,h*3600-args.prehistory_s) for c,h in windows.items()}
    ordered=sorted(targets.items(),key=lambda x:x[1])
    audit=[]

    for seed in [int(x) for x in args.seeds.split(",") if x.strip()]:
        cmd=[os.path.abspath(args.sumo),"-c",os.path.join(scenario,"due.actuated.sumocfg"),
             "--begin","0","--end","86400","--seed",str(seed),
             "--summary-output","/dev/null","--tripinfo-output","/dev/null","--log","/dev/null"]
        print("START",seed," ".join(cmd),flush=True)
        tc.start(cmd)
        try:
            for cond,target in ordered:
                while tc.time_s()<target and tc.min_expected()>0:
                    tc.step()
                now=tc.time_s()
                assert abs(now-target)<1e-9,(seed,cond,now,target)
                path=os.path.abspath(os.path.join(args.outdir,f"state_seed{seed}_{cond}.xml"))
                traci.simulation.saveState(path)
                record={
                    "seed":seed,"condition":cond,"state_time_s":now,
                    "control_start_s":windows[cond]*3600,
                    "prehistory_s":args.prehistory_s,
                    "vehicle_count":len(traci.vehicle.getIDList()),
                    "min_expected":tc.min_expected(),
                    "state_file":os.path.basename(path),
                    "sha256":sha256(path),
                }
                audit.append(record);print(record,flush=True)
        finally:
            tc.close()

    with open(os.path.join(args.outdir,"state_audit.csv"),"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(audit[0].keys()));w.writeheader();w.writerows(audit)
    with open(os.path.join(args.outdir,"state_manifest.json"),"w") as f:
        json.dump({"windows":windows,"targets":targets,"seeds":sorted(set(r["seed"] for r in audit)),
                   "records":audit},f,indent=2)

if __name__=="__main__":
    main()
