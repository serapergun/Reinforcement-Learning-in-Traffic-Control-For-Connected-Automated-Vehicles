#!/usr/bin/env python3
"""Generate SUMO 0.27 binary (.sbx) states for LuST operating windows.

Binary state files avoid the legacy XML vType round-trip parser that rejects
the bus cfmodel fields written by SUMO 0.27 itself.
"""
import argparse,csv,json,os,subprocess,hashlib

def windows(path):
    with open(path,newline="",encoding="utf-8") as f:
        return {r["condition"]:int(float(r["selected_hour"])) for r in csv.DictReader(f)}

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo",required=True);ap.add_argument("--scenario",required=True)
    ap.add_argument("--windows",required=True);ap.add_argument("--outdir",required=True)
    ap.add_argument("--seed",type=int,default=42)
    args=ap.parse_args()
    scenario=os.path.abspath(args.scenario);out=os.path.abspath(args.outdir);os.makedirs(out,exist_ok=True)
    w=windows(args.windows);conds=[c for c in ("Off-peak","AM","Lunch","PM") if c in w]
    times=[];files=[];meta={}
    for c in conds:
        t=w[c]*3600
        p=os.path.join(out,f"state_{c.replace('-','_')}.sbx")
        times.append(str(t));files.append(p);meta[c]={"hour":w[c],"time_s":t,"file":p}
    cmd=[os.path.abspath(args.sumo),"-c",os.path.join(scenario,"due.actuated.sumocfg"),
         "--seed",str(args.seed),"--save-state.times",",".join(times),
         "--save-state.files",",".join(files),"--end",str(max(map(int,times))+1),
         "--summary-output","/dev/null","--tripinfo-output","/dev/null","--log","/dev/null"]
    print("RUNNING"," ".join(cmd),flush=True)
    subprocess.run(cmd,cwd=scenario,check=True)
    for c in conds:
        p=meta[c]["file"]
        if not os.path.isfile(p) or os.path.getsize(p)==0:raise RuntimeError(f"missing state {p}")
        meta[c]["bytes"]=os.path.getsize(p);meta[c]["sha256"]=sha256(p)
    payload={"seed":args.seed,"states":meta,"command":cmd}
    with open(os.path.join(out,"binary_state_map.json"),"w") as f:json.dump(payload,f,indent=2)
    print(json.dumps(payload,indent=2))

if __name__=="__main__":
    main()
