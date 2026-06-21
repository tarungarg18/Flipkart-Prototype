import os
import re
import numpy as np

_ART = None
BLR_CENTER_LAT, BLR_CENTER_LON = 12.9716, 77.5946


def _dir():
    return os.path.dirname(__file__)


def available():
    need = ["closure_classifier.joblib", "severity_regressor.joblib",
            "closure_features.joblib", "severity_features.joblib", "runtime_lookups.joblib"]
    return all(os.path.exists(os.path.join(_dir(), n)) for n in need)


def _load():
    global _ART
    if _ART is not None:
        return _ART
    import joblib
    d = _dir()
    lk = joblib.load(os.path.join(d, "runtime_lookups.joblib"))
    _ART = {
        "clf": joblib.load(os.path.join(d, "closure_classifier.joblib")),
        "reg": joblib.load(os.path.join(d, "severity_regressor.joblib")),
        "closure_features": joblib.load(os.path.join(d, "closure_features.joblib")),
        "severity_features": joblib.load(os.path.join(d, "severity_features.joblib")),
        **lk,
    }
    return _ART


def clean_key(s):
    s = str(s).strip().lower()
    return re.sub(r"[\s\-]+", "_", s)


def haversine_km(lat, lon, clat=BLR_CENTER_LAT, clon=BLR_CENTER_LON):
    R = 6371.0
    dlat = np.radians(lat - clat)
    dlon = np.radians(lon - clon)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(clat)) * np.cos(np.radians(lat)) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def _lookup_rate(rate_dict, raw_value, fallback):
    if raw_value is None:
        return fallback
    return rate_dict.get(clean_key(raw_value), fallback)


def calculate_barricades(severity, closure_proba, incident_span_m, is_on_corridor, threshold, params):
    severity = float(np.clip(severity, 0, 10))
    closure_proba = float(np.clip(closure_proba, 0, 1))
    incident_span_m = max(0.0, float(incident_span_m))

    closure_gravity = 0.0
    if closure_proba >= threshold:
        closure_gravity = (closure_proba - threshold) / (1 - threshold)

    severity_term = 1 + params["GRAVITY_K_SEVERITY"] * (severity / 10) ** params["GRAVITY_P_SEVERITY"]
    closure_term = 1 + params["GRAVITY_K_CLOSURE"] * closure_gravity
    span_term = 1 + params["GRAVITY_K_SPAN"] * (incident_span_m / params["SPAN_SCALE_M"]) ** params["GRAVITY_P_SPAN"]
    corridor_term = (1 + params["CORRIDOR_GRAVITY_BONUS"]) if is_on_corridor else 1.0

    raw = params["BARRICADE_BASE"] * severity_term * closure_term * span_term * corridor_term
    return int(np.clip(round(raw), params["BARRICADE_FLOOR"], params["BARRICADE_CEILING"]))


def recommend_manpower(severity, cause_tier):
    total = max(2, int(round(2 * np.exp(severity * 0.32))))
    if severity >= 7.5 or cause_tier >= 0.9:
        inspectors = max(1, int(total * 0.1))
        hc = max(2, int(total * 0.3))
        pc = total - (inspectors + hc)
        text = f"{total} Units ({inspectors} Inspector, {hc} HC, {pc} PC) [SECTOR COMMAND]"
    elif severity >= 4.5:
        hc = max(1, int(total * 0.25))
        pc = total - hc
        text = f"{total} Units ({hc} Head Constable, {pc} PC)"
    else:
        text = f"{total} Police Constables (Routine Lane Management)"
    return {"total": total, "display_text": text}


def recommend_diversion(severity, barricades, is_on_corridor):
    if barricades >= 25 and is_on_corridor:
        return "Fully close the primary corridor segment. Reroute inbound traffic to parallel ring arterials."
    if severity >= 5.5:
        return "Enforce multi-point perimeter filtering. Restrict heavy transit vehicles at preceding sub-junctions."
    if barricades > 10:
        return "Deploy single-lane bottlenecks. No macro route alterations required."
    return "Maintain standard stream. Handle locally with directional flag points."


