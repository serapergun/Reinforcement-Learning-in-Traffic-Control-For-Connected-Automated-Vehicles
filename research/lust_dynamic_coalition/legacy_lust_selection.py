#!/usr/bin/env python3
"""Select nine LuST TLS agents using a SUMO-0.27-compatible baseline.

The script keeps the official LuST network and demand unchanged. It adds
read-only E2 approach detectors and combines them with the official E1 detector
outputs to compute the manuscript congestion index:
  CI = 0.30 Q_norm + 0.25 O_norm + 0.30 TL_norm + 0.15 F_norm

Q  : mean maximum queue length in vehicles from E2 detectors
O  : mean E2 occupancy
TL : interval halting-duration accumulation from E2 detectors
F  : approach vehicle contribution count from official E1 end detectors

The selected operating hours are the highest aggregate controlled-approach
halting-duration hours inside the AM/Lunch/PM windows and the lowest in the
00:00-06:00 off-peak window.
"""
import argparse, csv, json, math, os, subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
import numpy as np

def f(x, default=0.0):
    try: return float(x)
    except Exception: return default

def parse_net(path):
    root=ET.parse(path).getroot()
    junctions={}
    lanes={}
    graph=defaultdict(set)
    for j in root.findall("junction"):
        junctions[j.get("id")]={"x":f(j.get("x"),math.nan),"y":f(j.get("y"),math.nan),"type":j.get("type","")}
    for e in root.findall("edge"):
        if e.get("function"): continue
        fr,to=e.get("from"),e.get("to")
        if fr and to:
            graph[fr].add(to);graph[to].add(fr)
        for l in e.findall("lane"):
            lanes[l.get("id")]={"length":f(l.get("length")),"edge":e.get("id")}
    incoming=defaultdict(set)
    for c in root.findall("connection"):
        tl=c.get("tl")
        if not tl: continue
        lid=f"{c.get('from')}_{c.get('fromLane')}"
        if lid in lanes: incoming[tl].add(lid)
    return junctions,lanes,graph,incoming

def make_e2(net_path, out_additional, out_xml):
    junctions,lanes,graph,incoming=parse_net(net_path)
    root=ET.Element("additional")
    detmap={}
    idx=0
    for tl in sorted(incoming):
        for lane in sorted(incoming[tl]):
            L=lanes[lane]["length"]
            if L<=1: continue
            detlen=min(250.0,max(5.0,L-0.2))
            pos=max(0.0,L-detlen-0.1)
            did=f"LEGACY_E2_{idx}"
            idx+=1
            ET.SubElement(root,"laneAreaDetector",{
                "id":did,"lane":lane,"pos":f"{pos:.2f}","length":f"{detlen:.2f}",
                "freq":"300","file":os.path.abspath(out_xml),
                "timeThreshold":"1","speedThreshold":"1.39","jamThreshold":"10",
                "friendlyPos":"true",
            })
            detmap[did]=tl
    ET.indent(root,space="  ")
    ET.ElementTree(root).write(out_additional,encoding="utf-8",xml_declaration=True)
    return junctions,lanes,graph,incoming,detmap

def make_config(original, derived, e2_add, results):
    tree=ET.parse(original);root=tree.getroot()
    add=root.find("./input/additional-files")
    cur=add.get("value","")
    if os.path.basename(e2_add) not in cur.split():
        add.set("value",cur+" "+os.path.basename(e2_add))
    root.find("./output/summary-output").set("value",os.path.abspath(os.path.join(results,"legacy_selection.summary.xml")))
    root.find("./output/tripinfo-output").set("value",os.path.abspath(os.path.join(results,"legacy_selection.tripinfo.xml")))
    log=root.find("./report/log")
    if log is not None: log.set("value",os.path.abspath(os.path.join(results,"legacy_selection.log")))
    ET.indent(root,space="  ")
    tree.write(derived,encoding="utf-8",xml_declaration=True)

