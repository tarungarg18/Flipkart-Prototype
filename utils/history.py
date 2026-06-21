import json
import os
import uuid
from datetime import datetime

_FILE_PRIMARY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prediction_history.json")
_FILE_TMP     = "/tmp/prediction_history.json"

def _history_file():
    parent = os.path.dirname(_FILE_PRIMARY)
    return _FILE_PRIMARY if os.access(parent, os.W_OK) else _FILE_TMP

_FILE = _history_file()


def load():
    if not os.path.exists(_FILE):
        return []
    try:
        with open(_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(data):
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


def add(inputs, result):
    data = load()
    safe_inputs = {}
    for k, v in inputs.items():
        if isinstance(v, (str, int, float, bool, list, dict, type(None))):
            safe_inputs[k] = v
        else:
            safe_inputs[k] = str(v)
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().isoformat(),
        "inputs": safe_inputs,
        "result": result,
        "actuals": None,
    }
    data.append(entry)
    _save(data)
    return entry["id"]


def update_actuals(entry_id, actuals):
    data = load()
    for entry in data:
        if entry["id"] == entry_id:
            entry["actuals"] = actuals
            break
    _save(data)


def delete_entry(entry_id):
    data = load()
    data = [e for e in data if e["id"] != entry_id]
    _save(data)
