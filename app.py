
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import osmnx as ox
import geopandas as gpd
import networkx as nx

from shapely.geometry import LineString, mapping
from fastapi.responses import JSONResponse

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# ==========================================
# PRE-LOAD THE LOCAL GRAPH INTO MEMORY
# ==========================================
print("Loading local map file into memory. This takes a few seconds...")
GLOBAL_GRAPH = ox.load_graphml("bengaluru_drive.graphml")

# We also pre-compute the GeoDataFrames so we don't have to do it on every click
GLOBAL_NODES, GLOBAL_EDGES = ox.graph_to_gdfs(GLOBAL_GRAPH)
print("Map loaded and ready! Server is live.")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request}
    )


@app.post("/block-road")
async def block_road(request: Request):

    data = await request.json()
    coords = data["coordinates"]

    # Instantly copy the pre-loaded graph and edges instead of downloading
    G = GLOBAL_GRAPH
    edges = GLOBAL_EDGES
    G_blocked = G.copy()

    # ==========================================
    # SCENARIO A: SINGLE POINT
    # ==========================================
    if len(coords) == 1:
        pt_lng = coords[0]["lng"]
        pt_lat = coords[0]["lat"]

        u, v, key = ox.distance.nearest_edges(G, X=pt_lng, Y=pt_lat)
        blocked_edges = edges.loc[[(u, v, key)]]

        try: 
            G_blocked.remove_edge(u, v, key)
        except: pass
        
        try: 
            G_blocked.remove_edge(v, u, 0)
        except: pass

        start_node = u
        end_node = v
        corridor_geojson = None 

    # ==========================================
    # SCENARIO B: DRAWN LINE
    # ==========================================
    else:
        line_coords = [(p["lng"], p["lat"]) for p in coords]
        line = LineString(line_coords)
        corridor = line.buffer(0.0002)
        
        blocked_edges = edges[edges.intersects(corridor)]

        for idx in blocked_edges.index:
            try:
                G_blocked.remove_edge(idx[0], idx[1], idx[2])
            except: pass

        isolated_nodes = list(nx.isolates(G_blocked))
        G_blocked.remove_nodes_from(isolated_nodes)

        start_node = ox.distance.nearest_nodes(G_blocked, X=coords[0]["lng"], Y=coords[0]["lat"])
        end_node = ox.distance.nearest_nodes(G_blocked, X=coords[-1]["lng"], Y=coords[-1]["lat"])
        
        corridor_geojson = mapping(corridor)

    # -----------------------------------
    # Distance & Route Calculation
    # -----------------------------------
    try:
        original_length = nx.shortest_path_length(G, start_node, end_node, weight="length")
        
        print("Calculating detour route...")
        route = nx.shortest_path(
            G_blocked,
            start_node,
            end_node,
            weight="length"
        )
        detour_length = nx.shortest_path_length(G_blocked, start_node, end_node, weight="length")
        length_increase = max(0.0, detour_length - original_length)
        print("Route found!")

    except nx.NetworkXNoPath:
        print("NO PATH FOUND")
        return JSONResponse(
            content={"status": "error", "message": "No detour available"}
        )

    route_coords = []
    for node in route:
        route_coords.append([G.nodes[node]["y"], G.nodes[node]["x"]])

    blocked_geojson = blocked_edges.to_json()

    return JSONResponse(
        content={
            "status": "success",
            "buffer": corridor_geojson,
            "blocked_roads": blocked_geojson,
            "detour_route": route_coords,
            "original_length": round(original_length, 2),
            "detour_length": round(detour_length, 2),
            "length_increase": round(length_increase, 2)
        }
    )