def parse_e2(path,detmap):
    hourly=defaultdict(lambda:defaultdict(lambda:defaultdict(float)))
    counts=defaultdict(lambda:defaultdict(lambda:defaultdict(int)))
    for ev,e in ET.iterparse(path,events=("end",)):
        if e.tag!="interval": continue
        did=e.get("id")
        tl=detmap.get(did)
        if tl is None: e.clear(); continue
        h=int(f(e.get("begin"))//3600)
        vals={
            "Q":f(e.get("meanMaxJamLengthInVehicles")),
            "O":f(e.get("meanOccupancy")),
            "TL":f(e.get("intervalHaltingDurationSum")),
            "N":f(e.get("meanVehicleNumber")),
        }
        for k,v in vals.items():
            if k=="TL":
                hourly[h][tl][k]+=v
            else:
                hourly[h][tl][k]+=v
                counts[h][tl][k]+=1
        e.clear()
    for h in hourly:
        for tl in hourly[h]:
            for k in ("Q","O","N"):
                hourly[h][tl][k]/=max(counts[h][tl][k],1)
    return hourly

def parse_e1(paths):
    out=defaultdict(lambda:defaultdict(float))
    for path in paths:
        if not os.path.isfile(path): continue
        for ev,e in ET.iterparse(path,events=("end",)):
            if e.tag!="interval": continue
            did=e.get("id","")
            if "_E_" not in did:
                e.clear();continue
            tl=did.split("_E_",1)[1]
            h=int(f(e.get("begin"))//3600)
            out[h][tl]+=f(e.get("nVehContrib"))
            e.clear()
    return out

def select_hours(hourly):
    score={}
    for h in range(24):
        score[h]=sum(d.get("TL",0.0) for d in hourly.get(h,{}).values())
    def pick(hrs,highest=True):
        vals=[(h,score.get(h,0.0)) for h in hrs]
        return (max if highest else min)(vals,key=lambda x:x[1])
    return {
        "Off-peak":pick(range(0,6),False),
        "AM":pick(range(6,11),True),
        "Lunch":pick(range(11,15),True),
        "PM":pick(range(15,21),True),
    },score

def norm(vals):
    a=np.asarray(vals,float)
    if len(a)==0:return a
    lo,hi=float(a.min()),float(a.max())
    if hi-lo<1e-12:return np.zeros_like(a)
    return (a-lo)/(hi-lo)

def condition_ci(hourly,e1,selected_hours):
    rows=[];ci={}
    for cond,(h,_) in selected_hours.items():
        tls=sorted(hourly.get(h,{}))
        raw=[]
        for tl in tls:
            d=hourly[h][tl]
            raw.append({"condition":cond,"hour":h,"tls_id":tl,
                        "Q_mean_max_jam_veh":d.get("Q",0.0),
                        "O_mean_pct":d.get("O",0.0),
                        "TL_interval_halting_s":d.get("TL",0.0),
                        "F_e1_end_vehicle_contrib":e1.get(h,{}).get(tl,0.0)})
        if not raw:continue
        q=norm([r["Q_mean_max_jam_veh"] for r in raw])
        o=norm([r["O_mean_pct"] for r in raw])
        tlv=norm([r["TL_interval_halting_s"] for r in raw])
        fl=norm([r["F_e1_end_vehicle_contrib"] for r in raw])
        ci[cond]={}
        for i,r in enumerate(raw):
            r.update({"Q_norm":q[i],"O_norm":o[i],"TL_norm":tlv[i],"F_norm":fl[i]})
            r["CI"]=.30*q[i]+.25*o[i]+.30*tlv[i]+.15*fl[i]
            ci[cond][r["tls_id"]]=r["CI"];rows.append(r)
    return rows,ci

def hops(graph,src,max_hops=5):
    q=deque([(src,0)]);seen={src};d={src:0}
    while q:
        u,k=q.popleft()
        if k>=max_hops:continue
        for v in graph.get(u,()):
            if v not in seen:
                seen.add(v);d[v]=k+1;q.append((v,k+1))
    return d

def select_connected(scores,graph,n=9,max_hops=4):
    ranked=sorted(scores,key=scores.get,reverse=True)
    if not ranked:return []
    chosen=[ranked[0]];remain=set(ranked[1:])
    while remain and len(chosen)<n:
        elig=[c for c in remain if any(hops(graph,s,max_hops).get(c,999)<=max_hops for s in chosen)]
        pool=elig if elig else list(remain)
        best=max(pool,key=scores.get);chosen.append(best);remain.remove(best)
    return chosen

def write_csv(path,rows):
    if not rows:return
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)

def plot_network(path,junctions,graph,selected):
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,8))
    seen=set()
    for u,nbrs in graph.items():
        for v in nbrs:
            key=tuple(sorted((u,v)))
            if key in seen:continue
            seen.add(key)
            if u in junctions and v in junctions:
                ax.plot([junctions[u]["x"],junctions[v]["x"]],
                        [junctions[u]["y"],junctions[v]["y"]],linewidth=.25,alpha=.25)
    xs=[];ys=[]
    for i,tl in enumerate(selected,1):
        j=junctions.get(tl)
        if not j:continue
        x,y=j["x"],j["y"];xs.append(x);ys.append(y)
        ax.scatter([x],[y],s=55,zorder=3);ax.text(x,y,f" A{i}\n{tl}",fontsize=7)
    if xs:
        pad=max(max(xs)-min(xs),max(ys)-min(ys),1000)*.18
        ax.set_xlim(min(xs)-pad,max(xs)+pad);ax.set_ylim(min(ys)-pad,max(ys)+pad)
    ax.set_aspect("equal");ax.set_xlabel("SUMO x-coordinate (m)");ax.set_ylabel("SUMO y-coordinate (m)")
    ax.set_title("LuST v2.0 selected nine TLS agents (SUMO 0.27-compatible baseline)")
    fig.tight_layout();fig.savefig(path,dpi=300,bbox_inches="tight");plt.close(fig)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo",required=True);ap.add_argument("--scenario",required=True);ap.add_argument("--results",required=True)
    args=ap.parse_args()
    scenario=os.path.abspath(args.scenario);results=os.path.abspath(args.results);os.makedirs(results,exist_ok=True)
    e2add=os.path.join(scenario,"legacy_study_e2.add.xml")
    e2out=os.path.join(results,"legacy_e2_output.xml")
    junctions,lanes,graph,incoming,detmap=make_e2(os.path.join(scenario,"lust.net.xml"),e2add,e2out)
    derived=os.path.join(scenario,"legacy_selection.sumocfg")
    make_config(os.path.join(scenario,"due.actuated.sumocfg"),derived,e2add,results)
    # Remove detector outputs from any prior run so provenance is unambiguous.
    for fn in ("e1_begin_output.xml","e1_end_output.xml"):
        p=os.path.join(scenario,fn)
        if os.path.exists(p):os.remove(p)
    cmd=[os.path.abspath(args.sumo),"-c",derived]
    print("RUNNING"," ".join(cmd),flush=True)
    subprocess.run(cmd,cwd=scenario,check=True)

    hourly=parse_e2(e2out,detmap)
    e1=parse_e1([os.path.join(scenario,"e1_begin_output.xml"),os.path.join(scenario,"e1_end_output.xml")])
    windows,hour_score=select_hours(hourly)
    rows,ci=condition_ci(hourly,e1,windows)
    all_tls=set().union(*(set(v) for v in ci.values()))
    robust={tl:.4*ci.get("AM",{}).get(tl,0)+.2*ci.get("Lunch",{}).get(tl,0)+.4*ci.get("PM",{}).get(tl,0) for tl in all_tls}
    selected=select_connected(robust,graph,9,4)

    rank=[]
    for k,tl in enumerate(sorted(robust,key=robust.get,reverse=True),1):
        j=junctions.get(tl,{})
        rank.append({"rank":k,"tls_id":tl,"CI_robust":robust[tl],"x":j.get("x"),"y":j.get("y"),
                     "incoming_lanes":len(incoming.get(tl,[])),"selected_9":int(tl in selected)})
    selected_rows=[]
    for i,tl in enumerate(selected,1):
        j=junctions.get(tl,{})
        selected_rows.append({"agent_alias":f"A{i}","tls_id":tl,"CI_robust":robust.get(tl,0),
                              "x":j.get("x"),"y":j.get("y"),"incoming_lanes":len(incoming.get(tl,[]))})
    winrows=[{"condition":c,"selected_hour":v[0],"aggregate_halting_duration_s":v[1]} for c,v in windows.items()]
    hourrows=[{"hour":h,"aggregate_halting_duration_s":hour_score[h]} for h in range(24)]
    write_csv(os.path.join(results,"tls_condition_metrics.csv"),rows)
    write_csv(os.path.join(results,"tls_robust_ranking.csv"),rank)
    write_csv(os.path.join(results,"selected_9_tls.csv"),selected_rows)
    write_csv(os.path.join(results,"selected_operating_windows.csv"),winrows)
    write_csv(os.path.join(results,"hourly_congestion_profile.csv"),hourrows)
    plot_network(os.path.join(results,"Figure2_legacy_LuST_selected_network.png"),junctions,graph,selected)
    meta={"selection_formula":"0.30 Q + 0.25 O + 0.30 TL + 0.15 F",
          "Q":"E2 meanMaxJamLengthInVehicles","O":"E2 meanOccupancy",
          "TL":"E2 intervalHaltingDurationSum","F":"official E1 end-detector nVehContrib",
          "robust_formula":"0.40 AM + 0.20 Lunch + 0.40 PM",
          "command":cmd,"selected_tls":selected,"windows":windows}
    with open(os.path.join(results,"selection_metadata.json"),"w") as f:json.dump(meta,f,indent=2)
    print(json.dumps(meta,indent=2))

if __name__=="__main__":
    main()
