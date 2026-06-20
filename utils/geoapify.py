import requests
import streamlit as st


def _key():
    try:
        return st.secrets.get("GEOAPIFY_KEY") or st.secrets.get("Geoapify", "") or ""
    except Exception:
        return ""


def search_places(query):
    key = _key()
    if not key or len(query) < 3:
        return []
    try:
        r = requests.get(
            "https://api.geoapify.com/v1/geocode/autocomplete",
            params={
                "text": query,
                "apiKey": key,
                "bias": "proximity:77.5946,12.9716",
                "lang": "en",
                "limit": 6,
                "filter": "countrycode:in",
            },
            timeout=6,
        )
        if r.ok:
            out = []
            for f in r.json().get("features", []):
                p = f["properties"]
                lat = p.get("lat")
                lon = p.get("lon")
                if lat is not None and lon is not None:
                    out.append({
                        "label": p.get("formatted", ""),
                        "lat": float(lat),
                        "lon": float(lon),
                    })
            return out
    except Exception:
        pass
    return []


def reverse_geocode(lat, lon):
    key = _key()
    if not key:
        return None
    try:
        r = requests.get(
            "https://api.geoapify.com/v1/geocode/reverse",
            params={"lat": lat, "lon": lon, "apiKey": key, "lang": "en"},
            timeout=6,
        )
        if r.ok:
            feats = r.json().get("features", [])
            if feats:
                return feats[0]["properties"].get("formatted")
    except Exception:
        pass
    return None
