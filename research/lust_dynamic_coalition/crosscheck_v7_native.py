#!/usr/bin/env python3
"""Independent-run native SUMO reproducibility check for V7 paired experiment."""
import argparse,csv,json,math,pathlib
METRICS=("mean_halting_vehicles","mean_waiting_time_lane_sum_s",
         "CO2_kg_selected_approaches","arrived_vehicles_global",
         "decision_steps","mask_eligible_slots")
def load(path):
    with open(path,encoding="utf-8",newline="") as f: return list(csv.DictReader(f))
def evaluate(paired,independent,rtol=1e-6,atol=1e-7):
    a=[r for r in load(paired) if r["coalition"]=="native"]
    b=load(independent)
    def index(rows):
        out={}
        for row in rows:
            key=(row["condition"],int(row["seed"]))
            if key in out: raise ValueError("Duplicate native reference: "+str(key))
            out[key]=row
        return out
    x=index(a); y=index(b)
    if set(x)!=set(y) or not x:
        raise ValueError("Independent native rows do not match paired native condition/seed coverage")
    deviations=[]
    for key in sorted(x):
        for metric in METRICS:
            observed=float(x[key][metric]); expected=float(y[key][metric])
            if not all(map(math.isfinite,(observed,expected))):
                raise ValueError("Nonfinite metric for "+str(key)+"/"+metric)
            close=math.isclose(observed,expected,rel_tol=rtol,abs_tol=atol)
            deviations.append(dict(condition=key[0],seed=key[1],metric=metric,
                                   paired=observed,independent=expected,consistent=close,
                                   absolute_difference=abs(observed-expected)))
    failed=[d for d in deviations if not d["consistent"]]
    return dict(status="PASS" if not failed else "FAIL",
                comparison="independent two-run native-actuated LuST replay equivalence",
                condition_seed_pairs=len(x),metrics_per_pair=len(METRICS),
                violations=failed,all_compared=deviations,rtol=rtol,atol=atol)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--paired",required=True);p.add_argument("--independent",required=True)
    p.add_argument("--output",required=True);p.add_argument("--rtol",type=float,default=1e-6)
    args=p.parse_args()
    result=evaluate(args.paired,args.independent,args.rtol)
    target=pathlib.Path(args.output);target.parent.mkdir(exist_ok=True,parents=True)
    target.write_text(json.dumps(result,indent=2),encoding="utf-8")
    if result["violations"]:raise SystemExit("FAIL: native replay mismatch: "+str(result["violations"]))
    print("PASS independent native replication across",result["condition_seed_pairs"],"paired runs")
if __name__=="__main__":main()
