import random


def predict_severity_score(inputs: dict) -> float:
    """
    Predicts traffic severity score (0.0 – 10.0).
    Replace this stub with real model inference.
    Expected keys: latitude, longitude, event_type, event_cause, start_datetime, road_closure
    """
    random.seed(hash(str(inputs)) % 100_000)
    return round(random.uniform(2.0, 9.5), 1)
