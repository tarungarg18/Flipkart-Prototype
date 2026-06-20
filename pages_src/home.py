import streamlit as st
from datetime import datetime, date, time as time_type
from utils.mapmyindia import search_places, get_token
from models.predictor import predict_severity_score

EVENT_CAUSES = [
    "Select cause",
    "Accident", "Congestion", "Construction", "Debris",
    "Fog / Low Visibility", "Pot Holes", "Procession", "Protest",
    "Public Event", "Road Conditions", "Tree Fall",
    "Vehicle Breakdown", "VIP Movement", "Water Logging", "Others",
]


def _init_state():
    defaults = {
        "lat_val":        0.0,
        "lng_val":        0.0,
        "addr_results":   [],
        "addr_confirmed": None,
        "severity_result": None,
        "last_searched_q": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _severity_meta(score: float):
    if score >= 7.5:
        return "Critical", "#dc2626", "#fef2f2", "#dc2626"
    if score >= 5.0:
        return "High",     "#ea580c", "#fff7ed", "#ea580c"
    if score >= 3.0:
        return "Medium",   "#d97706", "#fffbeb", "#d97706"
    return     "Low",      "#16a34a", "#f0fdf4", "#16a34a"


def render():
    _init_state()

    st.markdown("""
    <div class="page-header">
      <div class="ph-title">Event Traffic Severity Predictor</div>
      <div class="ph-sub">Event-Driven Congestion Intelligence &middot; Bangalore Traffic Control</div>
    </div>
    """, unsafe_allow_html=True)

    # ── LOCATION ──────────────────────────────────────────────────────────────
    st.markdown('<p class="section-label">Location</p>', unsafe_allow_html=True)

    # Address field — search runs inline on every rerun when query changes
    addr_input = st.text_input(
        "address_field",
        key="addr_query",
        placeholder="Start typing a Bangalore location...",
        label_visibility="collapsed",
    )

    # Inline debounce: search whenever query >= 3 chars and has changed
    q = addr_input.strip()
    if q and len(q) >= 3 and q != st.session_state.last_searched_q:
        results = search_places(q)
        st.session_state.addr_results   = results
        st.session_state.last_searched_q = q
        if results:
            st.session_state.addr_confirmed = None
    elif len(q) < 3:
        st.session_state.addr_results = []

    # Suggestion list
    if st.session_state.addr_results:
        st.caption("Select a location:")
        for i, r in enumerate(st.session_state.addr_results):
            name  = r.get("placeName", "")
            paddr = r.get("placeAddress", "")
            label = f"{name}  —  {paddr}" if paddr else name
            if st.button(label, key=f"sug_{i}", use_container_width=True):
                st.session_state.addr_confirmed = r
                st.session_state.addr_results   = []
                st.rerun()

    # Confirmed address pill
    if st.session_state.addr_confirmed:
        r     = st.session_state.addr_confirmed
        name  = r.get("placeName", "")
        paddr = r.get("placeAddress", "")
        st.markdown(
            f'<div class="confirmed-addr">'
            f'{name}{"  —  " + paddr if paddr else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Lat / Long — optional, enter manually if needed
    ll1, ll2 = st.columns(2)
    lat = ll1.number_input("Latitude (optional)",  key="lat_val", format="%.6f", step=0.0001)
    lng = ll2.number_input("Longitude (optional)", key="lng_val", format="%.6f", step=0.0001)

    st.divider()

    # ── EVENT DETAILS ─────────────────────────────────────────────────────────
    st.markdown('<p class="section-label">Event Details</p>', unsafe_allow_html=True)

    ec1, ec2 = st.columns(2)
    event_type  = ec1.selectbox("Event Type",  ["Planned", "Unplanned"])
    event_cause = ec2.selectbox("Event Cause", EVENT_CAUSES)

    dc1, dc2 = st.columns(2)
    start_date = dc1.date_input("Start Date", value=date.today())
    start_time = dc2.time_input("Start Time", value=time_type(9, 0), step=300)

    st.markdown("""
    <div class="road-closure-banner">
      <div>
        <div class="rcb-title">Road Closure Required</div>
        <div class="rcb-sub">Automatically determined by road closure model</div>
      </div>
      <span class="rcb-badge">AUTO &middot; TRUE</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PREDICT ───────────────────────────────────────────────────────────────
    if st.button("Predict Severity Score", use_container_width=True, type="primary"):
        if event_cause == "Select cause":
            st.error("Please select an event cause.")
        else:
            confirmed   = st.session_state.addr_confirmed
            address_str = (
                (confirmed.get("placeName", "") + " " + confirmed.get("placeAddress", "")).strip()
                if confirmed else q
            )
            lat_in = st.session_state.lat_val
            lng_in = st.session_state.lng_val
            inputs = {
                "latitude":       lat_in  if lat_in  != 0.0 else None,
                "longitude":      lng_in  if lng_in  != 0.0 else None,
                "address":        address_str,
                "event_type":     event_type,
                "event_cause":    event_cause,
                "start_datetime": datetime.combine(start_date, start_time).isoformat(),
                "road_closure":   True,
            }
            with st.spinner("Running severity model..."):
                score = predict_severity_score(inputs)
            st.session_state.severity_result = {"score": score, "inputs": inputs}

    # ── RESULT ────────────────────────────────────────────────────────────────
    res = st.session_state.get("severity_result")
    if res:
        score  = res["score"]
        inputs = res["inputs"]
        level, color, bg, border = _severity_meta(score)
        pct = score / 10 * 100

        dt_str  = inputs.get("start_datetime", "").replace("T", "  at  ")
        lat_v   = inputs.get("latitude")
        lng_v   = inputs.get("longitude")
        coord   = (
            f'<div class="rc-detail">Coordinates: {lat_v:.6f}, {lng_v:.6f}</div>'
            if (lat_v is not None and lng_v is not None) else ""
        )
        loc_row = (
            f'<div class="rc-detail">Location: {inputs["address"]}</div>'
            if inputs.get("address") else ""
        )

        st.markdown(f"""
        <div class="result-card" style="border-color:{border};background:{bg}">
          <div class="rc-header">Severity Prediction Result</div>
          <div class="rc-score" style="color:{color}">{score:.1f}</div>
          <div class="rc-max">out of 10.0</div>
          <div class="rc-bar-bg">
            <div class="rc-bar" style="width:{pct:.1f}%;background:{color}"></div>
          </div>
          <div class="rc-badge" style="border-color:{border};color:{color};background:{bg}">
            {level.upper()} SEVERITY
          </div>
          <div class="rc-details">
            {loc_row}
            <div class="rc-detail">Date &amp; Time: {dt_str}</div>
            <div class="rc-detail">Type: {inputs.get("event_type","")} &nbsp;|&nbsp; Cause: {inputs.get("event_cause","")}</div>
            {coord}
          </div>
        </div>
        """, unsafe_allow_html=True)
