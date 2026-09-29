#!/usr/bin/env python3
import argparse, csv, gzip, json, math, os, subprocess, sys
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

def open_xml(path):
    return gzip.open(path, "rb") if str(path).endswith(".gz") else open(path, "rb")

def f(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def parse_net(net_path):
    tree = ET.parse(net_path)
    root = tree.getroot()
    junctions = {}
    lanes = {}
    edges = {}
    graph = defaultdict(set)
    for j in root.findall("junction"):
        jid = j.get("id")
        junctions[jid] = {
            "x": f(j.get("x"), math.nan),
            "y": f(j.get("y"), math.nan),
            "type": j.get("type", "")
        }
    for e in root.findall("edge"):
        if e.get("function"):
            continue
        eid = e.get("id")
        fr, to = e.get("from"), e.get("to")
        shape = ""
        lane_elems = e.findall("lane")
        if lane_elems:
            shape = lane_elems[0].get("shape", "")
        edges[eid] = {"from": fr, "to": to, "shape": shape}
        if fr and to:
            graph[fr].add(to)
            graph[to].add(fr)
        for lane in lane_elems:
            lanes[lane.get("id")] = {
                "length": f(lane.get("length")),
                "edge": eid,
                "shape": lane.get("shape", "")
            }

    tl_to_lanes = defaultdict(set)
    for c in root.findall("connection"):
        tl = c.get("tl")
        fr = c.get("from")
        fl = c.get("fromLane")
        if tl is None or fr is None or fl is None:
            continue
        lane_id = f"{fr}_{fl}"
        if lane_id in lanes:
            tl_to_lanes[tl].add(lane_id)
    return junctions, lanes, edges, graph, tl_to_lanes

def generate_e2(net_path, add_path, out_rel):
    junctions, lanes, edges, graph, tl_to_lanes = parse_net(net_path)
    additional = ET.Element("additional")
    det_to_tl = {}
    idx = 0
    for tl in sorted(tl_to_lanes):
        for lane_id in sorted(tl_to_lanes[tl]):
            length = lanes[lane_id]["length"]
            if length <= 1:
                continue
            detector_length = min(250.0, max(5.0, length - 0.2))
            det_id = f"E2_{idx}"
            idx += 1
            ET.SubElement(additional, "laneAreaDetector", {
                "id": det_id,
                "lane": lane_id,
                "pos": f"{-detector_length:.2f}",
                "endPos": "-0.10",
                "friendlyPos": "true",
                "period": "300",
                "file": out_rel,
                "timeThreshold": "1.0",
                "speedThreshold": "1.39",
                "jamThreshold": "10.0"
            })
            det_to_tl[det_id] = tl
    ET.indent(additional, space="  ")
    ET.ElementTree(additional).write(add_path, encoding="utf-8", xml_declaration=True)
    return junctions, lanes, edges, graph, tl_to_lanes, det_to_tl

def run_sumo(scenario, results):
    cfg = os.path.join(scenario, "due.actuated.sumocfg")
    # LuST v2.0 configuration uses whitespace-separated route-files, which modern
    # SUMO interprets as a single filename. Override with the exact official files
    # using the current comma-separated syntax; no routes are modified.
    route_files = ",".join([
        "buslines.rou.xml",
        "DUERoutes/local.actuated.0.rou.xml",
        "DUERoutes/local.actuated.1.rou.xml",
        "DUERoutes/local.actuated.2.rou.xml",
        "transit.rou.xml",
    ])
    cmd = [
        "sumo", "-c", cfg,
        "--route-files", route_files,
        "--additional-files", "vtypes.add.xml,busstops.add.xml,study_e2.add.xml",
        "--summary-output", os.path.relpath(os.path.join(results, "study_summary.xml.gz"), scenario),
        "--tripinfo-output", os.path.relpath(os.path.join(results, "study_tripinfo.xml.gz"), scenario),
        "--device.emissions.probability", "1",
        "--tripinfo-output.write-unfinished", "true",
        "--seed", "42",
        "--begin", "0",
        "--end", "86400",
        "--xml-validation", "never",
        "--no-step-log", "true",
        "--duration-log.statistics", "true",
        "--log", os.path.relpath(os.path.join(results, "sumo.log"), scenario),
    ]
    print("RUNNING:", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=scenario, check=True)
    return cmd

def parse_tripinfo(path):
    n = 0
    completed = 0
    sums = defaultdict(float)
    co2_mg = 0.0
    with open_xml(path) as fh:
        for ev, elem in ET.iterparse(fh, events=("end",)):
            if elem.tag == "tripinfo":
                n += 1
                if elem.get("arrival") not in (None, "-1.00", "-1"):
                    completed += 1
                for key in ["duration", "waitingTime", "timeLoss", "routeLength", "departDelay"]:
                    sums[key] += f(elem.get(key))
                em = elem.find("emissions")
                if em is not None:
                    co2_mg += f(em.get("CO2_abs"))
                elem.clear()
    denom = max(n, 1)
    return {
        "reported_tripinfos": n,
        "completed_trips": completed,
        "ATT_s": sums["duration"] / denom,
        "AWT_s": sums["waitingTime"] / denom,
        "ATL_s": sums["timeLoss"] / denom,
        "mean_route_length_m": sums["routeLength"] / denom,
        "mean_depart_delay_s": sums["departDelay"] / denom,
        "CO2_kg": co2_mg / 1e6,
        "throughput_veh_per_h_completed": completed / 24.0,
    }

def parse_e2(path, det_to_tl):
    hourly_network = defaultdict(float)
    by_hour_tls = defaultdict(lambda: defaultdict(lambda: {
        "q_sum": 0.0, "o_sum": 0.0, "o_n": 0,
        "tl_sum": 0.0, "f_sum": 0.0, "speed_sum": 0.0, "speed_n": 0,
        "intervals": 0
    }))
    with open_xml(path) as fh:
        for ev, elem in ET.iterparse(fh, events=("end",)):
            if elem.tag != "interval":
                continue
            did = elem.get("id")
            if did not in det_to_tl:
                elem.clear()
                continue
            begin = f(elem.get("begin"))
            hour = int(begin // 3600)
            tl = det_to_tl[did]
            entered = f(elem.get("nVehEntered"))
            q = f(elem.get("meanMaxJamLengthInVehicles"))
            occ = f(elem.get("meanOccupancy"))
            nseen = f(elem.get("nVehSeen"))
            mtl = f(elem.get("meanTimeLoss"))
            spd = f(elem.get("meanSpeed"), math.nan)
            d = by_hour_tls[hour][tl]
            d["q_sum"] += q
            d["o_sum"] += occ
            d["o_n"] += 1
            d["tl_sum"] += mtl * nseen
            d["f_sum"] += entered
            if not math.isnan(spd) and spd >= 0:
                d["speed_sum"] += spd
                d["speed_n"] += 1
            d["intervals"] += 1
            hourly_network[hour] += entered
            elem.clear()
    return hourly_network, by_hour_tls

def select_hours(hourly_network):
    def choose(hrs, mode):
        vals = [(h, hourly_network.get(h, 0.0)) for h in hrs]
        return min(vals, key=lambda x:x[1]) if mode=="min" else max(vals, key=lambda x:x[1])
    return {
        "Off-peak": choose(range(0,6), "min"),
        "AM": choose(range(6,11), "max"),
        "Lunch": choose(range(11,15), "max"),
        "PM": choose(range(15,21), "max"),
    }

def minmax(vals):
    vals = list(vals)
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return [0.0 for _ in vals]
    return [(v-lo)/(hi-lo) for v in vals]

def compute_condition_metrics(by_hour_tls, selected_hours):
    rows = []
    ci_by_cond = {}
    for cond, (hour, _) in selected_hours.items():
        raw = []
        for tl, d in by_hour_tls[hour].items():
            intervals = max(d["intervals"], 1)
            raw.append({
                "condition": cond, "hour": hour, "tls_id": tl,
                "Q_mean_jam_veh": d["q_sum"]/intervals,
                "O_mean_pct": d["o_sum"]/max(d["o_n"],1),
                "TL_total_s": d["tl_sum"],
                "F_entered": d["f_sum"],
                "mean_speed_mps": d["speed_sum"]/max(d["speed_n"],1),
            })
        if not raw:
            continue
        qn = minmax([r["Q_mean_jam_veh"] for r in raw])
        on = minmax([r["O_mean_pct"] for r in raw])
        tln = minmax([r["TL_total_s"] for r in raw])
        fn = minmax([r["F_entered"] for r in raw])
        ci_by_cond[cond] = {}
        for i,r in enumerate(raw):
            r["Q_norm"] = qn[i]; r["O_norm"] = on[i]; r["TL_norm"] = tln[i]; r["F_norm"] = fn[i]
            r["CI"] = 0.30*qn[i] + 0.25*on[i] + 0.30*tln[i] + 0.15*fn[i]
            ci_by_cond[cond][r["tls_id"]] = r["CI"]
            rows.append(r)
    return rows, ci_by_cond

def shortest_hops(graph, src, max_hops=5):
    q = deque([(src,0)])
    seen = {src}
    dist = {src:0}
    while q:
        u,d = q.popleft()
        if d >= max_hops:
            continue
        for v in graph.get(u,()):
            if v not in seen:
                seen.add(v); dist[v]=d+1; q.append((v,d+1))
    return dist

def select_connected_tls(robust_scores, graph, n=9, max_hops=4):
    ranked = sorted(robust_scores, key=robust_scores.get, reverse=True)
    if not ranked:
        return []
    selected = [ranked[0]]
    remaining = set(ranked[1:])
    while remaining and len(selected) < n:
        eligible = []
        for cand in remaining:
            ok = False
            for s in selected:
                d = shortest_hops(graph, s, max_hops).get(cand)
                if d is not None and d <= max_hops:
                    ok = True
                    break
            if ok:
                eligible.append(cand)
        pool = eligible if eligible else list(remaining)
        best = max(pool, key=lambda x: robust_scores[x])
        selected.append(best)
        remaining.remove(best)
    return selected

def write_csv(path, rows, fields=None):
    if not rows:
        return
    if fields is None:
        fields = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def plot_network(path_png, path_pdf, junctions, edges, selected, robust):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9,8))
    xs=[]; ys=[]
    for e in edges.values():
        shape = e.get("shape","")
        pts=[]
        if shape:
            for p in shape.split():
                try:
                    x,y = map(float,p.split(",")[:2]); pts.append((x,y))
                except Exception:
                    pass
        if len(pts)>=2:
            ax.plot([p[0] for p in pts],[p[1] for p in pts], linewidth=0.3, alpha=0.35)
    for i,tl in enumerate(selected,1):
        j = junctions.get(tl,{})
        x,y = j.get("x",math.nan), j.get("y",math.nan)
        if math.isnan(x) or math.isnan(y):
            continue
        xs.append(x); ys.append(y)
        ax.scatter([x],[y],s=55,zorder=4)
        ax.text(x,y,f" A{i}\n{tl}",fontsize=7,va="bottom",ha="left")
    if xs:
        pad=max(max(xs)-min(xs),max(ys)-min(ys),1000)*0.18
        ax.set_xlim(min(xs)-pad,max(xs)+pad); ax.set_ylim(min(ys)-pad,max(ys)+pad)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("SUMO x-coordinate (m)")
    ax.set_ylabel("SUMO y-coordinate (m)")
    ax.set_title("LuST v2.0: selected nine traffic-signal agents from measured baseline congestion")
    fig.tight_layout()
    fig.savefig(path_png,dpi=300,bbox_inches="tight")
    fig.savefig(path_pdf,bbox_inches="tight")
    plt.close(fig)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--results", required=True)
    args=ap.parse_args()
    scenario=os.path.abspath(args.scenario)
    results=os.path.abspath(args.results)
    os.makedirs(results,exist_ok=True)
    net=os.path.join(scenario,"lust.net.xml")
    add=os.path.join(scenario,"study_e2.add.xml")
    e2_rel=os.path.relpath(os.path.join(results,"study_e2.xml.gz"),scenario)

    junctions, lanes, edges, graph, tl_to_lanes, det_to_tl = generate_e2(net,add,e2_rel)
    with open(os.path.join(results,"detector_map.json"),"w") as f:
        json.dump(det_to_tl,f,indent=2)

    cmd=run_sumo(scenario,results)

    trip=parse_tripinfo(os.path.join(results,"study_tripinfo.xml.gz"))
    hourly, by_hour_tls=parse_e2(os.path.join(results,"study_e2.xml.gz"),det_to_tl)
    selected_hours=select_hours(hourly)
    cond_rows, ci_by_cond=compute_condition_metrics(by_hour_tls,selected_hours)

    all_tls=set()
    for m in ci_by_cond.values(): all_tls.update(m)
    robust={}
    for tl in all_tls:
        robust[tl]=0.4*ci_by_cond.get("AM",{}).get(tl,0)+0.2*ci_by_cond.get("Lunch",{}).get(tl,0)+0.4*ci_by_cond.get("PM",{}).get(tl,0)
    ranking=sorted(robust,key=robust.get,reverse=True)
    selected=select_connected_tls(robust,graph,n=9,max_hops=4)

    rank_rows=[]
    for rank,tl in enumerate(ranking,1):
        j=junctions.get(tl,{})
        rank_rows.append({
            "rank":rank,"tls_id":tl,"CI_robust":robust[tl],
            "x":j.get("x"),"y":j.get("y"),
            "incoming_lanes":len(tl_to_lanes.get(tl,[])),
            "selected_9": int(tl in selected)
        })

    sel_rows=[]
    for i,tl in enumerate(selected,1):
        j=junctions.get(tl,{})
        sel_rows.append({
            "agent_alias":f"A{i}","tls_id":tl,"CI_robust":robust.get(tl,0),
            "x":j.get("x"),"y":j.get("y"),
            "incoming_lanes":len(tl_to_lanes.get(tl,[]))
        })

    hour_rows=[{"hour":h,"signal_demand_count":hourly.get(h,0.0)} for h in range(24)]
    condition_rows=[{"condition":k,"selected_hour":v[0],"signal_demand_count":v[1]} for k,v in selected_hours.items()]
    write_csv(os.path.join(results,"hourly_signal_demand.csv"),hour_rows)
    write_csv(os.path.join(results,"selected_operating_windows.csv"),condition_rows)
    write_csv(os.path.join(results,"tls_condition_metrics.csv"),cond_rows)
    write_csv(os.path.join(results,"tls_robust_ranking.csv"),rank_rows)
    write_csv(os.path.join(results,"selected_9_tls.csv"),sel_rows)
    write_csv(os.path.join(results,"baseline_metrics.csv"),[trip])

    plot_network(os.path.join(results,"Figure2_real_LuST_selected_network.png"),
                 os.path.join(results,"Figure2_real_LuST_selected_network.pdf"),
                 junctions,edges,selected,robust)

    sumo_version=subprocess.check_output(["sumo","--version"],text=True).splitlines()[0]
    try:
        lust_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=os.path.dirname(scenario),text=True).strip()
    except Exception:
        lust_commit=""
    metadata={
        "sumo_version":sumo_version,
        "lust_commit":lust_commit,
        "lust_expected_tag":"v2.0",
        "seed":42,
        "e2_period_s":300,
        "e2_approach_length_m":250,
        "congestion_index":"0.30*Q_norm + 0.25*O_norm + 0.30*TL_norm + 0.15*F_norm",
        "robust_index":"0.40*CI_AM + 0.20*CI_Lunch + 0.40*CI_PM",
        "selected_hours":selected_hours,
        "selected_tls":selected,
        "command":cmd,
        "baseline_metrics":trip
    }
    with open(os.path.join(results,"run_metadata.json"),"w") as f:
        json.dump(metadata,f,indent=2)
    print(json.dumps(metadata,indent=2))

if __name__=="__main__":
    main()
