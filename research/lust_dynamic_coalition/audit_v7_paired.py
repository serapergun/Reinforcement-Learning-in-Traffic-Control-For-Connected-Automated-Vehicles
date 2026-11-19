#!/usr/bin/env python3
"""Audit exactly matched V7 pilot rows; descriptive only (n=2)."""
import argparse,csv,json,math,collections,pathlib,statistics
EXPECTED={'native','MO+VI','MO+VI+EC','TA+MO+VI+EC'}
METRICS=('mean_waiting_time_lane_sum_s','mean_halting_vehicles','CO2_kg_selected_approaches','arrived_vehicles_global')
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    rows=list(csv.DictReader(open(a.input,newline='',encoding='utf-8')))
    by=collections.defaultdict(dict)
    for row in rows:
        seed=int(row['seed']);co=row['coalition']
        if co in by[seed]:raise ValueError(f'duplicate seed/coalition {seed}/{co}')
        by[seed][co]=row
    if len(by)!=2 or len(rows)!=8:raise ValueError('pilot must contain exactly two seeds x four strategies')
    if any(set(x)!=EXPECTED for x in by.values()):raise ValueError('missing or unexpected strategy')
    details=[]; summary={}
    for seed,group in sorted(by.items()):
        base=group['native']
        for coal in sorted(EXPECTED-{'native'}):
            r=group[coal]
            d={'seed':seed,'coalition':coal}
            for m in METRICS:
                b=float(base[m]);y=float(r[m])
                if not (math.isfinite(b) and math.isfinite(y)):raise ValueError('nonfinite metric')
                if b==0:raise ValueError('zero baseline '+m)
                change=100*(y-b)/b
                key='delta_pct_'+m
                recorded=r.get(key,'')
                if recorded not in ('',None) and abs(float(recorded)-change)>1e-7:
                    raise ValueError(f'paired delta mismatch seed={seed} coal={coal} metric={m}')
                d[key]=change
            n=int(float(r.get('interventions',0)))
            if n<0:raise ValueError('negative interventions')
            d['interventions']=n
            details.append(d)
    for coal in sorted(EXPECTED-{'native'}):
        part=[r for r in details if r['coalition']==coal]
        summary[coal]={'n_seeds':len(part),'interventions_total':sum(x['interventions'] for x in part)}
        for m in METRICS:
            key='delta_pct_'+m
            vals=[x[key] for x in part]
            summary[coal][key+'_mean']=statistics.mean(vals)
            summary[coal][key+'_min']=min(vals)
            summary[coal][key+'_max']=max(vals)
    result={'status':'DESCRIPTIVE_ONLY','seed_count':2,'total_rows':8,'paired_rows':details,
            'summary':summary,'limitations':[
               'n=2: no inferential significance statements',
               'new V6 checkpoint cannot be compared as identical to the lost original',
               'native global arrival metric differs in spatial scope from selected-approach CO2',
               'pilot is AM only, so no four-condition generalization']}
    target=pathlib.Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('PASS: 8 source rows and 6 paired coalitions validated')
if __name__=='__main__':main()
