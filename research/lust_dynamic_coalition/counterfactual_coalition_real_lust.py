#!/usr/bin/env python3
"""
Saved-state counterfactual coalition valuation for the official LuST v2.0 experiment.

For every condition and seed:
  1) run the same native-actuated warmup;
  2) save the SUMO state at the branch point;
  3) verify deterministic warmup state equality across source-channel histories;
  4) restore that exact state for the actuated reference and all 14 feasible coalitions;
  5) compute transport benefit, measured resource burden, coalition value,
     Shapley allocation, pairwise synergy, core feasibility and nucleolus.

This is the first stage intended to produce game-theoretic paper results.
"""
import argparse, csv, hashlib, itertools, json, math, os, shutil, sys
from collections import defaultdict
import numpy as np
import torch
from scipy.optimize import linprog

sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from train_mappo_real_lust import MAPPO
from train_coalition_aware_mappo import (
    PLAYERS, feasible_coalitions, CoalitionEnv, QueueForecaster, read_csv
)

def ckey(S):
    if isinstance(S,str): return S
    return "+".join(p for p in PLAYERS if p in set(S))

def source_only(S):
    return tuple(p for p in PLAYERS if p in set(S) and p!="EC")

def file_sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def load_agent(path,n_agents=9,obs_dim=16):
    obj=torch.load(path,map_location="cpu")
    agent=MAPPO(n_agents,obs_dim,2,seed=42)
    agent.actor.load_state_dict(obj["actor"]);agent.critic.load_state_dict(obj["critic"])
    agent.actor.eval();agent.critic.eval()
    return agent,obj.get("meta",{})

def capture_source_history(scenario,selection,gru_path,source_coalition,branch_time,seed,state_path,label):
    fore=QueueForecaster(gru_path)
    env=CoalitionEnv(
        scenario,selection,fore,source_coalition,branch_time,1,seed,label,
        p_fcd=.20,p_v2x=.75,warmup_s=300
    )
    env.start()
    try:
        # start() has reached the branch point without applying any control action.
        env.conn.simulation.saveState(state_path)
        history={tl:[np.asarray(x,dtype=np.float32).tolist() for x in list(fore.history[tl])] for tl in env.tls}
        fingerprint={
            "sim_time":env.conn.simulation.getTime(),
            "min_expected":env.conn.simulation.getMinExpectedNumber(),
            "vehicle_count":len(env.conn.vehicle.getIDList()),
            "state_sha256":file_sha256(state_path),
        }
        return history,fingerprint
    finally:env.close()

def native_step(env):
    arrived=0;co2=0.;served=0;tl_inc=0.
    for _ in range(env.decision_dt):
        if env.conn.simulation.getMinExpectedNumber()<=0:break
        env.conn.simulationStep();arrived+=env.conn.simulation.getArrivedNumber()
        current=set()
        for tl in env.tls:
            rs=env.raw_state(tl);co2+=rs["co2"];current.update(rs["vids"])
        served+=len(env.prev_selected_vids-current)
        new_last={}
        for vid in current:
            try:
                cur=float(env.conn.vehicle.getTimeLoss(vid))
                if vid in env.last_time_loss:tl_inc+=max(0.,cur-env.last_time_loss[vid])
                new_last[vid]=cur
            except Exception:pass
        env.prev_selected_vids=current;env.last_time_loss=new_last
    raw=[env.raw_state(tl) for tl in env.tls]
    halt=sum(x["halt"] for x in raw);wait=sum(x["waiting"] for x in raw)
    lanes=sum(x["lanes"] for x in raw)
    reward=-.5*halt/max(8*lanes,1)-.5*wait/max(300*lanes,1)
    env.metrics["halt"]+=halt;env.metrics["waiting"]+=wait;env.metrics["arrived"]+=arrived
    env.metrics["served"]+=served;env.metrics["time_loss"]+=tl_inc
    env.metrics["co2_mg"]+=co2;env.metrics["reward"]+=reward;env.steps+=1
    done=env.conn.simulation.getTime()>=env.end or env.conn.simulation.getMinExpectedNumber()<=0
    # Keep histories advancing, but reference resource counters are not used.
    env.observe()
    return done

