#!/usr/bin/env python3
import argparse,csv,json,os,random
from collections import defaultdict
import numpy as np

FEATURES=["veh_count","halting_count","mean_speed_mps","mean_occupancy_pct","waiting_time_s"]
EXPECTED_TLS=sorted(["-10160","-29460","-3054","-5704","-8604","-9194","-29558","-5432","-21042"])

def metrics(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float)
    mae=float(np.mean(np.abs(y-p)));rmse=float(np.sqrt(np.mean((y-p)**2)))
    den=float(np.sum((y-y.mean())**2));r2=float(1-np.sum((y-p)**2)/den) if den>0 else 0.0
    return {"MAE":mae,"RMSE":rmse,"R2":r2}

def load_validate(path,strict=True):
    rows=[]
    with open(path,newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in ["time_s"]+FEATURES+["co2_mg_s"]: r[k]=float(r[k])
            rows.append(r)
    if strict:
        tids=sorted(set(r["tls_id"] for r in rows))
        assert len(tids)==9, f"expected 9 TLS agents, got {len(tids)}: {tids}"
        assert len(rows)==9*8640, f"expected {9*8640} rows, got {len(rows)}"
        for tid in tids:
            ts=sorted(r["time_s"] for r in rows if r["tls_id"]==tid)
            assert len(ts)==8640,(tid,len(ts));assert ts[0]==10 and ts[-1]==86400,(tid,ts[0],ts[-1])
            assert all(abs(b-a-10)<1e-9 for a,b in zip(ts,ts[1:])),f"time gap {tid}"
    return rows

def sequences(rows,L=30,h=6):
    by=defaultdict(list)
    for r in rows: by[r["tls_id"]].append(r)
    X=[];delta=[];future=[];current=[];times=[];tids=[]
    for tid,rs in by.items():
        rs=sorted(rs,key=lambda r:r["time_s"])
        a=np.asarray([[r[k] for k in FEATURES] for r in rs],np.float32)
        q=np.asarray([r["halting_count"] for r in rs],np.float32)
        for i in range(L-1,len(rs)-h):
            if abs(rs[i+h]["time_s"]-rs[i]["time_s"]-h*10)>1e-9: continue
            X.append(a[i-L+1:i+1]);current.append(q[i]);future.append(q[i+h]);delta.append(q[i+h]-q[i])
            times.append(rs[i]["time_s"]);tids.append(tid)
    return map(np.asarray,(X,delta,future,current,times,tids))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--data",required=True);ap.add_argument("--outdir",required=True)
    ap.add_argument("--epochs",type=int,default=40);ap.add_argument("--patience",type=int,default=7);ap.add_argument("--seed",type=int,default=42)
    ap.add_argument("--smoke",action="store_true");args=ap.parse_args();os.makedirs(args.outdir,exist_ok=True)
    random.seed(args.seed);np.random.seed(args.seed)
    import torch,torch.nn as nn
    torch.manual_seed(args.seed);torch.set_num_threads(max(1,min(4,os.cpu_count() or 1)))
    rows=load_validate(args.data,strict=not args.smoke)
    if args.smoke:
        keep=sorted(set(r["time_s"] for r in rows))[:240]
        rows=[r for r in rows if r["time_s"] in set(keep)]
    X,d,y,q0,times,tids=sequences(rows)
    assert len(y)>0 and np.isfinite(X).all() and np.isfinite(y).all()
    q1=np.quantile(times,.60);q2=np.quantile(times,.80);tr=times<=q1;va=(times>q1)&(times<=q2);te=times>q2
    assert tr.any() and va.any() and te.any()
    # robust feature scaling learned from training only
    flat=X[tr].reshape(-1,X.shape[-1]);med=np.median(flat,axis=0);iqr=np.percentile(flat,75,axis=0)-np.percentile(flat,25,axis=0);iqr=np.where(iqr<1e-6,1.0,iqr)
    Xn=np.clip((X-med)/iqr,-10,10)
    # target residual scaling learned from training only
    dm=float(d[tr].mean());ds=float(d[tr].std()+1e-6);dn=(d-dm)/ds
    tid_order=sorted(set(tids.tolist()));tidmap={t:i for i,t in enumerate(tid_order)}
    tidx=np.asarray([tidmap[t] for t in tids],np.int64)
    # deterministic time-of-day linear residual benchmark fit on train only
    tod=np.stack([np.ones(len(times)),np.sin(2*np.pi*times/86400),np.cos(2*np.pi*times/86400),q0],axis=1)
    beta=np.linalg.lstsq(tod[tr],d[tr],rcond=None)[0];linpred=q0[te]+tod[te]@beta
    class Net(nn.Module):
        def __init__(self):
            super().__init__();self.emb=nn.Embedding(len(tid_order),4);self.gru=nn.GRU(len(FEATURES)+4,64,batch_first=True,dropout=0)
            self.head=nn.Sequential(nn.Linear(64,32),nn.ReLU(),nn.Dropout(.10),nn.Linear(32,1))
        def forward(self,x,t):
            e=self.emb(t)[:,None,:].expand(-1,x.shape[1],-1);z,_=self.gru(torch.cat([x,e],2));return self.head(z[:,-1]).squeeze(-1)
    model=Net();opt=torch.optim.AdamW(model.parameters(),lr=5e-4,weight_decay=1e-4);lossfn=nn.SmoothL1Loss();batch=512
    def tensors(mask):
        return torch.tensor(Xn[mask],dtype=torch.float32),torch.tensor(tidx[mask]),torch.tensor(dn[mask],dtype=torch.float32)
    Xt,Tt,Yt=tensors(tr);Xv,Tv,Yv=tensors(va);best=None;bestv=float("inf");bad=0;hist=[]
    for ep in range(args.epochs):
        model.train();perm=torch.randperm(len(Xt));ls=[]
        for st in range(0,len(Xt),batch):
            ix=perm[st:st+batch];pred=model(Xt[ix],Tt[ix]);loss=lossfn(pred,Yt[ix]);opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.0);opt.step();ls.append(float(loss))
        model.eval()
        with torch.no_grad(): vl=float(lossfn(model(Xv,Tv),Yv))
        hist.append({"epoch":ep+1,"train_loss":float(np.mean(ls)),"val_loss":vl})
        print(hist[-1],flush=True)
        if vl<bestv-1e-6: bestv=vl;bad=0;best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        else:
            bad+=1
            if bad>=args.patience: break
    model.load_state_dict(best);model.eval();Xte,Tte,_=tensors(te)
    with torch.no_grad(): dp=model(Xte,Tte).numpy()*ds+dm
    gp=np.maximum(0,q0[te]+dp);pers=q0[te]
    out={"target":"delta_halting_count_60s","features":FEATURES,"samples_total":int(len(y)),"samples_train":int(tr.sum()),"samples_val":int(va.sum()),"samples_test":int(te.sum()),
         "best_epoch":int(np.argmin([z["val_loss"] for z in hist])+1),"persistence":metrics(y[te],pers),"linear_time_residual":metrics(y[te],linpred),"GRU_v2_residual":metrics(y[te],gp),
         "feature_scaling":"train-only median/IQR clipped [-10,10]","target_scaling":{"mean":dm,"std":ds},"split":"chronological 60/20/20","tls_embedding_dim":4}
    # per TLS and operating-hour diagnostics
    per={}
    for tid in sorted(set(tids[te].tolist())):
        m=tids[te]==tid;per[tid]={"n":int(m.sum()),"persistence":metrics(y[te][m],pers[m]),"GRU_v2":metrics(y[te][m],gp[m])}
    out["per_tls"]=per
    with open(os.path.join(args.outdir,"gru_v2_validation.json"),"w") as f:json.dump(out,f,indent=2)
    with open(os.path.join(args.outdir,"gru_v2_history.csv"),"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["epoch","train_loss","val_loss"]);w.writeheader();w.writerows(hist)
    with open(os.path.join(args.outdir,"gru_v2_predictions.csv"),"w",newline="") as f:
        w=csv.writer(f);w.writerow(["time_s","tls_id","truth","persistence","linear_time_residual","gru_v2"])
        for z in zip(times[te],tids[te],y[te],pers,linpred,gp):w.writerow(z)
    torch.save({"state_dict":model.state_dict(),"metrics":out,"feature_median":med,"feature_iqr":iqr,"tls_order":tid_order},os.path.join(args.outdir,"gru_v2_residual.pt"))
    print(json.dumps(out,indent=2))

if __name__=="__main__":main()
