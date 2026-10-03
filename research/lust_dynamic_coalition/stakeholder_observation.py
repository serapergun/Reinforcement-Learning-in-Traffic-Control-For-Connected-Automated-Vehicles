#!/usr/bin/env python3
"""Deterministic stakeholder observation adapter for LuST/SUMO 0.27.
TA=infrastructure detector state; MO=20% mobility probes; VI=75% connected vehicles;
EC=validated 60-s persistence forecast. Controller safety state is not a stakeholder channel.
"""
import hashlib, numpy as np
PLAYERS=("TA","MO","VI","EC")
P_FCD=.20
P_V2X=.75

def stable_keep(seed,tls_id,vehicle_id,channel,p):
    key=f"{int(seed)}|{tls_id}|{vehicle_id}|{channel}".encode()
    u=int(hashlib.sha1(key).hexdigest()[:15],16)/float(16**15-1)
    return u < float(p)

def feasible_coalitions():
    out=[]
    for bits in range(1,16):
        c=tuple(p for i,p in enumerate(PLAYERS) if bits&(1<<i))
        if c!=("EC",): out.append(c)
    return out

class StakeholderObservation:
    """Build policy information without leaking exact TA state into absent coalitions."""
    def __init__(self,env,coalition,seed):
        self.env=env; self.c=set(coalition); self.seed=int(seed)
        self.last_queue={}

    @property
    def dim(self): return 14

    def _vehicles_on_lanes(self,lanes):
        tc=self.env.tc; ids=[]
        # SUMO 0.27 lane domain exposes getLastStepVehicleIDs.
        fn=getattr(tc.traci.lane,"getLastStepVehicleIDs",None)
        if fn is None: return ids
        for lane in lanes:
            try: ids.extend(list(fn(lane)))
            except Exception: pass
        return sorted(set(ids))

    def _vehicle_speed(self,vid):
        try:return float(self.env.tc.traci.vehicle.getSpeed(vid))
        except Exception:return 0.

    def _vehicle_wait(self,vid):
        try:return float(self.env.tc.vehicle_waiting(vid))
        except Exception:return 0.

    def one(self,tl):
        s=self.env.lane_stats(tl); lanes=self.env.inc[tl]; vids=self._vehicles_on_lanes(lanes)
        # TA exact infrastructure state.
        ta=[s["veh"]/max(12*s["lanes"],1),s["halt"]/max(8*s["lanes"],1),
            s["occ"]/100.,s["waiting"]/max(300*s["lanes"],1)] if "TA" in self.c else [0.]*4
        # MO: deterministic 20% probe mobility information.
        moids=[v for v in vids if stable_keep(self.seed,tl,v,"MO",P_FCD)]
        mos=[self._vehicle_speed(v) for v in moids]
        mow=[self._vehicle_wait(v) for v in moids]
        mo=[len(moids)/max(len(vids),1), (sum(mos)/max(len(mos),1))/15.,
            (sum(mow)/max(len(mow),1))/60.] if "MO" in self.c else [0.]*3
        # VI: deterministic 75% connected-vehicle availability and stopped fraction.
        vids2=[v for v in vids if stable_keep(self.seed,tl,v,"VI",P_V2X)]
        vis=[self._vehicle_speed(v) for v in vids2]
        vi=[len(vids2)/max(len(vids),1),sum(x<.1 for x in vis)/max(len(vis),1)] if "VI" in self.c else [0.]*2
        # EC: validated persistence q(t+60)=q(t), using an available coalition queue estimate.
        q_est=None
        if "TA" in self.c:q_est=float(s["halt"])
        elif "VI" in self.c:q_est=float(sum(x<.1 for x in vis))/P_V2X
        elif "MO" in self.c:q_est=float(sum(x<.1 for x in mos))/P_FCD
        ec=[np.clip(q_est/max(8*s["lanes"],1),0,3)] if ("EC" in self.c and q_est is not None) else [0.]
        mask=[1. if p in self.c else 0. for p in PLAYERS]
        x=np.asarray(ta+mo+vi+ec+mask,dtype=np.float32)
        return np.clip(x,0,5)

    def observe(self):
        return np.stack([self.one(tl) for tl in self.env.tls])
