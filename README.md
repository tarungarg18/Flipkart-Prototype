# Smart Traffic Command Center

A Streamlit dashboard that predicts event-driven traffic disruption for Bengaluru. Given an event's location and details, it returns a severity score (0–10), a road-closure decision, recommended barricade and manpower counts, a diversion plan, and a live reroute map.

Trained on ~8,173 anonymized Bengaluru Traffic Police (Astram) events using two chained gradient-boosting models: a closure classifier feeding a severity regressor.

## Features

- **Predictor** — draw a point or road stretch on an interactive map (address autocomplete via Geoapify) and get a live prediction plus reroute.
- **Assumptions** — model thresholds, cause weights, and known corridors.
- **Evaluation** — searchable prediction history with post-event actuals logging.
- **Analytics** — severity distribution, cause breakdown, hourly patterns, and CSV export.

## Requirements

- Python 3.11–3.13
- Dependencies listed in `requirements.txt`

## Setup

```bash
# clone (the road graph is stored via Git LFS)
git lfs install
git clone <repo-url>
cd Dashboard

# install dependencies
pip install -r requirements.txt
```

Add a Geoapify API key for address search and reverse geocoding. Create `.streamlit/secrets.toml`:

```toml
GEOAPIFY_KEY = "your_key_here"
```

(Alternatively set a `GEOAPIFY_KEY` environment variable.)

## Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Project Structure

```
app.py                  # entry point, page config + CSS
pages_src/home.py       # all four pages and prediction UI
models/
  runtime.py            # rebuilds engineered features and runs inference
  predictor.py          # input mapping for the models
  *.joblib              # trained models, feature lists, lookups
utils/
  routing.py            # osmnx road graph, closure detection, reroute
  geoapify.py           # address search / reverse geocode
  history.py            # JSON-backed prediction history
  styles.py             # CSS
bengaluru_drive.graphml # road network (Git LFS, ~130 MB)
```

## Notes

- The road graph (`bengaluru_drive.graphml`) is tracked with Git LFS. If it's missing, `routing.py` downloads the Bengaluru network from OpenStreetMap on first use.
- Models were trained with scikit-learn 1.7.2; a different version may emit unpickle warnings.

## Tech Stack

Streamlit · scikit-learn · osmnx · networkx · folium · geopandas · Geoapify · plotly
