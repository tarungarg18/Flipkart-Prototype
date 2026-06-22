# Smart Traffic Command Center

### AI-Powered Event-Driven Traffic Intelligence for Bengaluru

**Smart Traffic Command Center** predicts how badly a planned or unplanned event will disrupt Bengaluru traffic — **before the event begins**. Given a location and event details, it returns a severity score, a road-closure decision, recommended barricade and manpower counts, a diversion strategy, and a live reroute map across the city's real road network.

> *From reactive incident response to predictive traffic command — helping control rooms decide before disruption starts.*

---

## 🔗 Live Demo

> **🌐 Deployed app:** **[smart-traffic-command-center.streamlit.app](https://smart-traffic-control-center.streamlit.app/)**

---

## 📌 Overview

Traffic control today is **reactive**. When a protest, VIP movement, festival, or accident occurs, there is no tool that tells the control room how severe it will be, whether a road must close, or how many personnel to deploy — so resources are estimated by hand, *after* disruption has already begun.

Smart Traffic Command Center addresses this by turning **8,173 historical Bengaluru Traffic Police events** into live, quantified decisions. Operators draw the affected location on an interactive map, enter the event details, and instantly receive an evidence-based response plan plus a routing recommendation computed over the full Bengaluru road graph.

---

## 🎯 Objectives

- Quantify event-driven traffic disruption **before** it happens
- Replace manual severity guesses with a data-driven score
- Recommend right-sized barricade and manpower deployment
- Provide an actionable reroute for closed corridors
- Log outcomes so the system can keep improving over time

---

## ✨ Key Features

### 🗺️ Interactive Predictor
- Draw a **point** or a **road stretch** directly on a Bengaluru map
- Address autocomplete and reverse geocoding via Geoapify
- Automatic corridor detection from the real road network
- Live prediction the moment you hit **Predict**

### 🧠 Severity & Closure Prediction
- **Severity Score (0–10)** quantifying expected disruption
- **Road-closure decision** with a tuned confidence percentage
- **Barricade count** via a gravity-style formula
- **Manpower plan** scaled to severity and event tier
- **Diversion strategy** recommendation

### 🛣️ Live Reroute Engine
- Routing across the full **~393,000-edge** Bengaluru road graph
- Closed road shown in **red**, best detour in **green**, with added-distance metric
- Follows true road geometry — detours trace real streets, not straight lines

### 📋 Transparent Assumptions
- Every model threshold, cause weight, and known corridor surfaced as readable cards — no black box

### 🔍 Evaluation & Feedback Loop
- Searchable history of every prediction
- Log post-event actuals (severity, barricades, manpower) — the foundation for retraining

### 📊 Analytics
- Severity distribution, events by cause, hourly patterns, predicted-vs-actual
- One-click CSV export

---

## 🧪 Models & Performance

Two gradient-boosting models run in a chain — the closure classifier's output becomes a feature for the severity regressor.

| Model | Algorithm | Features | Metric |
|---|---|---|---|
| Closure Classifier | Gradient Boosting Classifier | 62 | **ROC-AUC 0.989** |
| Severity Regressor | Gradient Boosting Regressor | 64 | **R² 0.999** |

- Closure threshold tuned to **0.65** (not the default 0.5) to balance false alarms against missed closures.
- **~95% of severity is location-driven** — corridor and spatial-cluster priority matter far more than the event cause alone.
- Train/test split happens **before** any aggregate feature is computed, so corridor/zone/cluster rates never leak test data.

---

## 📚 Dataset

- **Source:** Astram — Bengaluru Traffic Police internal event-logging system
- **8,173** anonymized traffic events · **46** raw columns each
- Transformed into **62–64 engineered features**: incident span (Haversine), cyclical time encoding, corridor/zone/cluster priority rates, cause tiers, rush-hour and heavy-vehicle flags

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│         Historical Traffic Events (Astram, 8,173 rows)       │
└───────────────────────────────┬──────────────────────────────┘
                                ▼
┌────────────────────────────────────────────────────────────┐
│   Feature Engineering  →  62–64 model-ready features         │
│   (geometry, cyclical time, corridor/cluster priority rates) │
└───────────────────────────────┬──────────────────────────────┘
                                ▼
┌────────────────────────────────────────────────────────────┐
│   Inference Runtime (runtime.py)                             │
│   Closure Classifier → severity feature → Severity Regressor │
│   + barricade / manpower / diversion logic                   │
└───────────────────────────────┬──────────────────────────────┘
                                ▼
┌────────────────────────────────────────────────────────────┐
│   Streamlit Command Center                                   │
│   Predictor · Assumptions · Evaluation · Analytics           │
│   + osmnx/folium live reroute map                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| **App / UI** | Streamlit · folium · streamlit-folium |
| **ML & Data** | scikit-learn · pandas · numpy · joblib |
| **Geospatial / Routing** | osmnx · networkx · geopandas · shapely |
| **Geocoding** | Geoapify API |
| **Analytics** | plotly |

---

## 📂 Project Structure

```
Dashboard/
├── app.py                      # Entry point — page config + CSS
├── pages_src/
│   └── home.py                 # All four pages and the prediction UI
├── models/
│   ├── runtime.py              # Rebuilds engineered features + runs inference
│   ├── predictor.py            # Input mapping + corridor detection
│   └── *.joblib                # Trained models, feature lists, lookups
├── utils/
│   ├── routing.py              # Road graph, closure detection, reroute engine
│   ├── geoapify.py             # Address search / reverse geocode
│   ├── history.py              # JSON-backed prediction history
│   └── styles.py               # CSS
├── bengaluru_drive.graphml     # Road network (Git LFS, ~130 MB)
├── requirements.txt
└── README.md
```

---

## 🚀 Installation & Setup

**Prerequisites:** Python 3.11–3.13

### Option A — From the source zip (recommended)
1. Extract the zip and open a terminal inside the project folder.

### Option B — Clone from GitHub
```bash
git clone <your-repo-url>
cd Dashboard
```
> *Optional:* run `git lfs install` before cloning to fetch the prebuilt road graph. If skipped, the app downloads the network from OpenStreetMap automatically on first run.

### Setup & Run (common to both)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your Geoapify API key (address search + reverse geocoding)
#    Rename .streamlit/secrets.toml.example -> .streamlit/secrets.toml and set:
#    GEOAPIFY_KEY = "your_key_here"
#    (Free key at geoapify.com. App still runs without it — shows coordinates
#     instead of street names.)

# 3. Launch
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🧭 How to Use

1. On the **Predictor** page, draw a line along a road (e.g. *Old Airport Road*) — drawing a stretch, not a point, lets the model detect closures.
2. Select an **Event Cause** (e.g. *VIP Movement*) and a **time**.
3. Click **Predict Severity**.
4. Review the severity score, closure decision, barricade/manpower plan, and the live reroute map.
5. Explore **Assumptions**, log outcomes in **Evaluation**, and view trends in **Analytics**.

> ⏱️ The first prediction loads the Bengaluru road network (~60s). Every prediction afterward is instant.

---

## 🛣️ Roadmap

- Live traffic ingestion (Google Maps / TomTom / HERE) for real-time congestion-aware routing
- Top-3 ranked diversions (k-shortest-path) instead of a single detour
- Continuous feedback loop — dispatcher-confirmed outcomes feed periodic retraining
- Predictive congestion forecasting and incident hotspot detection
- Multi-city support with configurable geospatial layers

---

## 🔒 Notes

- Models were trained with **scikit-learn 1.7.2**; other versions may emit harmless unpickle warnings.
- Never commit API keys — use `.streamlit/secrets.toml` (gitignored) or a `GEOAPIFY_KEY` environment variable.
- The road graph is tracked via Git LFS; the app falls back to an OpenStreetMap download if it is unavailable.

