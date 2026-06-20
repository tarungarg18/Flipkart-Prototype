import requests
import streamlit as st


@st.cache_data(ttl=82800, show_spinner=False)
def _fetch_token(client_id: str, client_secret: str) -> str | None:
    try:
        r = requests.post(
            "https://outpost.mapmyindia.com/api/security/oauth/token",
            data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
            timeout=8,
        )
        if r.ok:
            return r.json().get("access_token")
    except Exception:
        pass
    return None


def get_token() -> str | None:
    try:
        cid = st.secrets.get("MAPMYINDIA_CLIENT_ID", "")
        sec = st.secrets.get("MAPMYINDIA_CLIENT_SECRET", "")
        if cid and sec:
            return _fetch_token(cid, sec)
    except Exception:
        pass
    return None


def search_places(query: str) -> list[dict]:
    """Text → list of place suggestions (name + address for display)."""
    token = get_token()
    if not token or len(query) < 3:
        return []
    try:
        r = requests.get(
            "https://atlas.mapmyindia.com/api/places/search/json",
            params={"query": query, "access_token": token, "region": "IND"},
            timeout=6,
        )
        if r.ok:
            return r.json().get("suggestedLocations", [])[:6]
    except Exception:
        pass
    return []
