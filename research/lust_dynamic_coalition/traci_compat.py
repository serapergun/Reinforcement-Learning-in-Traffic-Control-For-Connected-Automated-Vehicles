#!/usr/bin/env python3
"""Compatibility adapter for SUMO 0.27-era and modern TraCI APIs.

It covers only the API surface used by this study, normalizes legacy
millisecond-based traffic-light/simulation times to seconds, and maps the
historical trafficlights domain to the modern trafficlight name.
"""

class TraCICompat:
    def __init__(self, traci_module):
        self.traci = traci_module
        self.tl = getattr(traci_module, "trafficlight", None)
        if self.tl is None:
            self.tl = getattr(traci_module, "trafficlights", None)
        if self.tl is None:
            raise RuntimeError("Traffic-light TraCI domain unavailable")
        self.legacy_time = not hasattr(self.traci.simulation, "getTime")

    def start(self, cmd):
        return self.traci.start(cmd)

    def close(self):
        return self.traci.close()

    def step(self):
        return self.traci.simulationStep()

    def time_s(self):
        if hasattr(self.traci.simulation, "getTime"):
            return float(self.traci.simulation.getTime())
        return float(self.traci.simulation.getCurrentTime()) / 1000.0

    def min_expected(self):
        return int(self.traci.simulation.getMinExpectedNumber())

    def arrived_number(self):
        return int(self.traci.simulation.getArrivedNumber())

    def tls_ids(self):
        return list(self.tl.getIDList())

    def phase(self, tls_id):
        return int(self.tl.getPhase(tls_id))

    def phase_state(self, tls_id):
        return str(self.tl.getRedYellowGreenState(tls_id))

    def next_switch_s(self, tls_id):
        value = float(self.tl.getNextSwitch(tls_id))
        return value / 1000.0 if self.legacy_time else value

    def phase_duration_s(self, tls_id):
        value = float(self.tl.getPhaseDuration(tls_id))
        return value / 1000.0 if self.legacy_time else value

    def spent_duration_s(self, tls_id):
        if hasattr(self.tl, "getSpentDuration"):
            return float(self.tl.getSpentDuration(tls_id))
        remaining = max(0.0, self.next_switch_s(tls_id) - self.time_s())
        return max(0.0, self.phase_duration_s(tls_id) - remaining)

    def set_phase_duration_s(self, tls_id, seconds):
        return self.tl.setPhaseDuration(tls_id, float(seconds))

    def lane_vehicle_number(self, lane):
        return int(self.traci.lane.getLastStepVehicleNumber(lane))

    def lane_halting_number(self, lane):
        return int(self.traci.lane.getLastStepHaltingNumber(lane))

    def lane_speed(self, lane):
        return float(self.traci.lane.getLastStepMeanSpeed(lane))

    def lane_occupancy(self, lane):
        return float(self.traci.lane.getLastStepOccupancy(lane))

    def lane_waiting(self, lane):
        return float(self.traci.lane.getWaitingTime(lane))

    def lane_co2(self, lane):
        return float(self.traci.lane.getCO2Emission(lane))

    def vehicle_ids(self):
        return list(self.traci.vehicle.getIDList())

    def vehicle_waiting(self, vehicle_id):
        return float(self.traci.vehicle.getWaitingTime(vehicle_id))
