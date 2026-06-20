import streamlit as st
from datetime import datetime, date, time as time_type
from utils.geoapify import search_places, reverse_geocode, _key as geo_key
from models.predictor import predict

EVENT_CAUSES = [
    "Select cause",
    "Accident", "Congestion", "Construction", "Debris",
    "Fog / Low Visibility", "Pot Holes", "Procession", "Protest",
    "Public Event", "Road Conditions", "Tree Fall",
    "Vehicle Breakdown", "VIP Movement", "Water Logging", "Others",
]


def init_state():
    defaults = {
        "lat_val":          0.0,
        "lng_val":          0.0,
        "addr_results":     [],
        "addr_confirmed":   None,
        "last_searched_q":  "",
        "last_rev_geocode": (0.0, 0.0),
        "last_map_click":   None,
        "severity_result":  None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def in_bangalore(lat, lng):
    return 12.6 <= lat <= 13.25 and 77.3 <= lng <= 77.9


def severity_meta(score):
    if score >= 7.5:
        return "Critical", "#dc2626", "#fef2f2", "#dc2626"
    if score >= 5.0:
        return "High", "#ea580c", "#fff7ed", "#ea580c"
    if score >= 3.0:
        return "Medium", "#d97706", "#fffbeb", "#d97706"
    return "Low", "#16a34a", "#f0fdf4", "#16a34a"


def build_map(lat, lng):
    import folium
    center_lat = lat if lat != 0.0 else 12.9716
    center_lng = lng if lng != 0.0 else 77.5946
    zoom = 14 if lat != 0.0 else 12

    key = geo_key()
    if key:
        tiles = f"https://maps.geoapify.com/v1/tile/osm-bright/{{z}}/{{x}}/{{y}}.png?apiKey={key}"
        attr = "OpenStreetMap"
    else:
        tiles = "OpenStreetMap"
        attr = "OpenStreetMap"

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom,
        tiles=tiles,
        attr=attr,
        prefer_canvas=True,
        control_scale=False,
    )
    m.get_root().html.add_child(folium.Element(
        "<style>.leaflet-control-attribution{display:none !important;}</style>"
    ))

    if lat != 0.0 and lng != 0.0:
        label = (st.session_state.addr_confirmed or {}).get("label", f"{lat:.5f}, {lng:.5f}")
        folium.CircleMarker(
            location=[lat, lng],
            radius=10,
            color="#4f46e5",
            fill=True,
            fill_color="#4f46e5",
            fill_opacity=0.8,
            tooltip=label,
        ).add_to(m)

    return m


