import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, time as time_type
from utils.geoapify import search_places, reverse_geocode, _key as geo_key
from models.predictor import predict
from models import runtime

EVENT_CAUSES = [
    "Select cause",
    "Accident", "Congestion", "Construction", "Debris",
    "Fog / Low Visibility", "Pot Holes", "Procession", "Protest",
    "Public Event", "Road Conditions", "Tree Fall",
    "Vehicle Breakdown", "VIP Movement", "Water Logging", "Others",
]

SEVERITY_BANDS = [
    ("Low",      "0.0 – 3.0",  "#16a34a"),
    ("Medium",   "3.0 – 5.0",  "#d97706"),
    ("High",     "5.0 – 7.5",  "#ea580c"),
    ("Critical", "7.5 – 10.0", "#dc2626"),
]

PAGES = ["Predictor", "Assumptions", "Evaluation", "Analytics"]


def init_state():
    defaults = {
        "page":             "Predictor",
        "lat_val":          0.0,
        "lng_val":          0.0,
        "addr_results":     [],
        "addr_confirmed":   None,
        "last_searched_q":  "",
        "last_rev_geocode": (0.0, 0.0),
        "last_drawing":     None,
        "selection_coords": [],
        "selection_kind":   None,
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


def _tiles():
    key = geo_key()
    if key:
        return f"https://maps.geoapify.com/v1/tile/osm-bright/{{z}}/{{x}}/{{y}}.png?apiKey={key}"
    return "OpenStreetMap"


def _skeleton(height):
    return f'<div class="skeleton" style="height:{height}px"></div>'


def build_map(lat, lng):
    import folium
    from folium.plugins import Draw

    center_lat = lat if lat != 0.0 else 12.9716
    center_lng = lng if lng != 0.0 else 77.5946
    zoom = 14 if lat != 0.0 else 12

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom,
        tiles=_tiles(),
        attr="OpenStreetMap",
        prefer_canvas=True,
        control_scale=False,
    )
    m.get_root().html.add_child(folium.Element(
        "<style>.leaflet-control-attribution{display:none !important;}</style>"
    ))
    Draw(
        draw_options={
            "polyline":    {"shapeOptions": {"color": "#dc2626", "weight": 5}},
            "marker":      True,
            "polygon":     False,
            "rectangle":   False,
            "circle":      False,
            "circlemarker": False,
        },
        edit_options={"edit": False},
    ).add_to(m)

    coords = st.session_state.selection_coords
    if coords:
        if len(coords) == 1:
            folium.CircleMarker(
                location=[coords[0]["lat"], coords[0]["lng"]],
                radius=9, color="#4f46e5", fill=True,
                fill_color="#4f46e5", fill_opacity=0.85, tooltip="Selected point",
            ).add_to(m)
        else:
            folium.PolyLine(
                [[c["lat"], c["lng"]] for c in coords],
                color="#4f46e5", weight=5, opacity=0.85, tooltip="Selected stretch",
            ).add_to(m)
    return m


def _drawing_to_coords(drawing):
    geom = drawing.get("geometry", {})
    gtype = geom.get("type")
    gc = geom.get("coordinates")
    if gtype == "Point":
        return [{"lat": gc[1], "lng": gc[0]}], "point"
    if gtype == "LineString" and len(gc) >= 2:
        return [{"lat": c[1], "lng": c[0]} for c in gc], "path"
    return None, None


