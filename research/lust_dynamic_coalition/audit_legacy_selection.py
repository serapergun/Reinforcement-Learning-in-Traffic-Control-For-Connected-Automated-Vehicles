#!/usr/bin/env python3
import argparse,csv,json,math,os,sys

def rows(path):
    with open(path,newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def finite(x):
    try:return math.isfinite(float(x))
    except Exception:return False

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--dir",required=True);args=ap.parse_args()
    d=os.path.abspath(args.dir)
    req=["selected_9_tls.csv","selected_operating_windows.csv","tls_condition_metrics.csv",
         "tls_robust_ranking.csv","selection_metadata.json"]
    missing=[x for x in req if not os.path.isfile(os.path.join(d,x))]
    assert not missing,f"missing selection outputs: {missing}"

    sel=rows(os.path.join(d,"selected_9_tls.csv"))
    assert len(sel)==9,f"expected 9 selected TLS, got {len(sel)}"
    assert len({r["tls_id"] for r in sel})==9,"selected TLS IDs are not unique"
    assert [r["agent_alias"] for r in sel]==[f"A{i}" for i in range(1,10)],"aliases must be A1..A9"
    for r in sel:
        assert finite(r["CI_robust"]) and finite(r["x"]) and finite(r["y"])
        assert int(float(r["incoming_lanes"]))>0

    wins=rows(os.path.join(d,"selected_operating_windows.csv"))
    w={r["condition"]:int(float(r["selected_hour"])) for r in wins}
    assert set(w)=={"Off-peak","AM","Lunch","PM"},w
    assert 0<=w["Off-peak"]<=5
    assert 6<=w["AM"]<=10
    assert 11<=w["Lunch"]<=14
    assert 15<=w["PM"]<=20

    metrics=rows(os.path.join(d,"tls_condition_metrics.csv"))
    assert metrics,"empty condition metrics"
    metric_tls={r["tls_id"] for r in metrics}
    assert set(r["tls_id"] for r in sel).issubset(metric_tls)
    for k in ["Q_mean_max_jam_veh","O_mean_pct","TL_interval_halting_s","F_e1_end_vehicle_contrib","CI"]:
        assert all(finite(r[k]) for r in metrics),f"non-finite {k}"
    # Reject a degenerate detector run in which every congestion component is zero.
    totals={k:sum(float(r[k]) for r in metrics) for k in
            ["Q_mean_max_jam_veh","O_mean_pct","TL_interval_halting_s","F_e1_end_vehicle_contrib"]}
    assert totals["TL_interval_halting_s"]>0,"all E2 halting-duration measurements are zero"
    assert totals["F_e1_end_vehicle_contrib"]>0,"all E1 flow measurements are zero"

    ranking=rows(os.path.join(d,"tls_robust_ranking.csv"))
    assert len(ranking)>=9
    chosen={r["tls_id"] for r in ranking if int(float(r["selected_9"]))==1}
    assert chosen=={r["tls_id"] for r in sel},"ranking selection flags disagree with selected_9_tls.csv"

    meta=json.load(open(os.path.join(d,"selection_metadata.json")))
    report={"selected_tls":[r["tls_id"] for r in sel],"windows":w,"component_totals":totals,
            "selection_formula":meta.get("selection_formula"),"robust_formula":meta.get("robust_formula"),
            "status":"PASS"}
    out=os.path.join(d,"selection_audit.json")
    json.dump(report,open(out,"w"),indent=2)
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
