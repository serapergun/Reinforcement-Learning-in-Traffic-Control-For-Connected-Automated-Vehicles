#!/usr/bin/env python3
"""Build Phase3A multi-seed robustness table/figure from focal coalition values."""
import argparse,csv,os
from collections import defaultdict
import numpy as np

FOCAL=("A1+A3+A4","A3+A4+A7+A8+A9","grand")

def norm(s):
    s=s.strip()
    return "grand" if s=="grand" else "+".join(sorted(s.replace(",","+").split("+"),key=lambda z:int(z[1:])))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("seedwise_csv"); ap.add_argument("--outdir",default="phase3a_analysis")
    args=ap.parse_args(); os.makedirs(args.outdir,exist_ok=True)
    rows=list(csv.DictReader(open(args.seedwise_csv,newline="")))
    d=defaultdict(list); byseed=defaultdict(dict)
    for r in rows:
        k=norm(r["coalition"]); v=float(r["v_balanced"] if "v_balanced" in r else r["utility"])
        seed=int(r["seed"]); d[k].append(v); byseed[seed][k]=v
    missing=[k for k in FOCAL if k not in d]
    if missing: raise ValueError(f"Missing focal coalitions: {missing}")
    out=[]
    for k in FOCAL:
        a=np.array(d[k],float)
        out.append({"coalition":k,"mean_v":a.mean(),"sd_v":a.std(ddof=1),"min_v":a.min(),"max_v":a.max(),
                    "positive_seeds":int((a>0).sum()),"n_seeds":len(a)})
    with open(os.path.join(args.outdir,"Table_R4_five_seed_robustness.csv"),"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    try:
        import matplotlib.pyplot as plt
        seeds=sorted(byseed)
        plt.figure(figsize=(7.2,4.6))
        for k in FOCAL:
            plt.plot(seeds,[byseed[s][k] for s in seeds],marker="o",label=k)
        plt.axhline(0,linewidth=.8);plt.xlabel("Traffic seed");plt.ylabel("Balanced coalition value v(S)")
        plt.xticks(seeds);plt.legend();plt.tight_layout()
        plt.savefig(os.path.join(args.outdir,"Figure_R3_seedwise_utility.png"),dpi=300);plt.close()
    except ImportError:
        print("WARNING: matplotlib unavailable; table created but figure skipped")
    for r in out: print(r)

if __name__=="__main__": main()
