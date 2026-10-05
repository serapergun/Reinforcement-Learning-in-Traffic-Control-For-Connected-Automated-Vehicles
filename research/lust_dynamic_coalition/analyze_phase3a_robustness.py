#!/usr/bin/env python3
"""Build Phase3A multi-seed robustness table/figure from focal coalition values."""
import argparse,csv,os
from collections import defaultdict
import numpy as np
from math import sqrt

FOCAL=("A1+A3+A4","A3+A4+A7+A8+A9","grand")

def norm(s):
    s=s.strip()
    if s=="grand":
        return "grand"
    parts=[x for x in s.replace(",","+").split("+") if x]
    parts=sorted(parts,key=lambda z:int(z[1:]))
    return "grand" if parts==[f"A{i}" for i in range(1,10)] else "+".join(parts)

def value_from_row(r):
    for col in ("v_balanced","utility","v"):
        if col in r and str(r[col]).strip()!="":
            return float(r[col])
    raise ValueError("Expected one of utility columns: v_balanced, utility, or v")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("seedwise_csv"); ap.add_argument("--outdir",default="phase3a_analysis")
    args=ap.parse_args(); os.makedirs(args.outdir,exist_ok=True)
    rows=list(csv.DictReader(open(args.seedwise_csv,newline="")))
    d=defaultdict(list); byseed=defaultdict(dict)
    for r in rows:
        k=norm(r["coalition"]); v=value_from_row(r)
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
    # Paired small-sample inference against the grand coalition.
    try:
        from scipy.stats import ttest_rel, t, wilcoxon
        stats=[]
        grand=np.array([byseed[s]["grand"] for s in sorted(byseed)],float)
        for k in FOCAL[:-1]:
            a=np.array([byseed[s][k] for s in sorted(byseed)],float)
            diff=a-grand; n=len(diff); mean=float(diff.mean()); sd=float(diff.std(ddof=1))
            se=sd/sqrt(n); crit=float(t.ppf(.975,n-1)); lo=mean-crit*se; hi=mean+crit*se
            tres=ttest_rel(a,grand)
            # n=5 => exact Wilcoxon has discrete p-values; report alongside t-test.
            wres=wilcoxon(diff,alternative="two-sided",method="exact")
            stats.append({"coalition":k,"reference":"grand","n":n,"mean_paired_advantage":mean,
                          "ci95_low":lo,"ci95_high":hi,"cohens_dz":mean/sd,
                          "paired_t":float(tres.statistic),"paired_t_p":float(tres.pvalue),
                          "wilcoxon_W":float(wres.statistic),"wilcoxon_exact_p":float(wres.pvalue),
                          "wins":int((diff>0).sum())})
        with open(os.path.join(args.outdir,"paired_statistics.csv"),"w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(stats[0]));w.writeheader();w.writerows(stats)
        # Regression targets from the verified five-seed panel.
        targets={"A1+A3+A4":(.03490287098580091,.0007894,.0625,5),
                 "A3+A4+A7+A8+A9":(.02945390391,.0078977,.0625,5)}
        for r in stats:
            m,tp,wp,wins=targets[r["coalition"]]
            if abs(r["mean_paired_advantage"]-m)>1e-9 or abs(r["paired_t_p"]-tp)>2e-6 or abs(r["wilcoxon_exact_p"]-wp)>1e-12 or r["wins"]!=wins:
                raise RuntimeError(f"Statistical regression check failed: {r}")
        print("Statistical regression checks: PASS")
        for r in stats: print(r)
    except ImportError:
        print("WARNING: scipy unavailable; paired inference skipped")
    for r in out: print(r)

if __name__=="__main__": main()
