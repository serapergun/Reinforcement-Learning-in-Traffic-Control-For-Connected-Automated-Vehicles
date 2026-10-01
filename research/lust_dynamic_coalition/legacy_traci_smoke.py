#!/usr/bin/env python3
"""
Minimal Python-3 TraCI compatibility smoke for SUMO 0.27.0.

This intentionally uses only APIs required by the later nine-TLS controller/data
collector and writes a machine-readable capability report.
"""
import argparse, json, os, sys, traceback

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sumo", required=True)
    ap.add_argument("--sumo-tools", required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--begin", type=int, default=28800)
    ap.add_argument("--duration", type=int, default=120)
    args=ap.parse_args()

    sys.path.insert(0, os.path.abspath(args.sumo_tools))
    import traci

    tl_domain = getattr(traci, "trafficlights", None)
    if tl_domain is None:
        tl_domain = getattr(traci, "trafficlight", None)
    assert tl_domain is not None, "No TraCI traffic-light domain"

    cfg=os.path.join(os.path.abspath(args.scenario),"due.actuated.sumocfg")
    cmd=[os.path.abspath(args.sumo),"-c",cfg,
         "--begin",str(args.begin),"--end",str(args.begin+args.duration)]
    report={"command":cmd,"python":sys.version,"checks":{}}
    traci.start(cmd)
    try:
        tls=list(tl_domain.getIDList())
        lanes=list(traci.lane.getIDList())
        report["checks"]["tls_count"]=len(tls)
        report["checks"]["lane_count"]=len(lanes)
        assert tls and lanes

        tl=tls[0]; lane=lanes[0]
        def now_s():
            sim=traci.simulation
            if hasattr(sim,"getTime"):
                return float(sim.getTime())
            return float(sim.getCurrentTime())/1000.0

        report["checks"]["time_start_s"]=now_s()
        report["checks"]["tls_sample"]=tl
        report["checks"]["tls_phase"]=int(tl_domain.getPhase(tl))
        report["checks"]["tls_state"]=str(tl_domain.getRedYellowGreenState(tl))
        ns=float(tl_domain.getNextSwitch(tl))
        pd=float(tl_domain.getPhaseDuration(tl))
        # SUMO 0.27 TraCI encodes TLS times in ms; newer versions use seconds.
        if ns > 1e6:
            ns/=1000.0
        if pd > 1e4:
            pd/=1000.0
        report["checks"]["tls_next_switch_s"]=ns
        report["checks"]["tls_phase_duration_s"]=pd
        report["checks"]["lane_sample"]=lane
        report["checks"]["lane_vehicle_number"]=int(traci.lane.getLastStepVehicleNumber(lane))
        report["checks"]["lane_halting_number"]=int(traci.lane.getLastStepHaltingNumber(lane))
        report["checks"]["lane_mean_speed"]=float(traci.lane.getLastStepMeanSpeed(lane))
        report["checks"]["lane_occupancy"]=float(traci.lane.getLastStepOccupancy(lane))
        report["checks"]["lane_waiting_time"]=float(traci.lane.getWaitingTime(lane))
        report["checks"]["lane_co2"]=float(traci.lane.getCO2Emission(lane))
        report["checks"]["min_expected"]=int(traci.simulation.getMinExpectedNumber())

        # Advance using the legacy simulationStep API and confirm clock movement.
        t0=now_s()
        for _ in range(10):
            traci.simulationStep()
        t1=now_s()
        report["checks"]["time_after_10_steps_s"]=t1
        report["checks"]["clock_delta_s"]=t1-t0
        assert 9.0 <= t1-t0 <= 11.0

        # Read-only vehicle API needed by probe/V2X sampling.
        vids=list(traci.vehicle.getIDList())
        report["checks"]["vehicle_count"]=len(vids)
        if vids:
            v=vids[0]
            report["checks"]["vehicle_sample"]=v
            report["checks"]["vehicle_waiting_time"]=float(traci.vehicle.getWaitingTime(v))

        report["ok"]=True
    except Exception as e:
        report["ok"]=False
        report["error"]=repr(e)
        report["traceback"]=traceback.format_exc()
        raise
    finally:
        try: traci.close()
        finally:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)),exist_ok=True)
            with open(args.out,"w") as f: json.dump(report,f,indent=2)
            print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