def eval_reference(scenario,selection,gru_path,state_path,history,branch_time,horizon,seed,label):
    fore=QueueForecaster(gru_path)
    env=CoalitionEnv(scenario,selection,fore,("TA","MO","VI"),branch_time,horizon,seed,label,
                     p_fcd=.20,p_v2x=.75,warmup_s=0,load_state=state_path,initial_history=history)
    env.start()
    try:
        while True:
            if native_step(env):break
        return env.summary()
    finally:env.close()

def eval_coalition(scenario,selection,gru_path,agent,state_path,history,coalition,branch_time,horizon,seed,label):
    fore=QueueForecaster(gru_path)
    env=CoalitionEnv(scenario,selection,fore,coalition,branch_time,horizon,seed,label,
                     p_fcd=.20,p_v2x=.75,warmup_s=0,load_state=state_path,initial_history=history)
    obs=env.start()
    try:
        while True:
            a,_,_=agent.act(obs,deterministic=True)
            obs,r,done=env.step(a)
            if done:break
        return env.summary()
    finally:env.close()

def improvement(ref,x,key,higher=False,eps=1e-9):
    a=float(ref[key]);b=float(x[key])
    return (b-a)/(abs(a)+eps) if higher else (a-b)/(abs(a)+eps)

def compute_values(rows,refs,lambda_resource=.15):
    grouped=defaultdict(list)
    for r in rows:grouped[(r["condition"],int(r["seed"]))].append(r)
    out=[]
    for k,rr in grouped.items():
        cond,seed=k;ref=refs[k]
        maxD=max(float(x["payload_kB"]) for x in rr) or 1.
        maxB=max(float(x["message_count"])/(float(x["decision_steps"])*10.) for x in rr) or 1.
        maxG=max(float(x["EC_compute_ms"]) for x in rr) or 1.
        for x in rr:
            I_TL=improvement(ref,x,"approach_time_loss_s",False)
            I_AQL=improvement(ref,x,"mean_halting_vehicles",False)
            I_TH=improvement(ref,x,"controlled_throughput_events",True)
            I_CO2=improvement(ref,x,"CO2_kg_selected_approaches",False)
            P=.25*(I_TL+I_AQL+I_TH+I_CO2)
            D=float(x["payload_kB"])/maxD
            msg_rate=float(x["message_count"])/(float(x["decision_steps"])*10.)
            B=msg_rate/maxB
            G=float(x["EC_compute_ms"])/maxG
            C=(D+B+G)/3.
            y=dict(x)
            y.update({"I_TL":I_TL,"I_AQL":I_AQL,"I_TH":I_TH,"I_CO2":I_CO2,
                      "P_transport":P,"D_norm":D,"B_norm":B,"G_norm":G,
                      "C_resource":C,"v":P-lambda_resource*C,
                      "lambda_resource":lambda_resource})
            out.append(y)
    return out

def all_subsets():
    for k in range(5):
        for comb in itertools.combinations(PLAYERS,k):yield comb

def adjusted_game(v_feasible):
    g={tuple():0.0}
    for S in all_subsets():
        if not S:continue
        key=ckey(S)
        if S==("EC",):g[S]=0.0
        else:g[S]=float(v_feasible.get(key,0.0))
    return g

def shapley(g):
    import math
    n=4;phi={p:0. for p in PLAYERS}
    N=set(PLAYERS)
    for i in PLAYERS:
        others=[p for p in PLAYERS if p!=i]
        for k in range(len(others)+1):
            for comb in itertools.combinations(others,k):
                S=tuple(p for p in PLAYERS if p in comb)
                U=tuple(p for p in PLAYERS if p in set(comb)|{i})
                w=math.factorial(k)*math.factorial(n-k-1)/math.factorial(n)
                phi[i]+=w*(g[U]-g[S])
    return phi

def excess(g,S,y):
    return g[S]-sum(y[PLAYERS.index(p)] for p in S)