def _build_row(a, cause, hour, day_of_week, latitude, longitude,
               endlatitude, endlongitude, is_on_corridor, zone_name, corridor_name, veh_type):
    import pandas as pd

    is_on_corridor = int(bool(is_on_corridor))
    hour = int(hour) % 24
    day_of_week = int(day_of_week) % 7

    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)
    dow_sin = np.sin(2 * np.pi * day_of_week / 7)
    dow_cos = np.cos(2 * np.pi * day_of_week / 7)
    is_night = 1 if (hour >= 22 or hour <= 5) else 0
    is_weekend = 1 if day_of_week >= 5 else 0
    is_rush = 1 if (7 <= hour <= 10 or 17 <= hour <= 21) else 0
    hour_peak_prox = (9 - min(abs(hour - 9), abs(hour - 18))) / 9

    dist_to_center_km = float(haversine_km(np.array([latitude]), np.array([longitude]))[0])
    location_cluster = int(a["kmeans"].predict([[latitude, longitude]])[0])
    cluster_density_val = float(a["cluster_density"].get(location_cluster, a["cluster_density_mean_train"]))
    cluster_density_norm = float(a["cd_scaler"].transform([[cluster_density_val]])[0, 0])
    cluster_priority_rate_val = a["cluster_rate_dict"].get(location_cluster, a["global_mean"])

    cause_norm = clean_key(cause)
    cause_tier_val = a["CAUSE_TIER"].get(cause_norm, a["DEFAULT_TIER"])

    veh_type_norm = clean_key(veh_type) if veh_type is not None else "unknown"
    veh_type_mapped = a["VEH_MAP"].get(veh_type_norm, veh_type_norm)
    is_heavy_vehicle = int(bool(re.search(a["HEAVY_PATTERN"], veh_type_mapped)))

    zone_priority_rate_val = _lookup_rate(a["zone_rate_dict"], zone_name, a["global_mean"])
    corridor_priority_rate_val = (
        _lookup_rate(a["corridor_rate_dict"], corridor_name, a["global_mean"])
        if is_on_corridor else a["corridor_rate_dict"].get("non_corridor", a["global_mean"])
    )

    if endlatitude is None or endlongitude is None or endlatitude == 0 or endlongitude == 0:
        incident_span_m = 0.0
    else:
        incident_span_m = float(haversine_m(latitude, longitude, endlatitude, endlongitude))
        if np.isnan(incident_span_m):
            incident_span_m = 0.0

    junction_freq_norm_default = float(a["jf_scaler"].transform([[1]])[0, 0])

    values = {
        "latitude": latitude, "longitude": longitude,
        "incident_span_m": incident_span_m,
        "day_of_week": day_of_week, "month": 6,
        "hour_sin": hour_sin, "hour_cos": hour_cos, "dow_sin": dow_sin, "dow_cos": dow_cos,
        "is_night": is_night, "is_weekend": is_weekend, "is_monsoon": 0,
        "is_unresolved": 1, "is_heavy_vehicle": is_heavy_vehicle, "is_highway": 0,
        "dist_to_center_km": dist_to_center_km, "is_on_corridor": is_on_corridor,
        "location_cluster": location_cluster,
        "has_junction": 0, "junction_freq_norm": junction_freq_norm_default,
        "station_event_freq": 1,
        "cause_tier": cause_tier_val,
        "zone_priority_rate": zone_priority_rate_val,
        "corridor_priority_rate": corridor_priority_rate_val,
        "cluster_priority_rate": cluster_priority_rate_val,
        "rush_x_corridor": is_rush * is_on_corridor,
        "is_rush": is_rush,
        "hour_peak_prox": hour_peak_prox,
        "cluster_density_norm": cluster_density_norm,
    }

    row = pd.DataFrame(0, index=[0], columns=a["closure_features"], dtype=float)
    for k, v in values.items():
        if k in row.columns:
            row[k] = v

    cause_col = "event_cause_" + cause_norm
    if cause_col in row.columns:
        row[cause_col] = 1
    zone_col = ("zone_" + clean_key(zone_name)) if zone_name else None
    if zone_col and zone_col in row.columns:
        row[zone_col] = 1
    veh_col = "veh_type_" + veh_type_mapped
    if veh_col in row.columns:
        row[veh_col] = 1

    return row, location_cluster, dist_to_center_km, incident_span_m, is_heavy_vehicle


def infer(cause, hour, day_of_week, latitude, longitude,
          endlatitude=None, endlongitude=None, is_on_corridor=0,
          zone_name=None, corridor_name=None, veh_type=None, event_type="Unplanned"):
    a = _load()

    row, cluster_id, dist_km, span_m, is_heavy = _build_row(
        a, cause, hour, day_of_week, latitude, longitude,
        endlatitude, endlongitude, is_on_corridor, zone_name, corridor_name, veh_type,
    )

    et_col = "event_type_" + clean_key(event_type)
    if et_col in row.columns:
        row[et_col] = 1

    threshold = a["CLOSURE_DECISION_THRESHOLD"]
    closure_proba = float(a["clf"].predict_proba(row)[0, 1])
    closure_pred = int(closure_proba >= threshold)

    sev_row = row.reindex(columns=a["severity_features"], fill_value=0)
    sev_row.loc[0, "requires_road_closure"] = closure_pred
    if "heavy_x_closure" in sev_row.columns:
        sev_row.loc[0, "heavy_x_closure"] = is_heavy * closure_pred

    severity = float(np.clip(a["reg"].predict(sev_row)[0], 0, 10))
    barricades = calculate_barricades(severity, closure_proba, span_m, bool(is_on_corridor),
                                      threshold, a["barricade_params"])

    cause_tier_val = a["CAUSE_TIER"].get(clean_key(cause), a["DEFAULT_TIER"])
    manpower = recommend_manpower(severity, cause_tier_val)
    diversion = recommend_diversion(severity, barricades, is_on_corridor)

    return {
        "ok": True,
        "severity": round(severity, 1),
        "road_closure": bool(closure_pred),
        "closure_prob": closure_proba,
        "incident_span_m": span_m,
        "is_heavy_vehicle": bool(is_heavy),
        "barricades": barricades,
        "manpower_count": manpower["total"],
        "manpower_deployment": manpower["display_text"],
        "diversion_plan": diversion,
        "cluster_id": cluster_id,
        "is_on_corridor": bool(is_on_corridor),
    }


def corridor_keys():
    return list(_load()["corridor_rate_dict"].keys())


def info():
    a = _load()
    return {
        "closure_threshold": a["CLOSURE_DECISION_THRESHOLD"],
        "cause_tier": a["CAUSE_TIER"],
        "default_tier": a["DEFAULT_TIER"],
        "barricade_params": a["barricade_params"],
        "corridors": sorted(k for k in a["corridor_rate_dict"].keys() if k != "non_corridor"),
    }
