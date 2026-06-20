# setup_map.py
import osmnx as ox

print("Downloading Bengaluru road network... Please wait.")

# Download the drivable road network for Bengaluru
G = ox.graph_from_place("Bengaluru, India", network_type="drive")

print("Download complete. Saving to disk...")

# Save it locally as a graphml file
ox.save_graphml(G, filepath="bengaluru_drive.graphml")

print("Saved successfully as bengaluru_drive.graphml! You can now run your FastAPI server.")