def core_feasible(g,tol=1e-9):
    N=tuple(PLAYERS);proper=[S for S in all_subsets() if S and S!=N]
    A=[];b=[]
    for S in proper:
        row=np.zeros(4)
        for p in S:row[PLAYERS.index(p)]=-1.
        A.append(row);b.append(-g[S])
    res=linprog(np.zeros(4),A_ub=np.array(A),b_ub=np.array(b),
                A_eq=np.ones((1,4)),b_eq=np.array([g[N]]),
                bounds=[(None,None)]*4,method="highs")
    return bool(res.success), (res.x.tolist() if res.success else None)

def nucleolus(g,tol=1e-8):
    """
    Sequential least-core LP for a four-player TU game.
    Independent tight coalitions are fixed stage by stage until allocation rank is full.
    """
    N=tuple(PLAYERS)
    proper=[S for S in all_subsets() if S and S!=N]
    fixed=[]  # (incidence, excess_level)
    independent=[np.ones(4)]
    rank=np.linalg.matrix_rank(np.stack(independent))
    y=None
    for stage in range(10):
        # variables y1..y4, eps
        c=np.array([0.,0.,0.,0.,1.])
        A=[];b=[]
        for S in proper:
            if any(S==fs for fs,_,_ in fixed):continue
            row=np.zeros(5)
            for p in S:row[PLAYERS.index(p)]=-1.
            row[4]=-1.
            # v(S)-sum y <= eps  -> -sum y - eps <= -v(S)
            A.append(row);b.append(-g[S])
        Aeq=[np.array([1.,1.,1.,1.,0.])];beq=[g[N]]
        for S,lev,inc in fixed:
            row=np.zeros(5);row[:4]=inc
            # excess=v(S)-sum y=lev -> sum y=v(S)-lev
            Aeq.append(row);beq.append(g[S]-lev)
        res=linprog(c,A_ub=np.array(A) if A else None,b_ub=np.array(b) if A else None,
                    A_eq=np.stack(Aeq),b_eq=np.array(beq),bounds=[(None,None)]*5,method="highs")
        if not res.success:raise RuntimeError("Nucleolus LP failed: "+res.message)
        y=res.x[:4];eps=res.x[4]
        candidates=[]
        for S in proper:
            if any(S==fs for fs,_,_ in fixed):continue
            e=excess(g,S,y)
            if abs(e-eps)<=max(tol,1e-7*max(1.,abs(eps))):
                inc=np.array([1. if p in S else 0. for p in PLAYERS])
                candidates.append((S,inc))
        added=False
        for S,inc in candidates:
            newrank=np.linalg.matrix_rank(np.stack(independent+[inc]))
            if newrank>rank:
                fixed.append((S,eps,inc));independent.append(inc);rank=newrank;added=True
                if rank>=4:break
        if rank>=4:break
        if not added:
            # Numerical fallback: fix the currently tight coalition with the largest rank contribution.
            best=None
            for S in proper:
                if any(S==fs for fs,_,_ in fixed):continue
                inc=np.array([1. if p in S else 0. for p in PLAYERS])
                nr=np.linalg.matrix_rank(np.stack(independent+[inc]))
                if nr>rank:
                    e=excess(g,S,y);gap=abs(e-eps)
                    if best is None or gap<best[0]:best=(gap,S,inc)
            if best:
                _,S,inc=best;fixed.append((S,eps,inc));independent.append(inc);rank+=1
            else:break
    return {p:float(y[i]) for i,p in enumerate(PLAYERS)}

