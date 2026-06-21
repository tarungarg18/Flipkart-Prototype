import os
import streamlit as st

GRAPH_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bengaluru_drive.graphml")
BIG = 1e12

# OSM query used when the local file is absent (e.g. on Render)
_OSM_PLACE = "Bengaluru, Karnataka, India"


def graph_available():
    return True  # always available — fetched from OSM if local file missing


@st.cache_resource(show_spinner="Loading Bangalore road network…")
def load_graph():
    import osmnx as ox

    if os.path.exists(GRAPH_PATH):
        G = ox.load_graphml(GRAPH_PATH)
    else:
        # Download from OpenStreetMap (runs once per server lifetime)
        G = ox.graph_from_place(_OSM_PLACE, network_type="drive")
        # Try to cache locally so subsequent restarts are instant
        try:
            ox.save_graphml(G, GRAPH_PATH)
        except Exception:
            pass  # read-only filesystem on some hosts — fine, graph stays in memory

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


def _edge_geoms(edges, blocked_index):
    out = []
    for idx in blocked_index:
        try:
            geom = edges.loc[idx].geometry
        except Exception:
            continue
        if geom is not None and geom.geom_type == "LineString":
            out.append([[lat, lng] for lng, lat in geom.coords])
    return out


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

    blocked_coords = _edge_geoms(edges, blocked_index)

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

    route_coords = [[G.nodes[n]["y"], G.nodes[n]["x"]] for n in route]

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
