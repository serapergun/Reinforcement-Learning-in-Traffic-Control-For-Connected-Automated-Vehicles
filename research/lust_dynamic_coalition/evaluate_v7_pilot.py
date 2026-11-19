#!/usr/bin/env python3
"""Independent-seed paired pilot for NEW stakeholder MAPPO checkpoint only."""
import argparse,csv,json,hashlib,os,random,sys,math
from pathlib import Path
COALITIONS=[('MO','VI'),('MO','VI','EC'),('TA','MO','VI','EC')]
METRICS=['mean_halting_vehicles','mean_waiting_time_lane_sum_s','CO2_kg_selected_approaches','arrived_vehicles_global']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def paired_delta(y,ref):
    y,ref=float(y),float(ref)
    if not math.isfinite(y) or not math.isfinite(ref):raise ValueError('Nonfinite metric')
    return 100.0*(y-ref)/ref if abs(ref)>1e-12 else None
def main():
    p=argparse.ArgumentParser()
    for n in ('repo-modules','sumo','sumo-tools','scenario','selection','windows','checkpoint','outdir'):p.add_argument('--'+n,required=True)
    p.add_argument('--condition',default='AM',choices=['Off-peak','AM','Lunch','PM'])
    p.add_argument('--seeds',default='9301,9302');p.add_argument('--eval-s',type=int,default=900)
    p.add_argument('--deploy-margin',type=float,default=.15)
    a=p.parse_args()
    seeds=[int(s) for s in a.seeds.split(',')]
    if not seeds or len(set(seeds))!=len(seeds) or set(seeds)&set(range(1100,1114)) or 9001 in seeds:p.error('invalid/leaked seeds')
    if a.eval_s<=0 or a.eval_s%10 or not 0<=a.deploy_margin<1:p.error('invalid settings')
    sys.path.insert(0,str(Path(a.repo_modules).resolve()))
    sys.path.insert(0,str(Path(a.sumo_tools).resolve()))
    import numpy as np,torch,traci
    from train_mappo_legacy_replay import Env,read_csv,native_eval
    from train_stakeholder_mappo_legacy import StakeholderMAPPO,run
    selection=read_csv(a.selection)
    assert len(selection)==9 and len({r['tls_id'] for r in selection})==9
    windows={r['condition']:int(float(r['selected_hour'])) for r in read_csv(a.windows)}
    ck=torch.load(a.checkpoint,map_location='cpu',weights_only=False)
    assert ck.get('meta',{}).get('obs_dim')==14
    model=StakeholderMAPPO(9,14,3,42)
    model.actor.load_state_dict(ck['actor']);model.critic.load_state_dict(ck['critic'])
    model.actor.eval();model.critic.eval()
    target=Path(a.outdir);target.mkdir(parents=True,exist_ok=True)
    result=[]
    for seed in seeds:
        native=native_eval(traci,a.sumo,a.scenario,selection,windows[a.condition]*3600,a.eval_s,seed)
        result.append({'condition':a.condition,'seed':seed,'coalition':'native','strategy':'native',**native})
        for coalition in COALITIONS:
            random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
            env=Env(traci,a.scenario,selection,windows[a.condition]*3600,a.eval_s,seed)
            _,stats=run(env,a.sumo,model,coalition,False,deploy_margin=a.deploy_margin)
            row={'condition':a.condition,'seed':seed,'coalition':'+'.join(coalition),'strategy':'new_frozen_checkpoint',**stats}
            for metric in METRICS:
                row['native_'+metric]=native[metric]
                row['delta_pct_'+metric]=paired_delta(stats[metric],native[metric])
            result.append(row)
        with (target/'v7_paired_pilot.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in result for k in r)))
            w.writeheader();w.writerows(result)
    assert len(result)==4*len(seeds)
    evidence={'status':'new_checkpoint_paired_pilot','condition':a.condition,'seeds':seeds,
        'eval_s':a.eval_s,'rows':len(result),'deploy_margin':a.deploy_margin,
        'checkpoint_sha256':sha(a.checkpoint),'selection_sha256':sha(a.selection),
        'windows_sha256':sha(a.windows),'simulator_sha256':sha(a.sumo),
        'interpretation':'descriptive n=2 only; NOT old checkpoint reproduction',
        'metric_scope':'arrived_vehicles_global is global; CO2 selected approaches only'}
    (target/'v7_pilot_provenance.json').write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence,indent=2))
if __name__=='__main__':main()