def game_analysis(value_rows):
    # average v by condition/coalition over seeds
    by=defaultdict(list)
    for r in value_rows:by[(r["condition"],r["coalition"])].append(float(r["v"]))
    conditions=sorted(set(r["condition"] for r in value_rows))
    alloc=[];syn=[];stab=[]
    for cond in conditions:
        vf={coal:float(np.mean(vals)) for (c,coal),vals in by.items() if c==cond}
        g=adjusted_game(vf);phi=shapley(g);nuc=nucleolus(g);core_ok,_=core_feasible(g)
        N=tuple(PLAYERS)
        phi_vec=[phi[p] for p in PLAYERS];nuc_vec=[nuc[p] for p in PLAYERS]
        max_phi=max([0.]+[excess(g,S,phi_vec) for S in all_subsets() if S and S!=N])
        max_nuc=max([0.]+[excess(g,S,nuc_vec) for S in all_subsets() if S and S!=N])
        for p in PLAYERS:alloc.append({"condition":cond,"player":p,"Shapley":phi[p],"Nucleolus":nuc[p]})
        for i,j in itertools.combinations(PLAYERS,2):
            S=tuple(p for p in PLAYERS if p in {i,j})
            syn.append({"condition":cond,"pair":f"{i}+{j}","synergy":g[S]-g[(i,)]-g[(j,)]})
        stab.append({"condition":cond,"core_nonempty":int(core_ok),
                     "max_excess_Shapley":max_phi,"max_excess_Nucleolus":max_nuc,
                     "grand_value":g[N]})
    return alloc,syn,stab

def write_csv(path,rows):
    if not rows:return
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)

