import os
import streamlit as st

_GRAPH_PRIMARY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bengaluru_drive.graphml")
_GRAPH_TMP     = "/tmp/bengaluru_drive.graphml"
BIG = 1e12
_OSM_PLACE = "Bengaluru, Karnataka, India"


def _is_real_graphml(path):
    """Return False if the file is a Git LFS pointer instead of actual GraphML."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
        return head.startswith(b"<?xml") or head.startswith(b"<graphml")
    except Exception:
        return False


def _writable_cache_path():
    parent = os.path.dirname(_GRAPH_PRIMARY)
    return _GRAPH_PRIMARY if os.access(parent, os.W_OK) else _GRAPH_TMP


def graph_available():
    return True


@st.cache_resource(show_spinner="Loading Bangalore road network… (first load ~60 s)")
def load_graph():
    import osmnx as ox

    # Point osmnx HTTP cache at /tmp so it never writes to the read-only project root
    try:
        ox.settings.cache_folder = "/tmp/osmnx_cache"
    except Exception:
        pass

    # Try the committed graphml first — but skip it if it's a Git LFS pointer file
    if os.path.exists(_GRAPH_PRIMARY) and _is_real_graphml(_GRAPH_PRIMARY):
        G = ox.load_graphml(_GRAPH_PRIMARY)
    elif os.path.exists(_GRAPH_TMP):
        G = ox.load_graphml(_GRAPH_TMP)
    else:
        # Download from OpenStreetMap (once per server lifetime, cached by @st.cache_resource)
        G = ox.graph_from_place(_OSM_PLACE, network_type="drive")
        try:
            ox.save_graphml(G, _writable_cache_path())
        except Exception:
            pass

    nodes, edges = ox.graph_to_gdfs(G)
    _ = edges.sindex
    _ = nodes.sindex
    return G, nodes, edges


def _nearest_edge(edges, lng, lat):
    from shapely.geometry import Point
    pos = edges.sindex.nearest(Point(lng, lat), return_all=False)[1][0]
    u, v, k = edges.index[pos]
    return int(u), int(v), int(k)


def _nearest_node(nodes, lng, lat):
    from shapely.geometry import Point
    pos = nodes.sindex.nearest(Point(lng, lat), return_all=False)[1][0]
    return int(nodes.index[pos])


def _edge_geoms(edges, blocked_index, G):
    """Coordinates of each blocked edge, following its true road geometry.
    Falls back to the straight node-to-node segment when an edge has no
    stored geometry (otherwise straight edges would be silently dropped)."""
    out = []
    for idx in blocked_index:
        try:
            geom = edges.loc[idx].geometry
        except Exception:
            geom = None
        if geom is not None and geom.geom_type == "LineString":
            out.append([[lat, lng] for lng, lat in geom.coords])
        else:
            try:
                u, v = int(idx[0]), int(idx[1])
                out.append([[G.nodes[u]["y"], G.nodes[u]["x"]],
                            [G.nodes[v]["y"], G.nodes[v]["x"]]])
            except Exception:
                continue
    return out


def _route_to_coords(G, route):
    """Build the polyline for a node path by following each edge's real
    geometry, instead of drawing straight lines between node centers.
    Without this, curved roads render as chords that appear to cut across
    areas with no road."""
    if not route or len(route) < 2:
        return [[G.nodes[n]["y"], G.nodes[n]["x"]] for n in route]
    coords = []
    for u, v in zip(route[:-1], route[1:]):
        data = G.get_edge_data(u, v)
        if not data:
            coords.append([G.nodes[u]["y"], G.nodes[u]["x"]])
            continue
        best = min(data.values(), key=lambda d: d.get("length", 1e18))
        geom = best.get("geometry")
        if geom is not None and geom.geom_type == "LineString":
            pts = [[lat, lng] for lng, lat in geom.coords]
            # geometry may be stored v->u; flip so it runs u->v
            uy, ux = G.nodes[u]["y"], G.nodes[u]["x"]
            if (abs(pts[0][0] - uy) + abs(pts[0][1] - ux)) > \
               (abs(pts[-1][0] - uy) + abs(pts[-1][1] - ux)):
                pts.reverse()
        else:
            pts = [[G.nodes[u]["y"], G.nodes[u]["x"]],
                   [G.nodes[v]["y"], G.nodes[v]["x"]]]
        coords.extend(pts[1:] if coords and coords[-1] == pts[0] else pts)
    return coords


@st.cache_data(show_spinner=False)
def compute_closure(coords):
    import networkx as nx
    from shapely.geometry import LineString, mapping

    G, nodes, edges = load_graph()

    if len(coords) == 1:
        pt = coords[0]
        u, v, k = _nearest_edge(edges, pt["lng"], pt["lat"])
        blocked_index = [(u, v, k)]
        start_node, end_node = u, v
        buffer_geojson = None
    else:
        line = LineString([(p["lng"], p["lat"]) for p in coords])
        corridor = line.buffer(0.0003)
        positions = edges.sindex.query(corridor, predicate="intersects")
        blocked_index = [edges.index[i] for i in positions]
        start_node = _nearest_node(nodes, coords[0]["lng"], coords[0]["lat"])
        end_node = _nearest_node(nodes, coords[-1]["lng"], coords[-1]["lat"])
        buffer_geojson = mapping(corridor)

    blocked_coords = _edge_geoms(edges, blocked_index, G)

    try:
        original_length = nx.shortest_path_length(G, start_node, end_node, weight="length")
    except nx.NetworkXNoPath:
        original_length = None

    saved = {}

    def penalize(a, b):
        if G.has_edge(a, b):
            for kk in list(G[a][b].keys()):
                cur = G[a][b][kk].get("length", 0) or 0
                saved[(a, b, kk)] = G[a][b][kk].get("length")
                G[a][b][kk]["length"] = cur + BIG

    for idx in blocked_index:
        a, b = int(idx[0]), int(idx[1])
        penalize(a, b)
        penalize(b, a)

    try:
        route = nx.shortest_path(G, start_node, end_node, weight="length")
        detour_length = nx.shortest_path_length(G, start_node, end_node, weight="length")
    except nx.NetworkXNoPath:
        route, detour_length = [], None
    finally:
        for (a, b, kk), val in saved.items():
            if val is None:
                G[a][b][kk].pop("length", None)
            else:
                G[a][b][kk]["length"] = val

    route_coords = _route_to_coords(G, route)

    avoided = detour_length is not None and detour_length < BIG
    real_detour_len = detour_length if avoided else None
    increase = None
    if avoided and original_length is not None:
        increase = max(0.0, real_detour_len - original_length)

    return {
        "ok": True,
        "buffer": buffer_geojson,
        "blocked_roads": blocked_coords,
        "detour_route": route_coords,
        "avoided": avoided,
        "original_length": round(original_length, 2) if original_length is not None else None,
        "detour_length": round(real_detour_len, 2) if real_detour_len is not None else None,
        "length_increase": round(increase, 2) if increase is not None else None,
    }
