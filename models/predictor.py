from datetime import datetime
from models import runtime

CAUSE_LABEL_MAP = {
    "Accident":             "accident",
    "Congestion":           "congestion",
    "Construction":         "construction",
    "Debris":               "debris",
    "Fog / Low Visibility": "fog_low_visibility",
    "Pot Holes":            "pot_holes",
    "Procession":           "procession",
    "Protest":              "protest",
    "Public Event":         "public_event",
    "Road Conditions":      "road_conditions",
    "Tree Fall":            "tree_fall",
    "Vehicle Breakdown":    "vehicle_breakdown",
    "VIP Movement":         "vip_movement",
    "Water Logging":        "water_logging",
    "Others":               "others",
}


def _detect_corridor(address):
    if not address:
        return None, 0
    cleaned = runtime.clean_key(address)
    best = None
    for key in runtime.corridor_keys():
        if key == "non_corridor":
            continue
        if key in cleaned and (best is None or len(key) > len(best)):
            best = key
    if best:
        return best, 1
    return None, 0


def predict(inputs):
    if not runtime.available():
        return {"ok": False, "error": "Prediction models are not available right now."}

    try:
        dt = datetime.fromisoformat(inputs["start_datetime"])
        cause = CAUSE_LABEL_MAP.get(inputs.get("event_cause", ""), "others")

        selection = inputs.get("selection") or []
        if selection:
            lat = selection[0]["lat"]
            lng = selection[0]["lng"]
            if len(selection) > 1:
                endlat = selection[-1]["lat"]
                endlng = selection[-1]["lng"]
            else:
                endlat = endlng = None
        else:
            lat = inputs.get("latitude")
            lng = inputs.get("longitude")
            endlat = endlng = None

        corridor_name, is_on_corridor = _detect_corridor(inputs.get("address"))

        return runtime.infer(
            cause=cause,
            hour=dt.hour,
            day_of_week=dt.weekday(),
            latitude=lat,
            longitude=lng,
            endlatitude=endlat,
            endlongitude=endlng,
            is_on_corridor=is_on_corridor,
            zone_name=None,
            corridor_name=corridor_name,
            veh_type=inputs.get("veh_type"),
            event_type=inputs.get("event_type", "Unplanned"),
        )
    except Exception:
        return {"ok": False, "error": "Unable to predict right now. Please try again."}