def make_figures(outdir,value_rows,alloc,stab):
    import matplotlib.pyplot as plt
    # Value landscape by condition
    conds=sorted(set(r["condition"] for r in value_rows))
    coals=sorted(set(r["coalition"] for r in value_rows),key=lambda x:(len(x.split("+")),x))
    fig,ax=plt.subplots(figsize=(11,5.5))
    width=.8/max(len(conds),1);x=np.arange(len(coals))
    for k,c in enumerate(conds):
        vals=[]
        for coal in coals:
            q=[float(r["v"]) for r in value_rows if r["condition"]==c and r["coalition"]==coal]
            vals.append(np.mean(q) if q else np.nan)
        ax.bar(x+(k-(len(conds)-1)/2)*width,vals,width=width,label=c)
    ax.set_xticks(x);ax.set_xticklabels(coals,rotation=70,ha="right",fontsize=7)
    ax.set_ylabel("Coalition value v(S)");ax.legend();fig.tight_layout()
    fig.savefig(os.path.join(outdir,"Figure4_real_coalition_value_landscape.png"),dpi=300,bbox_inches="tight");plt.close(fig)

    # Shapley allocations
    fig,ax=plt.subplots(figsize=(8,5))
    x=np.arange(4);width=.8/max(len(conds),1)
    for k,c in enumerate(conds):
        vals=[next(r["Shapley"] for r in alloc if r["condition"]==c and r["player"]==p) for p in PLAYERS]
        ax.bar(x+(k-(len(conds)-1)/2)*width,vals,width=width,label=c)
    ax.set_xticks(x);ax.set_xticklabels(PLAYERS);ax.set_ylabel("Shapley allocation");ax.legend();fig.tight_layout()
    fig.savefig(os.path.join(outdir,"Figure7_real_shapley_allocations.png"),dpi=300,bbox_inches="tight");plt.close(fig)

    # Max excess
    fig,ax=plt.subplots(figsize=(8,5));x=np.arange(len(stab));w=.36
    ax.bar(x-w/2,[r["max_excess_Shapley"] for r in stab],width=w,label="Shapley")
    ax.bar(x+w/2,[r["max_excess_Nucleolus"] for r in stab],width=w,label="Nucleolus")
    ax.axhline(0,linewidth=.8);ax.set_xticks(x);ax.set_xticklabels([r["condition"] for r in stab])
    ax.set_ylabel("Maximum coalition excess");ax.legend();fig.tight_layout()
    fig.savefig(os.path.join(outdir,"Figure8_real_maximum_coalition_excess.png"),dpi=300,bbox_inches="tight");plt.close(fig)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scenario",required=True);ap.add_argument("--selection",required=True)
    ap.add_argument("--windows",required=True);ap.add_argument("--gru",required=True);ap.add_argument("--policy",required=True)
    ap.add_argument("--outdir",required=True);ap.add_argument("--horizon",type=int,default=300)
    ap.add_argument("--seeds",default="8101");ap.add_argument("--lambda-resource",type=float,default=.15)
    args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
    selection=sorted(read_csv(args.selection),key=lambda r:int(r["agent_alias"][1:]))
    wins={r["condition"]:int(float(r["selected_hour"])) for r in read_csv(args.windows)}
    conds=[c for c in ("Off-peak","AM","Lunch","PM") if c in wins]
    agent,policy_meta=load_agent(args.policy,len(selection),16)
    coals=feasible_coalitions()
    source_sets=sorted(set(source_only(S) for S in coals),key=lambda s:(len(s),s))
    raw_rows=[];refs={};state_checks=[]

    for seed in [int(x) for x in args.seeds.split(",") if x.strip()]:
        for cond in conds:
            branch_time=wins[cond]*3600+900
            histories={}
            canonical_state=os.path.join(args.outdir,f"state_{cond}_{seed}.xml")
            canonical_sha=None
            for j,src in enumerate(source_sets):
                state_tmp=canonical_state if j==0 else os.path.join(args.outdir,f"statecheck_{cond}_{seed}_{j}.xml")
                hist,fp=capture_source_history(args.scenario,selection,args.gru,src,branch_time,seed,state_tmp,
                                               f"prep-{cond}-{seed}-{j}")
                histories[ckey(src)]=hist
                if j==0:canonical_sha=fp["state_sha256"]
                equal=int(fp["state_sha256"]==canonical_sha)
                state_checks.append({"condition":cond,"seed":seed,"source_set":ckey(src),
                                     **fp,"matches_canonical_state":equal})
                if j>0:
                    try:os.remove(state_tmp)
                    except OSError:pass
            if not all(r["matches_canonical_state"] for r in state_checks if r["condition"]==cond and r["seed"]==seed):
                raise RuntimeError(f"Warmup state mismatch for {cond}, seed {seed}; counterfactual equality not satisfied.")

            ref_hist=histories[ckey(("TA","MO","VI"))]
            ref=eval_reference(args.scenario,selection,args.gru,canonical_state,ref_hist,branch_time,args.horizon,seed,
                               f"ref-{cond}-{seed}")
            refs[(cond,seed)]=ref
            for S in coals:
                hist=histories[ckey(source_only(S))]
                m=eval_coalition(args.scenario,selection,args.gru,agent,canonical_state,hist,S,branch_time,args.horizon,seed,
                                 f"cf-{cond}-{seed}-{'-'.join(S)}")
                raw_rows.append({"condition":cond,"seed":seed,"coalition":ckey(S),"coalition_size":len(S),**m})
                print(raw_rows[-1],flush=True)
            try:os.remove(canonical_state)
            except OSError:pass

    value_rows=compute_values(raw_rows,refs,args.lambda_resource)
    alloc,syn,stab=game_analysis(value_rows)
    ref_rows=[{"condition":c,"seed":s,**m} for (c,s),m in refs.items()]
    write_csv(os.path.join(args.outdir,"counterfactual_raw.csv"),raw_rows)
    write_csv(os.path.join(args.outdir,"actuated_reference.csv"),ref_rows)
    write_csv(os.path.join(args.outdir,"coalition_values.csv"),value_rows)
    write_csv(os.path.join(args.outdir,"shapley_nucleolus.csv"),alloc)
    write_csv(os.path.join(args.outdir,"pairwise_synergy.csv"),syn)
    write_csv(os.path.join(args.outdir,"core_stability.csv"),stab)
    write_csv(os.path.join(args.outdir,"state_equality_audit.csv"),state_checks)
    make_figures(args.outdir,value_rows,alloc,stab)
    meta={"horizon_s":args.horizon,"seeds":args.seeds,"lambda_resource":args.lambda_resource,
          "transport_weights":{"TL":.25,"AQL":.25,"TH":.25,"CO2":.25},
          "resource_weights":{"D":1/3,"B":1/3,"G":1/3},
          "reference":"native actuated control restored from identical saved SUMO state",
          "policy_metadata":policy_meta}
    with open(os.path.join(args.outdir,"game_run_metadata.json"),"w") as f:json.dump(meta,f,indent=2)
    print(json.dumps({"stability":stab,"metadata":meta},indent=2))

if __name__=="__main__":
    main()
