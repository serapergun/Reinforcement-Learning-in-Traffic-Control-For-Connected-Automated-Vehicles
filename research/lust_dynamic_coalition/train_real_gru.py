#!/usr/bin/env python3
import argparse, csv, json, math, os, random
import numpy as np

def load_rows(path):
    rows=[]
    with open(path,newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in ["time_s","veh_count","halting_count","mean_speed_mps","mean_occupancy_pct","waiting_time_s","co2_mg_s"]:
                r[k]=float(r[k])
            rows.append(r)
    return rows

def metrics(y,p):
    y=np.asarray(y,float); p=np.asarray(p,float)
    mae=float(np.mean(np.abs(y-p)))
    rmse=float(np.sqrt(np.mean((y-p)**2)))
    den=float(np.sum((y-y.mean())**2))
    r2=float(1-np.sum((y-p)**2)/den) if den>0 else 0.0
    return {"MAE":mae,"RMSE":rmse,"R2":r2}

def make_sequences(rows,L=30,h=6):
    by={}
    for r in rows:
        by.setdefault(r["tls_id"],[]).append(r)
    X=[]; y=[]; times=[]; tls=[]
    # Predictive inputs are limited to traffic-state variables that can be mapped to stakeholder data channels.\n    # CO2 is retained as an evaluation/resource outcome, not used as a GRU predictor.\n    feats=["veh_count","halting_count","mean_speed_mps","mean_occupancy_pct","waiting_time_s"]
    for tid,rs in by.items():
        rs=sorted(rs,key=lambda x:x["time_s"])
        arr=np.array([[r[k] for k in feats] for r in rs],dtype=np.float32)
        target=np.array([r["halting_count"] for r in rs],dtype=np.float32)
        for i in range(L-1,len(rs)-h):
            if rs[i+h]["time_s"]-rs[i]["time_s"] > (h*10+1):
                continue
            X.append(arr[i-L+1:i+1]); y.append(target[i+h]); times.append(rs[i]["time_s"]); tls.append(tid)
    return np.asarray(X),np.asarray(y),np.asarray(times),np.asarray(tls),feats

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",required=True)
    ap.add_argument("--outdir",required=True)
    ap.add_argument("--epochs",type=int,default=25)
    ap.add_argument("--seed",type=int,default=42)
    args=ap.parse_args()
    os.makedirs(args.outdir,exist_ok=True)
    random.seed(args.seed); np.random.seed(args.seed)
    import torch
    import torch.nn as nn
    torch.manual_seed(args.seed)

    rows=load_rows(args.data)
    X,y,times,tls,feats=make_sequences(rows,L=30,h=6)
    # chronological split prevents future-to-past leakage
    q1=np.quantile(times,0.60); q2=np.quantile(times,0.80)
    train=times<=q1; val=(times>q1)&(times<=q2); test=times>q2

    mu=X[train].reshape(-1,X.shape[-1]).mean(0)
    sd=X[train].reshape(-1,X.shape[-1]).std(0)+1e-6
    Xn=(X-mu)/sd

    persistence=X[test,-1,1]
    persist_m=metrics(y[test],persistence)

    class GRU(nn.Module):
        def __init__(self,d):
            super().__init__()
            self.gru=nn.GRU(d,64,batch_first=True)
            self.head=nn.Sequential(nn.Linear(64,32),nn.ReLU(),nn.Linear(32,1))
        def forward(self,x):
            z,_=self.gru(x)
            return self.head(z[:,-1]).squeeze(-1)

    model=GRU(X.shape[-1])
    opt=torch.optim.Adam(model.parameters(),lr=1e-3)
    loss_fn=nn.MSELoss()
    batch=512

    Xt=torch.tensor(Xn[train],dtype=torch.float32); yt=torch.tensor(y[train],dtype=torch.float32)
    Xv=torch.tensor(Xn[val],dtype=torch.float32); yv=torch.tensor(y[val],dtype=torch.float32)
    best=None; best_loss=float("inf")
    history=[]
    for ep in range(args.epochs):
        model.train()
        perm=torch.randperm(len(Xt))
        losses=[]
        for st in range(0,len(Xt),batch):
            idx=perm[st:st+batch]
            pred=model(Xt[idx]); loss=loss_fn(pred,yt[idx])
            opt.zero_grad(); loss.backward(); opt.step()
            losses.append(float(loss.detach()))
        model.eval()
        with torch.no_grad():
            vl=float(loss_fn(model(Xv),yv))
        history.append({"epoch":ep+1,"train_mse":float(np.mean(losses)),"val_mse":vl})
        if vl<best_loss:
            best_loss=vl
            best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        print(history[-1],flush=True)
    if best: model.load_state_dict(best)
    model.eval()
    with torch.no_grad():
        pred=model(torch.tensor(Xn[test],dtype=torch.float32)).numpy()
    gru_m=metrics(y[test],pred)
    out={
        "target":"halting_count_60s_ahead",
        "history_steps":30,"history_seconds":300,"horizon_steps":6,"horizon_seconds":60,
        "features":feats,"samples_total":int(len(y)),
        "samples_train":int(train.sum()),"samples_val":int(val.sum()),"samples_test":int(test.sum()),
        "persistence":persist_m,"GRU":gru_m,
        "normalization_mean":mu.tolist(),"normalization_std":sd.tolist(),
        "split":"chronological 60/20/20 on a single real SUMO run; later multi-seed evaluation remains required"
    }
    with open(os.path.join(args.outdir,"gru_validation.json"),"w") as f: json.dump(out,f,indent=2)
    with open(os.path.join(args.outdir,"gru_training_history.csv"),"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["epoch","train_mse","val_mse"]);w.writeheader();w.writerows(history)
    torch.save({"state_dict":model.state_dict(),"metrics":out},os.path.join(args.outdir,"gru_queue60s.pt"))
    with open(os.path.join(args.outdir,"gru_test_predictions.csv"),"w",newline="") as f:
        w=csv.writer(f);w.writerow(["time_s","tls_id","truth","persistence","gru"])
        for a,b,c,d,e in zip(times[test],tls[test],y[test],persistence,pred):w.writerow([a,b,c,d,e])
    print(json.dumps(out,indent=2))

if __name__=="__main__":
    main()