def render_detour(coords):
    import folium
    from utils.routing import graph_available, compute_closure

    st.markdown(
        '<p class="section-label">Predicted Road Closure &amp; Reroute &nbsp;&middot;&nbsp;'
        '<span class="section-label-hint">live route impact</span></p>',
        unsafe_allow_html=True,
    )
    if not graph_available():
        st.info("Road network not available. Run setup_map.py once to enable the reroute map.")
        return

    ph = st.empty()
    ph.markdown(_skeleton(380), unsafe_allow_html=True)
    data = compute_closure(coords)

    if not data.get("ok"):
        ph.empty()
        st.warning(data.get("error", "Could not calculate a reroute for this selection."))
        return

    center = coords[len(coords) // 2]
    m = folium.Map(location=[center["lat"], center["lng"]], zoom_start=15,
                   tiles=_tiles(), attr="OpenStreetMap", prefer_canvas=True)
    m.get_root().html.add_child(folium.Element(
        "<style>.leaflet-control-attribution{display:none !important;}</style>"
    ))
    if data["detour_route"]:
        folium.PolyLine(data["detour_route"], color="#16a34a", weight=7, opacity=0.9, tooltip="Reroute").add_to(m)
    for seg in data["blocked_roads"]:
        folium.PolyLine(seg, color="#dc2626", weight=6, opacity=0.95, tooltip="Closed road").add_to(m)
    folium.Marker(location=[center["lat"], center["lng"]], tooltip="Event location",
                  icon=folium.Icon(color="purple")).add_to(m)

    ph.empty()
    components.html(m.get_root().render(), height=390)

    if data["avoided"] and data["length_increase"] is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("Direct route", f"{data['original_length']:.0f} m")
        c2.metric("Reroute", f"{data['detour_length']:.0f} m")
        c3.metric("Added distance", f"+{data['length_increase']:.0f} m")
    else:
        st.caption("Closed road in red, best available reroute in green.")


_LOGO_SVG = """<svg width="42" height="42" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="42" height="42" rx="11" fill="#EEF2FF"/>
  <rect x="7"  y="25" width="5" height="11" rx="1.5" fill="#4338CA"/>
  <rect x="14" y="17" width="5" height="19" rx="1.5" fill="#4338CA"/>
  <rect x="21" y="12" width="5" height="24" rx="1.5" fill="#6366F1"/>
  <rect x="28" y="19" width="5" height="17" rx="1.5" fill="#818CF8"/>
  <path d="M6 33 Q13 26 21 29.5 Q29 33 36 26" stroke="#A5B4FC" stroke-width="2.2" fill="none" stroke-linecap="round"/>
</svg>"""


def render_header_nav():
    page = st.session_state.get("page", "Predictor")
    links = "".join(
        f'<a href="?p={p}" target="_self" class="nav-link {"nav-active" if p == page else ""}">{p}</a>'
        for p in PAGES
    )
    st.markdown(f"""
    <div class="app-header">
      <div class="app-header-inner">
        <div class="header-brand">
          {_LOGO_SVG}
          <div>
            <div class="header-title">Smart Traffic Command Center</div>
            <div class="header-sub">Event-Driven Congestion Intelligence &middot; Bangalore</div>
          </div>
        </div>
        <nav class="header-nav">{links}</nav>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_predictor():
    lat_val = st.session_state.lat_val
    lng_val = st.session_state.lng_val

    if (lat_val != 0.0 and lng_val != 0.0
            and (lat_val, lng_val) != st.session_state.last_rev_geocode):
        addr = reverse_geocode(lat_val, lng_val)
        st.session_state.last_rev_geocode = (lat_val, lng_val)
        if st.session_state.selection_kind != "path":
            st.session_state.selection_coords = [{"lat": lat_val, "lng": lng_val}]
            st.session_state.selection_kind = "point"
        if addr:
            st.session_state.addr_confirmed = {"label": addr, "lat": lat_val, "lon": lng_val}
            st.session_state.addr_results = []

    st.markdown(
        '<p class="section-label">Bangalore Map &nbsp;&middot;&nbsp;'
        '<span class="section-label-hint">drop a marker for a point, or draw a line for a road stretch</span></p>',
        unsafe_allow_html=True,
    )

    from streamlit_folium import st_folium
    mph = st.empty()
    mph.markdown(_skeleton(380), unsafe_allow_html=True)
    m = build_map(lat_val, lng_val)
    map_data = st_folium(
        m, height=380, use_container_width=True, key="input_map",
        returned_objects=["last_active_drawing"],
    )
    mph.empty()

    drawing = map_data.get("last_active_drawing") if map_data else None
    if drawing and drawing != st.session_state.last_drawing:
        st.session_state.last_drawing = drawing
        coords, kind = _drawing_to_coords(drawing)
        if coords:
            st.session_state.selection_coords = coords
            st.session_state.selection_kind = kind
            rep = coords[len(coords) // 2]
            st.session_state.lat_val = round(rep["lat"], 6)
            st.session_state.lng_val = round(rep["lng"], 6)
            st.rerun()

    if st.session_state.selection_kind == "path":
        st.caption(f"Selected road stretch with {len(st.session_state.selection_coords)} points.")
    elif st.session_state.selection_kind == "point":
        st.caption("Selected a single point.")

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
                st.session_state.selection_coords = [{"lat": r["lat"], "lng": r["lon"]}]
                st.session_state.selection_kind = "point"
                st.rerun()

    if st.session_state.addr_confirmed:
        c = st.session_state.addr_confirmed
        st.markdown(f'<div class="confirmed-addr">{c["label"]}</div>', unsafe_allow_html=True)

    ll1, ll2 = st.columns(2)
    ll1.number_input("Latitude", key="lat_val", format="%.6f", step=0.0001)
    ll2.number_input("Longitude", key="lng_val", format="%.6f", step=0.0001)

    st.divider()
    st.markdown('<p class="section-label">Event Details</p>', unsafe_allow_html=True)

    with st.form("predict_form", border=False):
        ec1, ec2 = st.columns(2)
        event_type  = ec1.selectbox("Event Type", ["Planned", "Unplanned"])
        event_cause = ec2.selectbox("Event Cause", EVENT_CAUSES)

        start_date = st.date_input("Start Date", value=date.today())
        tc1, tc2 = st.columns(2)
        start_hour = tc1.number_input("Hour (0-23)", min_value=0, max_value=23, value=9, step=1)
        start_min  = tc2.number_input("Minute (0-59)", min_value=0, max_value=59, value=0, step=1)

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Predict Severity", use_container_width=True, type="primary")

    if submitted:
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
            selection = st.session_state.selection_coords or [{"lat": lat_in, "lng": lng_in}]
            inputs = {
                "latitude":       lat_in,
                "longitude":      lng_in,
                "address":        address_str,
                "event_type":     event_type,
                "event_cause":    event_cause,
                "start_datetime": datetime.combine(start_date, start_time).isoformat(),
                "selection":      selection,
            }
            with st.spinner("Running prediction models..."):
                result = predict(inputs)
            if result.get("ok"):
                st.session_state.severity_result = {"result": result, "inputs": inputs, "selection": selection}
                from utils import history as hist
                hist.add(inputs, result)
            else:
                st.session_state.severity_result = None
                st.error(result.get("error", "Unable to predict right now."))

    res = st.session_state.get("severity_result")
    if res:
        rr = res["result"]
        score       = rr["severity"]
        closure     = rr["road_closure"]
        closure_prob = rr.get("closure_prob")
        barricades  = rr.get("barricades")
        manpower    = rr.get("manpower_deployment")
        diversion   = rr.get("diversion_plan")
        inputs      = res["inputs"]

        level, color, bg, border = severity_meta(score)
        pct = score / 10 * 100

        dt_str = inputs.get("start_datetime", "").replace("T", "  at  ")
        lat_v  = inputs.get("latitude")
        lng_v  = inputs.get("longitude")

        closure_color = "#dc2626" if closure else "#16a34a"
        closure_text  = "ROAD CLOSURE REQUIRED" if closure else "NO ROAD CLOSURE"
        if closure_prob is not None:
            closure_text += f" · {closure_prob * 100:.0f}%"
        closure_bg = "#fef2f2" if closure else "#f0fdf4"

        _S = ("display:flex;justify-content:space-between;gap:18px;"
              "font-size:0.97rem;align-items:baseline;margin-bottom:11px")
        _LBL = "color:#94a3b8;font-weight:600;white-space:nowrap"
        _VAL = "color:#1e293b;font-weight:700;text-align:right"

        def _row(lbl, val):
            return f'<div style="{_S}"><span style="{_LBL}">{lbl}</span><b style="{_VAL}">{val}</b></div>'

        rows = ""
        if inputs.get("address"):
            rows += _row("Location", inputs["address"])
        rows += _row("Date & Time", dt_str)
        rows += _row("Type / Cause", f'{inputs.get("event_type", "")} · {inputs.get("event_cause", "")}')
        if lat_v is not None and lng_v is not None:
            rows += _row("Coordinates", f"{lat_v:.6f}, {lng_v:.6f}")
        rows += _row("Barricades", f"{barricades} units")
        rows += _row("Manpower", manpower)
        rows += _row("Diversion", diversion)

        st.markdown(f"""
        <div style="border:1.5px solid {border};border-radius:14px;padding:28px 24px 22px;
                    margin-top:20px;background:{bg}">
          <div style="font-size:0.67rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.8px;color:#94a3b8;margin-bottom:14px;text-align:center">
            Prediction Result
          </div>
          <div style="font-size:3.8rem;font-weight:900;line-height:1;letter-spacing:-2px;
                      color:{color};text-align:center">{score:.1f}</div>
          <div style="font-size:0.9rem;color:#94a3b8;margin-top:2px;margin-bottom:14px;
                      text-align:center">out of 10.0</div>
          <div style="height:7px;background:#e2e8f0;border-radius:99px;overflow:hidden;
                      margin:0 auto 16px;max-width:260px">
            <div style="height:100%;width:{pct:.1f}%;background:{color};border-radius:99px"></div>
          </div>
          <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-bottom:18px">
            <span style="font-size:0.73rem;font-weight:700;letter-spacing:0.5px;border:1.5px solid {border};
                         color:{color};border-radius:99px;padding:4px 16px">{level.upper()} SEVERITY</span>
            <span style="font-size:0.73rem;font-weight:700;letter-spacing:0.5px;border:1.5px solid {closure_color};
                         color:{closure_color};background:{closure_bg};border-radius:99px;padding:4px 16px">
              {closure_text}
            </span>
          </div>
          <div style="border-top:1px solid #e2e8f0;padding-top:16px">{rows}</div>
        </div>
        """, unsafe_allow_html=True)

        selection = res.get("selection") or [{"lat": lat_v, "lng": lng_v}]
        if selection and selection[0].get("lat") is not None:
            st.markdown("<br>", unsafe_allow_html=True)
            render_detour(selection)


def render_assumptions():
    meta = runtime.info()

    st.markdown('<p class="section-label">Severity Bands</p>', unsafe_allow_html=True)
    bands_html = '<div class="assume-card"><div class="assume-list">'
    for name, rng, c in SEVERITY_BANDS:
        bands_html += (
            f'<div class="assume-row">'
            f'<span class="dot" style="background:{c}"></span>'
            f'<b>{name}</b><span class="rng">{rng}</span>'
            f'</div>'
        )
    bands_html += '</div></div>'
    st.markdown(bands_html, unsafe_allow_html=True)

    thr = meta["closure_threshold"]
    st.markdown(f"""
    <div class="assume-card">
      <div class="assume-title">Road Closure Decision</div>
      <div class="assume-list">
        <div class="assume-row"><span class="dot" style="background:#4f46e5"></span><b>Closure threshold</b><span class="rng">probability &ge; {thr:.2f}</span></div>
        <div class="assume-row"><span class="dot" style="background:#dc2626"></span><b>Drawn line (path)</b><span class="rng">high chance — incident span is key signal</span></div>
        <div class="assume-row"><span class="dot" style="background:#94a3b8"></span><b>Single point marker</b><span class="rng">lower chance — no span, no length signal</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tiers = sorted(meta["cause_tier"].items(), key=lambda kv: kv[1], reverse=True)
    seen = set()
    rows = ""
    for cause, tier in tiers:
        label = cause.replace("_", " ").title()
        if label in seen:
            continue
        seen.add(label)
        dot_color = "#dc2626" if tier >= 0.8 else "#d97706" if tier >= 0.5 else "#16a34a"
        rows += (
            f'<div class="assume-row">'
            f'<span class="dot" style="background:{dot_color}"></span>'
            f'<b>{label}</b><span class="rng">{tier:.2f}</span>'
            f'</div>'
        )
    st.markdown(f"""
    <div class="assume-card">
      <div class="assume-title">Cause Severity Weights</div>
      <div class="assume-list">{rows}</div>
    </div>
    """, unsafe_allow_html=True)

    corridors = meta["corridors"]
    corr_items = ""
    for c in corridors[:16]:
        corr_items += (
            f'<div class="assume-row">'
            f'<span class="dot" style="background:#4f46e5"></span>'
            f'<b>{c.replace("_", " ").title()}</b>'
            f'</div>'
        )
    if len(corridors) > 16:
        corr_items += f'<div class="assume-row" style="color:#94a3b8;font-size:0.85rem">+ {len(corridors)-16} more corridors</div>'
    st.markdown(f"""
    <div class="assume-card">
      <div class="assume-title">Known Corridors ({len(corridors)})</div>
      <div class="assume-body" style="margin-bottom:10px;font-size:0.88rem">
        Corridor is auto-detected by matching the address text. A match raises impact through the corridor priority rate.
      </div>
      <div class="assume-list">{corr_items}</div>
    </div>
    """, unsafe_allow_html=True)

    bp = meta["barricade_params"]
    st.markdown(f"""
    <div class="assume-card">
      <div class="assume-title">Barricades</div>
      <div class="assume-list">
        <div class="assume-row"><b>Base count</b><span class="rng">{bp['BARRICADE_BASE']:.0f} units</span></div>
        <div class="assume-row"><b>Floor / Ceiling</b><span class="rng">{bp['BARRICADE_FLOOR']} – {bp['BARRICADE_CEILING']} units</span></div>
        <div class="assume-row"><b>Scales with</b><span class="rng">severity, closure confidence, span, corridor</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="assume-card">
      <div class="assume-title">Inputs Defaulted (not collected from form)</div>
      <div class="assume-list">
        <div class="assume-row"><b>Zone</b><span class="rng">unknown &rarr; city average rate</span></div>
        <div class="assume-row"><b>Vehicle type</b><span class="rng">unknown &rarr; treated as non-heavy</span></div>
        <div class="assume-row"><b>Junction frequency</b><span class="rng">baseline (1 junction)</span></div>
        <div class="assume-row"><b>Month</b><span class="rng">off-monsoon</span></div>
        <div class="assume-row"><b>Road class</b><span class="rng">non-highway</span></div>
        <div class="assume-row"><b>Event status</b><span class="rng">unresolved</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="assume-card">
      <div class="assume-title">Reroute Map</div>
      <div class="assume-list">
        <div class="assume-row"><b>Single point</b><span class="rng">closes nearest road segment</span></div>
        <div class="assume-row"><b>Drawn line</b><span class="rng">closes all segments it crosses (0.03&deg; buffer)</span></div>
        <div class="assume-row"><b>Green line</b><span class="rng">shortest detour path</span></div>
        <div class="assume-row"><b>Red line</b><span class="rng">closed road segments</span></div>
        <div class="assume-row"><b>Route engine</b><span class="rng">osmnx + networkx shortest-path (penalty-restore)</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_evaluation():
    from utils import history as hist

    st.markdown(
        '<p class="section-label">Prediction History &nbsp;&middot;&nbsp;'
        '<span class="section-label-hint">enter post-event actuals to track accuracy</span></p>',
        unsafe_allow_html=True,
    )

    search = st.text_input(
        "search_eval", placeholder="Search by location, cause, event type, date...",
        label_visibility="collapsed", key="eval_search",
    )

    data = list(reversed(hist.load()))

    if search:
        s = search.lower()
        data = [
            e for e in data
            if s in (e["inputs"].get("address") or "").lower()
            or s in (e["inputs"].get("event_cause") or "").lower()
            or s in (e["inputs"].get("event_type") or "").lower()
            or s in e.get("timestamp", "").lower()
        ]

    if not data:
        st.info("No predictions yet. Go to Predictor to run your first prediction.")
        return

    st.caption(f"{len(data)} event(s) found")

    for entry in data:
        inp     = entry["inputs"]
        res     = entry["result"]
        actuals = entry.get("actuals") or {}
        ts      = entry.get("timestamp", "")[:16].replace("T", " ")
        loc     = inp.get("address") or f'{inp.get("latitude","")}, {inp.get("longitude","")}'
        cause   = inp.get("event_cause", "")
        sev     = res.get("severity", "-")
        closure = res.get("road_closure", False)

        has_actuals = bool(entry.get("actuals"))
        tag = " [actuals logged]" if has_actuals else ""
        label = f"{ts}  |  {str(loc)[:45]}  |  {cause}  |  Severity {sev}{tag}"

        with st.expander(label):
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("**Predicted values**")
                st.markdown(f"Severity: **{sev}**")
                st.markdown(f"Road closure: **{'Yes' if closure else 'No'}**")
                st.markdown(f"Barricades: **{res.get('barricades', '-')} units**")
                st.markdown(f"Manpower: **{res.get('manpower_count', '-')}**")
            with d2:
                st.markdown("**Event inputs**")
                st.markdown(f"Location: **{str(loc)[:60]}**")
                st.markdown(f"Type: **{inp.get('event_type', '')} — {cause}**")
                dt = inp.get("start_datetime", "").replace("T", " ")[:16]
                st.markdown(f"Date/Time: **{dt}**")

            st.divider()
            st.markdown("**Post-Event Actuals**")

            pc1, pc2 = st.columns(2)
            _sev_v = actuals.get("severity")
            _bar_v = actuals.get("barricades")
            _man_v = actuals.get("manpower")
            act_sev = pc1.number_input(
                "Actual Severity (0–10)", 0.0, 10.0,
                value=float(_sev_v) if _sev_v is not None else 0.0, step=0.1,
                key=f"asev_{entry['id']}",
            )
            act_bar = pc2.number_input(
                "Barricades Deployed", 0, 500,
                value=int(_bar_v) if _bar_v is not None else 0,
                key=f"abar_{entry['id']}",
            )
            act_man = pc1.number_input(
                "Manpower Deployed", 0, 500,
                value=int(_man_v) if _man_v is not None else 0,
                key=f"aman_{entry['id']}",
            )
            act_notes = pc2.text_area(
                "Notes", value=actuals.get("notes") or "",
                key=f"anotes_{entry['id']}", height=80,
            )

            sc1, sc2 = st.columns([2, 1])
            if sc1.button("Save Actuals", key=f"save_{entry['id']}", type="primary", use_container_width=True):
                hist.update_actuals(entry["id"], {
                    "severity":   act_sev,
                    "barricades": act_bar,
                    "manpower":   act_man,
                    "notes":      act_notes,
                    "saved_at":   datetime.now().isoformat(),
                })
                st.success("Actuals saved.")
                st.rerun()
            if sc2.button("Delete", key=f"del_{entry['id']}", use_container_width=True):
                hist.delete_entry(entry["id"])
                st.rerun()


def render_analytics():
    import pandas as pd
    from utils import history as hist

    st.markdown('<p class="section-label">Analytics &nbsp;&middot;&nbsp;<span class="section-label-hint">charts from prediction history</span></p>', unsafe_allow_html=True)

    data = hist.load()
    if not data:
        st.info("No predictions yet. Go to Predictor to make your first prediction.")
        return

    rows = []
    for e in data:
        inp = e["inputs"]
        res = e["result"]
        act = e.get("actuals") or {}
        try:
            hour = datetime.fromisoformat(str(inp.get("start_datetime", ""))).hour
        except Exception:
            hour = 0
        rows.append({
            "timestamp":      e.get("timestamp", ""),
            "location":       inp.get("address", ""),
            "event_type":     inp.get("event_type", ""),
            "cause":          inp.get("event_cause", ""),
            "hour":           hour,
            "pred_severity":  float(res.get("severity", 0)),
            "pred_closure":   int(bool(res.get("road_closure", False))),
            "pred_barricades": int(res.get("barricades", 0)),
            "act_severity":   float(act["severity"]) if act.get("severity") is not None else None,
            "act_barricades": int(act["barricades"]) if act.get("barricades") is not None else None,
            "act_manpower":   int(act["manpower"]) if act.get("manpower") is not None else None,
        })

    df = pd.DataFrame(rows)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Predictions", len(df))
    m2.metric("Avg Severity", f"{df['pred_severity'].mean():.1f}")
    m3.metric("Closure Rate", f"{df['pred_closure'].mean() * 100:.0f}%")
    m4.metric("With Actuals", int(df["act_severity"].notna().sum()))

    st.divider()

    try:
        import plotly.express as px

        pc = {"color_discrete_sequence": ["#4f46e5"]}
        layout_base = dict(margin=dict(l=0, r=0, t=24, b=0), plot_bgcolor="white", paper_bgcolor="white")

        st.markdown('<p class="section-label">Severity Score Distribution</p>', unsafe_allow_html=True)
        fig = px.histogram(df, x="pred_severity", nbins=20, **pc)
        fig.update_layout(**layout_base, height=220, xaxis_title="Predicted Severity", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

        if len(df) > 1:
            st.markdown('<p class="section-label">Events by Cause</p>', unsafe_allow_html=True)
            cc = df["cause"].value_counts().reset_index()
            cc.columns = ["cause", "count"]
            fig2 = px.bar(cc, x="count", y="cause", orientation="h", **pc)
            fig2.update_layout(**layout_base, height=max(180, len(cc) * 28), yaxis_title="", xaxis_title="Count")
            st.plotly_chart(fig2, use_container_width=True)

        if len(df) >= 3:
            st.markdown('<p class="section-label">Average Severity by Hour of Day</p>', unsafe_allow_html=True)
            hourly = df.groupby("hour")["pred_severity"].mean().reset_index()
            fig3 = px.line(hourly, x="hour", y="pred_severity", markers=True, **pc)
            fig3.update_layout(**layout_base, height=220, xaxis_title="Hour", yaxis_title="Avg Severity")
            st.plotly_chart(fig3, use_container_width=True)

        act_df = df.dropna(subset=["act_severity"])
        if len(act_df) >= 2:
            st.markdown('<p class="section-label">Predicted vs Actual Severity</p>', unsafe_allow_html=True)
            fig4 = px.scatter(act_df, x="pred_severity", y="act_severity", **pc)
            fig4.update_layout(**layout_base, height=260, xaxis_title="Predicted", yaxis_title="Actual")
            fig4.add_shape(type="line", x0=0, y0=0, x1=10, y1=10,
                           line=dict(color="#e2e8f0", dash="dash"))
            st.plotly_chart(fig4, use_container_width=True)

    except ImportError:
        st.info("Install plotly to view charts: `pip install plotly`")

    st.divider()
    st.markdown('<p class="section-label">Export</p>', unsafe_allow_html=True)
    csv_out = df.to_csv(index=False)
    st.download_button(
        "Download prediction history as CSV",
        csv_out,
        file_name="prediction_history.csv",
        mime="text/csv",
    )


def render():
    init_state()
    # Sync page from URL query param (soft navigation, session state preserved)
    p = st.query_params.get("p", "Predictor")
    if p in PAGES:
        st.session_state.page = p
    render_header_nav()
    page = st.session_state.page
    if page == "Predictor":
        render_predictor()
    elif page == "Assumptions":
        render_assumptions()
    elif page == "Evaluation":
        render_evaluation()
    elif page == "Analytics":
        render_analytics()