def render():
    init_state()

    lat_val = st.session_state.lat_val
    lng_val = st.session_state.lng_val

    if (lat_val != 0.0 and lng_val != 0.0
            and (lat_val, lng_val) != st.session_state.last_rev_geocode):
        addr = reverse_geocode(lat_val, lng_val)
        st.session_state.last_rev_geocode = (lat_val, lng_val)
        if addr:
            st.session_state.addr_confirmed = {"label": addr, "lat": lat_val, "lon": lng_val}
            st.session_state.addr_results = []

    st.markdown("""
    <div class="page-header">
      <div class="ph-title">Event Traffic Severity Predictor</div>
      <div class="ph-sub">Event-Driven Congestion Intelligence &middot; Bangalore Traffic Control</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<p class="section-label">Bangalore Map &nbsp;&middot;&nbsp;'
        '<span class="section-label-hint">click to set location</span></p>',
        unsafe_allow_html=True,
    )

    from streamlit_folium import st_folium
    m = build_map(lat_val, lng_val)
    map_data = st_folium(m, height=380, use_container_width=True)

    clicked = map_data.get("last_clicked") if map_data else None
    if clicked and clicked != st.session_state.last_map_click:
        st.session_state.last_map_click = clicked
        st.session_state.lat_val = round(clicked["lat"], 6)
        st.session_state.lng_val = round(clicked["lng"], 6)
        st.rerun()

    st.divider()

    st.markdown('<p class="section-label">Location</p>', unsafe_allow_html=True)

    addr_input = st.text_input(
        "Search address",
        key="addr_query",
        placeholder="Start typing a Bangalore location...",
        label_visibility="collapsed",
    )

    q = (addr_input or "").strip()
    if q and len(q) >= 3 and q != st.session_state.last_searched_q:
        results = search_places(q)
        st.session_state.addr_results = results
        st.session_state.last_searched_q = q
        if results:
            st.session_state.addr_confirmed = None
    elif len(q) < 3:
        st.session_state.addr_results = []

    if st.session_state.addr_results:
        st.caption("Select a location:")
        for i, r in enumerate(st.session_state.addr_results):
            if st.button(r["label"], key=f"sug_{i}", use_container_width=True):
                st.session_state.addr_confirmed = r
                st.session_state.addr_results = []
                st.session_state.lat_val = r["lat"]
                st.session_state.lng_val = r["lon"]
                st.session_state.last_rev_geocode = (r["lat"], r["lon"])
                st.rerun()

    if st.session_state.addr_confirmed:
        c = st.session_state.addr_confirmed
        st.markdown(
            f'<div class="confirmed-addr">{c["label"]}</div>',
            unsafe_allow_html=True,
        )

    ll1, ll2 = st.columns(2)
    ll1.number_input(
        "Latitude",
        key="lat_val",
        format="%.6f",
        step=0.0001,
        help="Auto-filled from address search or map click. Enter manually to look up the address.",
    )
    ll2.number_input(
        "Longitude",
        key="lng_val",
        format="%.6f",
        step=0.0001,
        help="Auto-filled from address search or map click. Enter manually to look up the address.",
    )

    st.divider()

    st.markdown('<p class="section-label">Event Details</p>', unsafe_allow_html=True)

    ec1, ec2 = st.columns(2)
    event_type = ec1.selectbox("Event Type", ["Planned", "Unplanned"])
    event_cause = ec2.selectbox("Event Cause", EVENT_CAUSES)

    start_date = st.date_input("Start Date", value=date.today())

    tc1, tc2 = st.columns(2)
    start_hour = tc1.number_input("Hour (0-23)", min_value=0, max_value=23, value=9, step=1)
    start_min = tc2.number_input("Minute (0-59)", min_value=0, max_value=59, value=0, step=1)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Predict Severity", use_container_width=True, type="primary"):
        lat_in = st.session_state.lat_val
        lng_in = st.session_state.lng_val

        if event_cause == "Select cause":
            st.error("Please select an event cause.")
        elif lat_in == 0.0 or lng_in == 0.0:
            st.error("Please set a location using the map, address search, or coordinates.")
        elif not in_bangalore(lat_in, lng_in):
            st.error("Please enter a location within Bangalore.")
        else:
            confirmed = st.session_state.addr_confirmed
            address_str = confirmed["label"] if confirmed else q
            start_time = time_type(int(start_hour), int(start_min))
            inputs = {
                "latitude":       lat_in,
                "longitude":      lng_in,
                "address":        address_str,
                "event_type":     event_type,
                "event_cause":    event_cause,
                "start_datetime": datetime.combine(start_date, start_time).isoformat(),
            }
            with st.spinner("Running prediction models..."):
                result = predict(inputs)
            if result.get("ok"):
                st.session_state.severity_result = {"result": result, "inputs": inputs}
            else:
                st.session_state.severity_result = None
                st.error(result.get("error", "Unable to predict right now."))

    res = st.session_state.get("severity_result")
    if res:
        score = res["result"]["severity"]
        closure = res["result"]["road_closure"]
        inputs = res["inputs"]

        level, color, bg, border = severity_meta(score)
        pct = score / 10 * 100

        dt_str = inputs.get("start_datetime", "").replace("T", "  at  ")
        lat_v = inputs.get("latitude")
        lng_v = inputs.get("longitude")
        coord = (
            f'<div class="rc-detail">Coordinates: {lat_v:.6f}, {lng_v:.6f}</div>'
            if lat_v is not None and lng_v is not None else ""
        )
        loc_row = (
            f'<div class="rc-detail">Location: {inputs["address"]}</div>'
            if inputs.get("address") else ""
        )
        closure_color = "#dc2626" if closure else "#16a34a"
        closure_label = "ROAD CLOSURE REQUIRED" if closure else "NO ROAD CLOSURE"
        closure_bg = "#fef2f2" if closure else "#f0fdf4"

        st.markdown(f"""
        <div class="result-card" style="border-color:{border};background:{bg}">
          <div class="rc-header">Prediction Result</div>
          <div class="rc-score" style="color:{color}">{score:.1f}</div>
          <div class="rc-max">out of 10.0</div>
          <div class="rc-bar-bg">
            <div class="rc-bar" style="width:{pct:.1f}%;background:{color}"></div>
          </div>
          <div class="rc-badges">
            <span class="rc-badge" style="border-color:{border};color:{color}">{level.upper()} SEVERITY</span>
            <span class="rc-closure-badge" style="color:{closure_color};border-color:{closure_color};background:{closure_bg}">{closure_label}</span>
          </div>
          <div class="rc-details">
            {loc_row}
            <div class="rc-detail">Date &amp; Time: {dt_str}</div>
            <div class="rc-detail">Type: {inputs.get("event_type","")} &nbsp;|&nbsp; Cause: {inputs.get("event_cause","")}</div>
            {coord}
          </div>
        </div>
        """, unsafe_allow_html=True)
