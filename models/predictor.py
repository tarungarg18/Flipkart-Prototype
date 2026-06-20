import os
import math

BANGALORE_CENTER = (12.9716, 77.5946)

EVENT_CAUSE_MAP = {
    "Accident":             "event_cause_accident",
    "Congestion":           "event_cause_congestion",
    "Construction":         "event_cause_construction",
    "Debris":               "event_cause_debris",
    "Fog / Low Visibility": "event_cause_fog_/_low_visibility",
    "Others":               "event_cause_others",
    "Pot Holes":            "event_cause_pot_holes",
    "Procession":           "event_cause_procession",
    "Protest":              "event_cause_protest",
    "Public Event":         "event_cause_public_event",
    "Road Conditions":      "event_cause_road_conditions",
    "Tree Fall":            "event_cause_tree_fall",
    "Vehicle Breakdown":    "event_cause_vehicle_breakdown",
    "VIP Movement":         "event_cause_vip_movement",
    "Water Logging":        "event_cause_water_logging",
}

CAUSE_COLS = [
    "event_cause_accident", "event_cause_congestion", "event_cause_construction",
    "event_cause_debris", "event_cause_fog_/_low_visibility", "event_cause_others",
    "event_cause_pot_holes", "event_cause_procession", "event_cause_protest",
    "event_cause_public_event", "event_cause_road_conditions", "event_cause_tree_fall",
    "event_cause_vehicle_breakdown", "event_cause_vip_movement", "event_cause_water_logging",
]

ALL_COLS = [
    "latitude", "longitude", "priority_num", "endlatitude", "endlongitude",
    "requires_road_closure", "hour_of_day", "day_of_week", "month",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "is_night", "is_weekend", "is_monsoon", "is_unresolved",
    "is_heavy_vehicle", "is_highway", "dist_to_center_km", "is_on_corridor",
    "location_cluster", "cluster_event_density", "has_junction",
    "junction_freq", "station_event_freq", "cause_tier",
    "zone_priority_rate", "corridor_priority_rate", "cluster_priority_rate",
    "rush_x_corridor", "tier_x_corridor", "heavy_x_closure",
] + CAUSE_COLS + [
    "event_type_planned", "event_type_unplanned",
    "veh_type_bmtc_bus", "veh_type_car", "veh_type_heavy_vehicle",
    "veh_type_ksrtc_bus", "veh_type_lcv", "veh_type_others",
    "veh_type_private_bus", "veh_type_private_car",
    "veh_type_three_wheeler", "veh_type_truck",
    "zone_central_zone_1", "zone_central_zone_2",
    "zone_east_zone_1", "zone_east_zone_2",
    "zone_north_zone_1", "zone_north_zone_2",
    "zone_south_zone_1", "zone_south_zone_2",
    "zone_west_zone_1", "zone_west_zone_2",
    "hour_peak_prox", "junction_freq_norm", "cluster_density_norm",
    "escalation_index", "volume_pc1_norm",
]

_sev_model = None
_clos_model = None
_loaded = False


def _load():
    global _sev_model, _clos_model, _loaded
    if _loaded:
        return
    _loaded = True
    try:
        import joblib
        base = os.path.dirname(__file__)
        for name in ["severity_prediction.pkl", "severity.pkl", "model.pkl"]:
            p = os.path.join(base, "Severity", name)
            if os.path.exists(p):
                _sev_model = joblib.load(p)
                break
        for name in ["road_closure.pkl", "road_closure_prediction.pkl", "model.pkl"]:
            p = os.path.join(base, "Road_Closure", name)
            if os.path.exists(p):
                _clos_model = joblib.load(p)
                break
    except Exception:
        pass


def _build_features(inputs, include_closure=True):
    import pandas as pd
    from datetime import datetime

    dt = datetime.fromisoformat(inputs["start_datetime"])
    h, d, m = dt.hour, dt.weekday(), dt.month
    lat = float(inputs.get("latitude") or BANGALORE_CENTER[0])
    lon = float(inputs.get("longitude") or BANGALORE_CENTER[1])
    dist = math.sqrt((lat - BANGALORE_CENTER[0]) ** 2 + (lon - BANGALORE_CENTER[1]) ** 2) * 111.32
    planned = int(inputs.get("event_type", "") == "Planned")
    cause_col = EVENT_CAUSE_MAP.get(inputs.get("event_cause", ""), "event_cause_others")

    row = {c: 0 for c in ALL_COLS}
    row.update({
        "latitude":             lat,
        "longitude":            lon,
        "hour_of_day":          h,
        "day_of_week":          d,
        "month":                m,
        "hour_sin":             math.sin(2 * math.pi * h / 24),
        "hour_cos":             math.cos(2 * math.pi * h / 24),
        "dow_sin":              math.sin(2 * math.pi * d / 7),
        "dow_cos":              math.cos(2 * math.pi * d / 7),
        "is_night":             int(h < 6 or h >= 20),
        "is_weekend":           int(d >= 5),
        "is_monsoon":           int(m in [6, 7, 8, 9]),
        "dist_to_center_km":    dist,
        "event_type_planned":   planned,
        "event_type_unplanned": 1 - planned,
        cause_col:              1,
        "veh_type_car":         1,
    })
    if include_closure:
        row["requires_road_closure"] = int(inputs.get("road_closure", True))

    return pd.DataFrame([row])


def _run(model, df):
    if hasattr(model, "feature_names_in_"):
        cols = list(model.feature_names_in_)
        for c in cols:
            if c not in df.columns:
                df[c] = 0
        return model.predict(df[cols])[0]
    return model.predict(df)[0]


def predict(inputs):
    _load()

    if _sev_model is None or _clos_model is None:
        return {"ok": False, "error": "Prediction models are not available right now."}

    try:
        df_c = _build_features(inputs, include_closure=False)
        road_closure = bool(_run(_clos_model, df_c))

        df_s = _build_features({**inputs, "road_closure": road_closure}, include_closure=True)
        raw = float(_run(_sev_model, df_s))
        severity = round(max(0.0, min(10.0, raw)), 1)
    except Exception:
        return {"ok": False, "error": "Unable to predict right now. Please try again."}

    return {"ok": True, "severity": severity, "road_closure": road_closure}
