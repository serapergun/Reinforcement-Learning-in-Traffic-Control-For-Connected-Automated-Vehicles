#!/usr/bin/env python3
"""Frozen-policy V8 diagnostics; no training or test-set selection."""
import argparse, csv, hashlib, json, math, sys
from pathlib import Path

COALITIONS = [('MO','VI'), ('MO','VI','EC'), ('TA','MO','VI','EC')]
MARGINS = (.15,.16,.17,.18,.19,.20,.21,.22,.23,.24,.25)
SCALES = (0., .25, .50, .75)
METRICS = ('mean_halting_vehicles','mean_waiting_time_lane_sum_s','CO2_kg_selected_approaches','arrived_vehicles_global')

def design():
    return [(c,m,'deterministic') for c in COALITIONS for m in MARGINS] + [(c,.15,mode) for c in COALITIONS for mode in ('stochastic','stochastic_veto')] + [(COALITIONS[1],.15,mode) for mode in ('ec_bit_zero','ec_bit_and_feature_zero')]

def choose(p, mask, margin):
    if len(p)!=3 or len(mask)!=3 or not mask[0] or not 0<=margin<1:
        raise ValueError('invalid decision inputs')
    if not all(math.isfinite(float(x)) for x in p):
        raise ValueError('nonfinite probabilities')
    best=max((i for i in range(3) if mask[i]),key=lambda i:p[i])
    return best if best and float(p[best]-p[0])>=margin else 0

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rollout(env, sumo, model, coalition, margin, mode, log):
    import numpy as np
    import torch
    from stakeholder_observation import StakeholderObservation
    counts=[0,0,0]
    rng=np.random.default_rng(100000+env.seed)
    try:
        env.start(sumo)
        adapter=StakeholderObservation(env,coalition,env.seed)
        while True:
            obs=adapter.observe().copy()
            if mode in ('ec_bit_zero','ec_bit_and_feature_zero'): obs[:,13]=0
            if mode=='ec_bit_and_feature_zero': obs[:,9]=0
            mask=env.action_mask()
            with torch.no_grad():
                probs=torch.softmax(model.actor(torch.tensor(obs,dtype=torch.float32)).masked_fill(~torch.tensor(mask,dtype=torch.bool),-1e9),dim=-1).numpy()
            def select(p,m):
                if mode.startswith('stochastic'):
                    q=np.where(m,p,0.).astype(float); q/=q.sum()
                    a=int(rng.choice(3,p=q))
                    if mode=='stochastic_veto' and a and p[a]-p[0]<margin: return 0
                    return a
                return choose(p,m,margin)
            actions=np.array([select(p,m) for p,m in zip(probs,mask)])
            before=env.interventions
            eligible=0
            for i,(p,m,a) in enumerate(zip(probs,mask,actions)):
                assert m[a]
                if m[1] or m[2]:
                    counts[a]+=1
                    eligible+=1
                log.write(json.dumps(dict(time=env.tc.time_s(),tls=env.tls[i],mask=m.tolist(),p=p.tolist(),action=int(a),ec=float(obs[i,9]),entropy=-sum(float(x)*math.log(float(x)) for x in p if x>0)))+'\n')
            _,_,done=env.step(actions)
            assert env.interventions-before==int(np.count_nonzero(actions))
            if done: break
        s=env.summary()
        assert sum(counts)==s['mask_eligible_slots']
        assert counts[1]+counts[2]==s['interventions']==s['action_requests']
        assert s['decision_steps']==90 and env.tc.time_s()==env.end
        return dict(s,eligible_action0=counts[0],eligible_action1=counts[1],eligible_action2=counts[2],extension_s=3*counts[1]+6*counts[2],eligible_intervention_fraction=(counts[1]+counts[2])/max(sum(counts),1))
    finally:
        env.close()

def main():
    p=argparse.ArgumentParser()
    for n in ('sumo','sumo-tools','scenario','selection','windows','checkpoint','outdir'):p.add_argument('--'+n,required=True)
    p.add_argument('--seed',type=int,required=True,choices=[9301,9302])
    p.add_argument('--case',type=int,required=True,choices=range(42))
    a=p.parse_args()
    sys.path.insert(0,str(Path(a.sumo_tools).resolve()))
    import torch,traci
    from train_mappo_legacy_replay import Env,read_csv,native_eval
    from train_stakeholder_mappo_legacy import StakeholderMAPPO
    torch.set_num_threads(1)
    sel=read_csv(a.selection)
    assert len(sel)==len({r['tls_id'] for r in sel})==9
    windows={r['condition']:int(float(r['selected_hour'])) for r in read_csv(a.windows)}
    assert windows['AM']==8
    ck=torch.load(a.checkpoint,map_location='cpu',weights_only=False)
    assert ck['meta']['obs_dim']==14
    model=StakeholderMAPPO(9,14,3,42)
    model.actor.load_state_dict(ck['actor']);model.actor.eval()
    out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True)
    row=dict(seed=a.seed,case=a.case,condition='AM',checkpoint_sha256=digest(a.checkpoint),selection_sha256=digest(a.selection),windows_sha256=digest(a.windows),simulator_sha256=digest(a.sumo))
    if a.case==0:
        row.update(coalition='native',margin='',scale='')
        row.update(native_eval(traci,a.sumo,a.scenario,sel,28800,900,a.seed))
    else:
        c,m,mode=design()[a.case-1]
        row.update(coalition='+'.join(c),margin=m,mode=mode,deployment_seed=100000+a.seed)
        env=Env(traci,a.scenario,sel,28800,900,a.seed)
        with (out/'decisions.jsonl').open('w') as log:
            row.update(rollout(env,a.sumo,model,c,m,mode,log))
    assert row['decision_steps']==90
    assert all(math.isfinite(float(row[k])) for k in METRICS)
    with (out/'result.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
    print(json.dumps(row))
if __name__=='__main__':main()
