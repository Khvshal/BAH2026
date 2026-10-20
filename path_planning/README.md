# Lunar Rover Path Planning & Energy Telemetry Toolkit

A modular, self-contained Python package and web-based mission control interface for autonomous planetary rover route planning across lunar polar terrain.

Originally developed for the **POLARIS** lunar water-ice scouting architecture, this package isolates the complete path planning, obstacle avoidance, and solar/battery budget telemetry pipelines into an independent, plug-and-play module.

---

## 🚀 Key Features

1. **Multi-Factor Cost Surface Formulation (`algorithms/cost_map.py`)**:
   - Terrain inclination mechanical resistance: $E = 1.0 + 8.0 \cdot \sin(\theta)$
   - Hard rollover barrier exclusion for slopes $> 15.0^\circ$ ($C = 10^6$)
   - Friction and boulder roughness penalties
   - Illumination incentive: penalizes permanently shadowed cold traps while rewarding direct solar exposure

2. **Weighted A\* Graph Search (`algorithms/astar.py`)**:
   - 8-connected grid kinematics with diagonal distance weighting ($\sqrt{2}$)
   - Admissible/weighted Euclidean heuristic ($w=1.5$ default) for fast convergence
   - Robust impassable barrier avoidance and boundary safety checks

3. **Ramer-Douglas-Peucker (RDP) Simplification (`algorithms/smoother.py`)**:
   - Compresses dense pixel steps into actionable primary rover waypoints without sacrificing obstacle clearance

4. **Solar & Energy Budget Simulation (`algorithms/energy_model.py`)**:
   - Step-by-step battery State of Charge (SoC %) simulation
   - Incline-dependent mechanical locomotion power draw ($W$)
   - Direct sunlight vs. PSR shadow solar panel power generation
   - Autonomous emergency solar recharge halt triggers when battery $< 20\%$

5. **Dual Operation Modes**:
   - **CLI & Matplotlib Diagnostic Runner (`cli_demo.py`)**: Generates a 4-panel diagnostic plot.
   - **Interactive Web UI & FastAPI Microservice (`api/server.py` + `ui/`)**: Real-time map clicks, kinematic parameter tuning, layer switching (DEM, Slope, PSR), and animated rover playback.

---

## 📂 Directory Structure

```text
path_planning/
├── algorithms/                 # Core mathematical & heuristic algorithms
│   ├── __init__.py
│   ├── astar.py                # Weighted A* search algorithm
│   ├── cost_map.py             # Traversal cost surface builder
│   ├── energy_model.py         # Battery & solar budget simulator
│   └── smoother.py             # RDP waypoint simplification & resampling
├── data/                       # Terrain loaders & synthetic crater generator
│   ├── __init__.py
│   └── sample_maps.py          # Loads POLARIS DEMs or generates polar crater fallback
├── api/                        # Standalone FastAPI service
│   ├── __init__.py
│   └── server.py               # REST API & static UI web server
├── ui/                         # Mission control web visualizer
│   ├── index.html              # Interactive canvas & HUD dashboard
│   ├── style.css               # Cinematic dark mission-control theme
│   └── app.js                  # Client controller, path drawing & telemetry charts
├── cli_demo.py                 # Standalone CLI test & 4-panel plot generator
├── requirements.txt            # Python dependencies
└── README.md                   # Complete documentation
```

---

## 🛠️ Installation

```powershell
cd path_planning
pip install -r requirements.txt
```

*Required libraries: `fastapi`, `uvicorn`, `numpy`, `scipy`, `matplotlib`, `pillow`, `pydantic`.*

---

## 🖥️ Running the CLI Demo

Run the end-to-end path planner and save a publication-quality 4-panel diagnostic plot:

```powershell
python cli_demo.py
```

### Custom Start and Goal Coordinates:
```powershell
python cli_demo.py --start 46 51 --goal 174 143 --out my_traverse_plan.png
```

This outputs detailed terminal statistics:
- Total physical distance (metres / km)
- Estimated mission duration (hours)
- Maximum slope encountered ($^\circ$)
- Minimum battery State of Charge (%)
- Number of autonomous solar recharge stops
- Saves `traverse_plan_result.png`

---

## 🌐 Running the Interactive Web Visualizer

Start the standalone FastAPI server:

```powershell
python api/server.py
```

Then open your browser at:
👉 **[http://localhost:8500](http://localhost:8500)**

### Visualizer Capabilities:
- **Interactive Map Pinning**: Click anywhere on the map to set Start (green) or Goal (red).
- **OHRC Optical Photographic Base Layer**: Projects the route directly on lunar surface panchromatic photography (with toggleable translucent $>15^\circ$ slope hazard overlays).
- **Custom OHRC File Drop**: Simply place any Chandrayaan-2/LROC image as `path_planning/data/ohrc_base.png` (or `.jpg`), and the server will automatically display it. If no file is provided, an authentic Lommel-Seeliger photometric reflectance simulation is generated using the actual Chandrayaan-2 solar geometry ($119.2^\circ$ azimuth, $1.5^\circ$ elevation).
- **Layer Toggles**: Switch between OHRC Optical, LOLA DEM Elevation, Slope Hazard, and PSR Shadows.
- **Hardware Parameter Tuning**: Real-time adjustment of Battery Capacity ($Wh$), Solar Panel Peak ($W$), Drive Draw ($W$), Rover Speed ($m/s$), Heuristic Weight ($w$), and Slope Threshold.
- **Playback Animation**: Scrub or play the rover traverse step-by-step with real-time battery SoC and power balance meters.
- **Telemetry Graph**: Real-time canvas line chart showing battery discharge and solar generation balance.

---

## 📡 REST API Reference

### 1. Health Check
`GET /api/health`
```json
{ "status": "ok", "service": "Lunar Rover Path Planning API" }
```

### 2. Ingest Terrain Metadata
`GET /api/terrain`
Returns grid dimensions, resolution, landmarks, and base64 layer images.

### 3. Compute Route
`POST /api/plan`
```json
{
  "start": [46, 51],
  "goal": [174, 143],
  "w": 1.5,
  "max_slope": 15.0,
  "rover_spec": {
    "battery_wh": 500.0,
    "solar_panel_w": 150.0,
    "drive_power_w": 100.0,
    "speed_m_per_s": 0.1
  }
}
```
**Response**:
```json
{
  "raw_path": [[46, 51], ...],
  "smooth_path": [[46, 51], ...],
  "telemetry": [
    {
      "step": 0,
      "grid_r": 46,
      "grid_c": 51,
      "slope_deg": 3.2,
      "status": "DRIVING",
      "battery_pct": 100.0,
      "solar_in_w": 150.0,
      "drive_w": 108.9,
      "net_w": 41.1,
      "distance_m": 0.0,
      "elapsed_hours": 0.0
    }
  ],
  "total_distance_m": 1245.8,
  "total_time_hours": 3.46,
  "min_battery_pct": 82.4,
  "max_slope_deg": 8.7
}
```
