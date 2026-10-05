#!/usr/bin/env python3
"""Reproduce Phase3A exact-game analysis from coalition_values.csv.

Requires the complete 2^9 operational characteristic function produced by
evaluate_coalitions_legacy_replay.py. No simulation is rerun here.
"""
import argparse, csv, itertools, math, os
from collections import defaultdict
import numpy as np

# Verified seed-9001 regression targets for the published balanced exact game.
REGRESSION={"grand_v":0.007595492418404752,"best_v":0.0455069834356523,"epsilon":0.022705376418353573}

PLAYERS=tuple(f"A{i}" for i in range(1,10))
N=len(PLAYERS)

def coalition_key(label):
    s=str(label).strip()
    if s in ("","empty","none"): return frozenset()
    if s=="grand": return frozenset(PLAYERS)
    return frozenset(x.strip() for x in s.replace(",", "+").split("+") if x.strip())

def read_game(path, value_col="v_balanced"):
    rows=list(csv.DictReader(open(path,newline="")))
    game={}
    row_by_key={}
    for r in rows:
        k=coalition_key(r["coalition"])
        if k in game: raise ValueError(f"Duplicate coalition: {r['coalition']}")
        game[k]=float(r[value_col]); row_by_key[k]=r
    expected=1<<N
    if len(game)!=expected: raise ValueError(f"Exact analysis requires {expected} unique coalitions; found {len(game)}")
    for bits in itertools.product((0,1), repeat=N):
        k=frozenset(p for p,b in zip(PLAYERS,bits) if b)
        if k not in game: raise ValueError(f"Missing coalition {sorted(k)}")
    if abs(game[frozenset()])>1e-10: raise ValueError("Expected v(empty)=0")
    return game,row_by_key

def shapley(game):
    fact=math.factorial; phi={p:0.0 for p in PLAYERS}
    for p in PLAYERS:
        others=[q for q in PLAYERS if q!=p]
        for r in range(N):
            w=fact(r)*fact(N-r-1)/fact(N)
            for comb in itertools.combinations(others,r):
                S=frozenset(comb)
                phi[p]+=w*(game[S|{p}]-game[S])
    return phi

def excess(game,x,S):
    return game[S]-sum(x[p] for p in S)

def least_core(game):
    try:
        from scipy.optimize import linprog
    except ImportError as e:
        raise SystemExit("scipy is required for least-core/nucleolus analysis") from e
    coal=[frozenset(c) for r in range(1,N) for c in itertools.combinations(PLAYERS,r)]
    # variables x_1..x_n, epsilon; v(S)-x(S)<=epsilon
    A=[]; b=[]
    for S in coal:
        A.append([-1.0 if p in S else 0.0 for p in PLAYERS]+[-1.0])
        b.append(-game[S])
    c=[0.0]*N+[1.0]
    eq=[[1.0]*N+[0.0]]; beq=[game[frozenset(PLAYERS)]]
    res=linprog(c,A_ub=A,b_ub=b,A_eq=eq,b_eq=beq,bounds=[(None,None)]*(N+1),method="highs")
    if not res.success: raise RuntimeError(res.message)
    x={p:float(res.x[i]) for i,p in enumerate(PLAYERS)}
    eps=float(res.x[-1])
    tol=1e-8
    binding=[S for S in coal if abs(excess(game,x,S)-eps)<=tol]
    rank=np.linalg.matrix_rank(np.array([[1.0 if p in S else 0.0 for p in PLAYERS] for S in binding]+[[1.0]*N]))
    return x,eps,binding,int(rank)

