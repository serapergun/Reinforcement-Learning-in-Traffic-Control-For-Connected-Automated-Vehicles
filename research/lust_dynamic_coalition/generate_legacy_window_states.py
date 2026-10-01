#!/usr/bin/env python3
"""Generate reproducible SUMO 0.27 saved states for selected LuST operating windows."""
import argparse,csv,json,os,subprocess

def read_windows(path):
    with open(path,newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    return {r["condition"]:int(float(r["selected_hour"])) for r in rows}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo",required=True)
    ap.add_argument("--scenario",required=True)
    ap.add_argument("--windows",required=True)
    ap.add_argument("--outdir",required=True)
    ap.add_argument("--warmup-s",type=int,default=300)
    ap.add_argument("--seed",type=int,default=42)
    args=ap.parse_args()
    scenario=os.path.abspath(args.scenario);outdir=os.path.abspath(args.outdir)
    os.makedirs(outdir,exist_ok=True)
    wins=read_windows(args.windows)
    order=[c for c in ("Off-peak","AM","Lunch","PM") if c in wins]
    times=[];files=[];mapping={}
    for cond in order:
        t=max(0,wins[cond]*3600-args.warmup_s)
        p=os.path.join(outdir,f"state_{cond.replace('-','_')}.xml")
        times.append(str(t));files.append(p);mapping[cond]={"hour":wins[cond],"state_time_s":t,"file":p}
    cmd=[os.path.abspath(args.sumo),"-c",os.path.join(scenario,"due.actuated.sumocfg"),
         "--seed",str(args.seed),
         "--save-state.times",",".join(times),
         "--save-state.files",",".join(files),
         "--end",str(max(int(x) for x in times)+1),
         "--summary-output","/dev/null","--tripinfo-output","/dev/null","--log","/dev/null"]
    print("RUNNING"," ".join(cmd),flush=True)
    subprocess.run(cmd,cwd=scenario,check=True)
    missing=[p for p in files if not os.path.isfile(p) or os.path.getsize(p)==0]
    if missing: raise RuntimeError(f"Missing saved states: {missing}")
    with open(os.path.join(outdir,"state_map.json"),"w") as f:json.dump({"seed":args.seed,"warmup_s":args.warmup_s,"states":mapping},f,indent=2)
    print(json.dumps(mapping,indent=2))

if __name__=="__main__":
    main()