def write_csv(path,rows):
    if not rows:return
    with open(path,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("coalition_values")
    ap.add_argument("--outdir",default="phase3a_analysis")
    ap.add_argument("--value-col",default="v_balanced")
    ap.add_argument("--regression-check",action="store_true",help="assert verified seed-9001 balanced-game targets")
    args=ap.parse_args(); os.makedirs(args.outdir,exist_ok=True)
    game,raw=read_game(args.coalition_values,args.value_col)
    phi=shapley(game)
    grand=frozenset(PLAYERS)
    eff=sum(phi.values())-game[grand]
    if abs(eff)>1e-9: raise RuntimeError(f"Shapley efficiency failed: {eff}")
    x,eps,binding,rank=least_core(game)
    # For this verified Phase3A game, first-stage least-core constraints + efficiency
    # have full allocation rank (9), so the least-core solution is unique and equals
    # the nucleolus. Abort rather than over-label if a future game lacks this property.
    if rank<N:
        raise RuntimeError(f"Least-core allocation not unique (binding+efficiency rank={rank}); sequential nucleolus LP required")
    shap_max=max(excess(game,phi,S) for S in game if S not in (frozenset(),grand))
    nuc_max=max(excess(game,x,S) for S in game if S not in (frozenset(),grand))
    alloc=[]
    for p in PLAYERS:
        singleton=frozenset([p])
        alloc.append({"player":p,"singleton_v":game[singleton],"shapley":phi[p],"nucleolus":x[p],
                      "shapley_IR":phi[p]+1e-10>=game[singleton],"nucleolus_IR":x[p]+1e-10>=game[singleton]})
    write_csv(os.path.join(args.outdir,"allocations.csv"),alloc)
    bysize=defaultdict(list)
    for S,v in game.items(): bysize[len(S)].append(v)
    size_rows=[{"coalition_size":k,"n":len(vs),"mean_v":np.mean(vs),"sd_v":np.std(vs,ddof=1) if len(vs)>1 else 0,
                "min_v":min(vs),"max_v":max(vs)} for k,vs in sorted(bysize.items())]
    write_csv(os.path.join(args.outdir,"coalition_size_summary.csv"),size_rows)
    best=max(game,key=game.get)
    summary=[{"n_players":N,"n_coalitions":len(game),"grand_v":game[grand],
              "best_coalition":"+".join(sorted(best,key=lambda z:int(z[1:]))),"best_v":game[best],
              "shapley_sum":sum(phi.values()),"shapley_efficiency_error":eff,
              "core_feasible":eps<=1e-9,"least_core_epsilon":eps,
              "binding_constraints":len(binding),"binding_plus_efficiency_rank":rank,
              "shapley_max_excess":shap_max,"nucleolus_max_excess":nuc_max,
              "max_excess_reduction_pct":100*(shap_max-nuc_max)/shap_max}]
    write_csv(os.path.join(args.outdir,"game_summary.csv"),summary)
    # Publication Figure R1: all exact coalition values by coalition size.
    try:
        import matplotlib.pyplot as plt
        xs=[]; ys=[]
        for S,v in sorted(game.items(),key=lambda kv:(len(kv[0]),kv[1])):
            xs.append(len(S)); ys.append(v)
        plt.figure(figsize=(7.2,4.6)); plt.scatter(xs,ys,s=14,alpha=.55)
        plt.scatter([len(best)],[game[best]],s=70,marker="*",label="Exact best")
        plt.scatter([N],[game[grand]],s=50,marker="s",label="Grand coalition")
        plt.axhline(0,linewidth=.8); plt.xlabel("Coalition size"); plt.ylabel("Balanced coalition value v(S)")
        plt.legend(); plt.tight_layout(); plt.savefig(os.path.join(args.outdir,"Figure_R1_coalition_value_vs_size.png"),dpi=300); plt.close()
        # Publication Figure R2: exact allocation comparison.
        xx=np.arange(N); w=.38
        plt.figure(figsize=(7.2,4.6)); plt.bar(xx-w/2,[phi[p] for p in PLAYERS],w,label="Shapley")
        plt.bar(xx+w/2,[x[p] for p in PLAYERS],w,label="Nucleolus")
        plt.axhline(0,linewidth=.8); plt.xticks(xx,PLAYERS); plt.ylabel("Normalized performance-credit allocation")
        plt.legend(); plt.tight_layout(); plt.savefig(os.path.join(args.outdir,"Figure_R2_shapley_vs_nucleolus.png"),dpi=300); plt.close()
    except ImportError:
        print("WARNING: matplotlib unavailable; CSV outputs created but figures skipped")
    if args.regression_check:
        tests=[("grand_v",game[grand],REGRESSION["grand_v"]),("best_v",game[best],REGRESSION["best_v"]),("epsilon",eps,REGRESSION["epsilon"])]
        for name,got,want in tests:
            if not math.isclose(got,want,rel_tol=0,abs_tol=1e-10):
                raise RuntimeError(f"Regression check failed for {name}: got {got}, expected {want}")
        if rank!=9: raise RuntimeError(f"Regression check failed: binding+efficiency rank={rank}, expected 9")
        print("Regression check: PASS")
    print(summary[0])
    for r in alloc: print(r)

if __name__=="__main__": main()
