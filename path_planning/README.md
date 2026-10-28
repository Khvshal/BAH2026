# 🌕 Lunar Rover Path Planning & Energy Telemetry Toolkit

An end-to-end, modular Python package and interactive mission control dashboard for autonomous planetary rover route planning across complex lunar polar terrain.

Originally engineered for the **POLARIS** lunar water-ice prospecting architecture (Bharatiya Antariksh Hackathon / BAH2026), this module isolates the complete pathfinding, terrain traversability evaluation, obstacle avoidance, and battery/solar energy budget simulation pipelines into a self-contained, dependency-light package.

---

## 📑 Table of Contents

- [Overview & Architecture](#-overview--architecture)
- [Comprehensive Folder & File Directory](#-comprehensive-folder--file-directory)
- [Algorithms Implemented](#-algorithms-implemented)
  - [1. Breadth-First Search (BFS)](#1-breadth-first-search-bfs)
  - [2. Depth-First Search (DFS)](#2-depth-first-search-dfs)
  - [3. Depth-Limited Search (DLS)](#3-depth-limited-search-dls)
  - [4. Dijkstra's Uniform-Cost Search](#4-dijkstras-uniform-cost-search)
  - [5. Weighted A* Graph Search](#5-weighted-a-graph-search)
- [Core Mathematical & Scientific Models](#-core-mathematical--scientific-models)
  - [Lunar Terrain & Lommel-Seeliger Reflectance Model](#lunar-terrain--lommel-seeliger-reflectance-model)
  - [Multi-Factor Cost Surface Formulation](#multi-factor-cost-surface-formulation)
  - [Ramer-Douglas-Peucker (RDP) Waypoint Simplification](#ramer-douglas-peucker-rdp-waypoint-simplification)
  - [Solar & Battery State-of-Charge (SoC) Telemetry](#solar--battery-state-of-charge-soc-telemetry)
- [Benchmark Suite](#-benchmark-suite)
- [Installation & Setup](#-installation--setup)
- [Execution Modes](#-execution-modes)
- [REST API Reference](#-rest-api-reference)
- [Data Ingestion & Real OHRC / DEM Support](#-data-ingestion--real-ohrc--dem-support)

---

## 🧭 Overview & Architecture

Operating a lunar rover at the lunar south pole entails extreme operational challenges:
- **Steep Topography**: Deep impact craters with slopes exceeding 15°–30° risk catastrophic wheel slip or vehicle rollover.
- **Harsh Lighting Geometry**: Solar elevation sits at grazing angles ($\sim 1.5^\circ$), casting deep, pitch-black shadows into Permanently Shadowed Regions (PSRs).
- **Power Budgets**: Traversal through PSRs cuts off solar panel generation entirely, demanding precise battery state-of-charge monitoring and scheduled emergency solar recharge halts.

This toolkit solves these problems through an integrated pipeline:

```
[Digital Elevation Model / Real OHRC Image]
                     │
                     ▼
       Terrain Feature Extraction
       (Slope, Roughness, PSR Shadow Mask)
                     │
                     ▼
      Composite Cost Map Formulation
   (Inclination Work + Rollover Barriers + Sun Incentive)
                     │
                     ▼
        Graph Search (5 Algorithms)
      BFS / DFS / DLS / Dijkstra / A*
       (Kinematic 8-Neighbor Grid)
                     │
                     ▼
          RDP Waypoint Simplification
     (Reduces Dense Pixels to Primary Waypoints)
                     │
                     ▼
       Step-by-Step Energy & Telemetry Model
   (Power Draw, Solar Influx, Battery SoC, Auto-Recharge)
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  [Headless CLI Demo]   [FastAPI + Web HUD UI]
  4-Panel Diagnostics    Interactive Rover Playback
```

---

## 📂 Comprehensive Folder & File Directory

Every file in this folder serves a dedicated, modular purpose:

```text
path_planning/
├── algorithms/                    # Mathematical, heuristic, and physical models
│   ├── __init__.py                # Package exports for all search algorithms
│   ├── search_common.py           # Shared SearchResult schema, 8-connected kinematics, validation
│   ├── astar.py                   # Weighted A* graph search (priority queue + Euclidean heuristic)
│   ├── bfs.py                     # Breadth-First Search (FIFO queue, unweighted)
│   ├── dfs.py                     # Depth-First Search (iterative LIFO stack)
│   ├── dls.py                     # Depth-Limited Search (DFS with configurable depth cutoff)
│   ├── dijkstra.py                # Dijkstra's uniform-cost search (min-heap priority queue)
│   ├── cost_map.py                # Multi-factor traversability cost surface generator
│   ├── energy_model.py            # Physics-based rover power, solar, and battery simulator
│   └── smoother.py                # RDP waypoint pruning & linear path resampling
│
├── api/                           # Backend REST microservice
│   ├── __init__.py                # API package initializer
│   └── server.py                  # FastAPI service serving API endpoints & the web visualizer
│
├── data/                          # Map generation, terrain caching & data ingestion
│   ├── __init__.py                # Data package exports
│   ├── sample_maps.py             # Synthetic crater generator & real Chandrayaan-2 OHRC loader
│   └── terrain_cache_256.npz      # Cached precomputed terrain layers (256x256 at 5m/pixel)
│
├── experiments/                   # Reproducible comparative benchmark suite
│   ├── benchmark_config.json      # 15 stratified route pairs + algorithm configuration
│   ├── generate_benchmark_pairs.py # Curates & verifies benchmark pairs with Dijkstra ground truth
│   ├── evaluate_path.py           # Independent path validator & energy telemetry evaluator
│   ├── run_benchmark.py           # Full benchmark runner: CSV, JSON, figures, and markdown report
│   └── results/                   # Generated benchmark output
│       ├── benchmark_results.csv  # Raw per-trial results (135 rows)
│       ├── benchmark_summary.csv  # Aggregate statistics per algorithm configuration
│       ├── pairwise_comparison.csv # Each algorithm vs. Dijkstra optimal reference
│       ├── benchmark_manifest.json # Experiment metadata and reproducibility manifest
│       ├── benchmark_report.md    # Auto-generated research report
│       └── figures/               # Publication-quality diagnostic plots (7 figures)
│           ├── runtime_comparison.png
│           ├── node_expansions_comparison.png
│           ├── path_distance_comparison.png
│           ├── terrain_cost_comparison.png
│           ├── success_rate_comparison.png
│           ├── energy_and_battery_soc_comparison.png
│           └── path_overlays_terrain.png
│
├── tests/                         # Automated test suite
│   ├── __init__.py                # Tests package initializer
│   └── test_search_algorithms.py  # 15 unit tests: edge cases, correctness, determinism
│
├── ui/                            # Frontend browser-based mission control HUD
│   ├── index.html                 # Semantic HTML5 dashboard, canvas viewport & controls
│   ├── style.css                  # Sci-fi dark glassmorphic stylesheet & responsive HUD theme
│   └── app.js                     # Canvas multi-layer renderer, interactive clicks & charts
│
├── cli_demo.py                    # Standalone terminal demo generating a 4-panel diagnostic plot
├── requirements.txt               # Strict Python dependencies
├── traverse_plan_result.png       # Generated publication-quality 4-panel diagnostic image
└── README.md                      # This file
```

---

## 🔍 Algorithms Implemented

All five algorithms operate on an identical 8-connected grid with shared kinematics, obstacle thresholds, and diagonal corner-cutting prevention via the common [`search_common.py`](algorithms/search_common.py) framework. Every algorithm returns a standardized `SearchResult` dataclass.

### 1. Breadth-First Search (BFS)
**File:** [`algorithms/bfs.py`](algorithms/bfs.py)

- **Data Structure:** FIFO queue (`collections.deque`)
- **Optimality:** Guarantees minimum **hop count** (graph edge count) — NOT minimum physical distance or terrain cost
- **Completeness:** Complete on finite grids
- **Use Case:** Baseline unweighted reference; finds shortest-edge-count path regardless of terrain difficulty

### 2. Depth-First Search (DFS)
**File:** [`algorithms/dfs.py`](algorithms/dfs.py)

- **Data Structure:** Iterative LIFO stack (avoids Python recursion limit)
- **Optimality:** **Not optimal** — produces deep, winding, circuitous routes with high terrain cost
- **Completeness:** Complete on finite grids (visited set prevents cycles)
- **Use Case:** Uninformed baseline demonstrating the pathology of unguided depth-first exploration on spatial grids

### 3. Depth-Limited Search (DLS)
**File:** [`algorithms/dls.py`](algorithms/dls.py)

- **Data Structure:** Iterative LIFO stack with depth tracking and linked-list path reconstruction
- **Parameters:** Configurable `depth_limit` (max edges from start); `max_expansions` safety cap (default 250,000)
- **Termination Semantics:**
  - `DEPTH_LIMIT_EXCEEDED` — search was cut off by depth constraint
  - `EXHAUSTED_NO_SOLUTION` — proved goal unreachable within the depth radius
- **Use Case:** Demonstrates depth-cutoff dynamics and the relationship between depth limit and route feasibility

### 4. Dijkstra's Uniform-Cost Search
**File:** [`algorithms/dijkstra.py`](algorithms/dijkstra.py)

- **Data Structure:** Min-heap priority queue (`heapq`)
- **Optimality:** **Provably cost-optimal** for non-negative edge weights — serves as **ground truth reference**
- **Completeness:** Complete for finite non-negative cost graphs
- **Use Case:** Definitive optimal baseline; all other algorithms are compared against Dijkstra's terrain cost

### 5. Weighted A* Graph Search
**File:** [`algorithms/astar.py`](algorithms/astar.py)

- **Evaluation Function:** $f(n) = g(n) + w \cdot h(n)$
- **Heuristic:** Admissible Euclidean distance scaled by minimum passable cost: $h(n) = w \cdot \min(C) \cdot d_{\text{Euclid}}(n, \text{goal})$
- **Weight $w$:** Default $w = 1.5$. At $w = 1.0$, equivalent to optimal A*; at $w > 1.0$, trades slight sub-optimality for substantial speedup
- **8-Connected Kinematics:** Orthogonal step cost $= \Delta \cdot \frac{C_1 + C_2}{2}$, diagonal step cost $= \sqrt{2} \Delta \cdot \frac{C_1 + C_2}{2}$
- **Use Case:** Primary mission planning algorithm — near-optimal paths with dramatically reduced search space

---

## 🔬 Core Mathematical & Scientific Models

### Lunar Terrain & Lommel-Seeliger Reflectance Model
Lunar regolith exhibits extreme backscattering (opposition surge) and porous micro-shadowing that Lambertian reflectance models cannot accurately represent.

When synthetic terrain is generated in [`data/sample_maps.py`](data/sample_maps.py), the optical brightness is modeled using the Lommel-Seeliger law:
$$\mu_0 = \max(0, \vec{n} \cdot \vec{s}), \quad \mu = \vec{n} \cdot \vec{v}$$
$$I_{\text{reflectance}} = \frac{\mu_0}{\mu_0 + \mu}$$
Where:
- $\vec{s}$ is the solar illumination unit vector at azimuth $119.2^\circ$ and polar elevation $1.5^\circ$.
- $\vec{n}$ is the local terrain surface normal derived from DEM spatial gradients $\nabla z = \left(\frac{\partial z}{\partial x}, \frac{\partial z}{\partial y}\right)$.
- $\vec{v}$ is the nadir camera viewing vector $(0, 0, 1)$.

### Multi-Factor Cost Surface Formulation
The per-pixel cost scalar $C(r, c)$ in [`algorithms/cost_map.py`](algorithms/cost_map.py) evaluates three primary hazards:

$$C(r, c) = C_{\text{incline}}(\theta) + C_{\text{safety}}(\theta, R) + C_{\text{illumination}}(P)$$

1. **Inclination Mechanical Work**:
   $$C_{\text{incline}}(\theta) = 1.0 + 8.0 \cdot \sin(\theta)$$
2. **Safety Penalties & Rollover Thresholds**:
   $$C_{\text{safety}}(\theta, R) = \begin{cases} 
   10^6 & \text{if } \theta > 15.0^\circ \text{ (Rollover Hazard / Impassable)} \\
   +50.0 & \text{if } 10.0^\circ < \theta \le 15.0^\circ \text{ (Caution Margin)} \\
   0 & \text{otherwise}
   \end{cases} \quad + \quad (10.0 \cdot R)$$
   Where $R \in [0, 1]$ is the local micro-roughness.
3. **Illumination Preference**:
   $$C_{\text{illumination}}(P) = \begin{cases} 
   +5.0 & \text{if in Permanently Shadowed Region (PSR)} \\
   -1.0 & \text{if sunlit (Incentivizes solar exposure)}
   \end{cases}$$

### Ramer-Douglas-Peucker (RDP) Waypoint Simplification
Dense raster grid paths generate staircase micro-steps. [`algorithms/smoother.py`](algorithms/smoother.py) compresses the path by identifying points with perpendicular distance $> \epsilon$ (default $\epsilon = 1.5$ pixels):
$$d_{\perp} = \frac{|(y_2 - y_1)x_0 - (x_2 - x_1)y_0 + x_2 y_1 - y_2 x_1|}{\sqrt{(y_2 - y_1)^2 + (x_2 - x_1)^2}}$$
This condenses paths from $>300$ grid steps down to 20–40 distinct navigation waypoints suitable for uplink to an onboard guidance computer.

### Solar & Battery State-of-Charge (SoC) Telemetry
The physical simulation in [`algorithms/energy_model.py`](algorithms/energy_model.py) models:
- **Motor Locomotion Power**:
  $$P_{\text{drive}} = P_{\text{base}} \cdot \left(1.0 + 2.0 \cdot \sin(\max(0, \theta))\right) \quad [W]$$
- **Solar Generation**:
  $$P_{\text{solar}} = P_{\text{peak}} \cdot (1 - \text{PSR}) \quad [W]$$
- **Battery Update**:
  $$E_{t+\Delta t} = \min\left(E_{\text{max}}, E_t + (P_{\text{solar}} - P_{\text{drive}}) \cdot \Delta t\right) \quad [Wh]$$
- **Autonomous Recharge Halt**: If $SoC < 20\%$, the rover stops driving for $0.5\text{ hours}$ in sunlight to replenish battery reserves before resuming navigation.

---

## 📊 Benchmark Suite

The `experiments/` directory contains a full reproducible benchmark comparing all 5 algorithms across **15 stratified lunar terrain route pairs** (135 total trials):

### Route Categories
| Category | Pairs | Description |
|----------|-------|-------------|
| SHORT | 3 | 20–45 cell Euclidean distance, gentle terrain |
| MEDIUM | 4 | 50–110 cell distance, mixed topography |
| LONG | 3 | 120–200+ cell distance, major traverses |
| OBSTACLE_DETOUR | 2 | Direct line blocked by >15° slopes |
| STEEP_MARGIN | 1 | Routes along caution-limit slopes (10°–15°) |
| PSR_COLD_TRAP | 2 | Enters permanently shadowed cold-trap regions |

### Benchmark Outputs
- **`benchmark_results.csv`**: 135 rows of per-trial raw metrics
- **`benchmark_summary.csv`**: Aggregate statistics per algorithm configuration
- **`pairwise_comparison.csv`**: Each algorithm vs. Dijkstra optimal reference (distance/cost/runtime ratios)
- **`benchmark_manifest.json`**: Full experiment metadata and reproducibility manifest
- **`benchmark_report.md`**: Auto-generated comprehensive research report
- **7 publication-quality figures**: Runtime, node expansions, path distance, terrain cost, success rate, energy/battery, and path overlays

### Running the Benchmark
```powershell
# Full benchmark (135 trials)
python experiments/run_benchmark.py

# Smoke test (quick validation)
python experiments/run_benchmark.py --smoke-test
```

### Running Tests
```powershell
pytest tests/test_search_algorithms.py -v
```

---

## 🛠️ Installation & Setup

Ensure Python 3.9+ is installed.

```powershell
# Navigate to the path_planning directory
cd "c:\Users\Admin\Desktop\TY PROJECTS\AI LAB\BAH2026\path_planning"

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Execution Modes

### Mode A: CLI Demo & 4-Panel Diagnostic Matplotlib Plot

Run the standalone CLI pipeline:
```powershell
python cli_demo.py
```

#### Optional CLI Arguments:
```powershell
python cli_demo.py --start 46 51 --goal 174 143 --w 1.5 --max-slope 15.0 --out my_plan.png
```

#### Sample Terminal Output:
```text
=================================================================
      LUNAR ROVER PATH PLANNING & ENERGY TELEMETRY PIPELINE
=================================================================

[1/5] Ingesting lunar polar terrain maps...
  * Origin: Alpha Ridge (Primary) at grid (46, 51)
  * Destination: Shoemaker Deep PSR Cache at grid (174, 143)
  * Terrain Grid Size: 256x256 (pixel res = 5.0m)

[2/5] Building composite traversability cost surface...
  * Safe navigable terrain: 88.4%
  * Hazardous/Impassable (>15° slope): 11.6%

[3/5] Executing Weighted A* graph search (w=1.5)...
  * Raw A* path found: 172 grid steps.

[4/5] Smoothing path via Ramer-Douglas-Peucker (RDP)...
  * Path simplified to: 28 primary drive waypoints.

[5/5] Simulating rover battery discharge and solar charging...

TRAVERSE MISSION SUMMARY:
-----------------------------------------------------------------
  * Physical Traverse Length:  1,061.2 metres (1.06 km)
  * Mission Elapsed Time:      3.21 hours
  * Maximum Slope Traversing:  8.4° (Safe: < 15.0°)
  * Minimum Battery Level:     78.2% (No critical depletion)
  * Solar Recharge Stops:      0
-----------------------------------------------------------------
[SUCCESS] Diagnostic 4-panel plot saved to: traverse_plan_result.png
```

---

### Mode B: Interactive Mission Control Web Interface

Start the local FastAPI server:
```powershell
python api/server.py
```

Then open your browser to:
👉 **[http://localhost:8500](http://localhost:8500)**

#### Web Visualizer Features:
- **Interactive Waypoint Pinning**: Left-click on the map to set Start (green pin); right-click or Shift-click to set Goal (red pin).
- **Preset Selection**: Instant dropdown presets for lunar landing sites and science targets.
- **Multi-Layer Toggle**: Switch between **OHRC Optical**, **LOLA DEM Elevation**, **Slope Hazard Heatmap**, and **PSR Shadow Masks**.
- **Hazard Overlays**: Translucent red hazard masking dynamically highlights slopes exceeding your chosen threshold.
- **Hardware Parameter Controls**: Adjust battery capacity ($Wh$), solar panel output ($W$), drive power ($W$), rover speed ($m/s$), and heuristic weight ($w$).
- **Animated Playback**: Step-by-step rover drive playback with real-time heading orientation, battery readout, and power meters.
- **Telemetry Charts**: Embedded canvas graphs showing battery discharge and net power over mission elapsed time.

---

## 📡 REST API Reference

The FastAPI service exposes three primary endpoints:

### 1. Health Status
`GET /api/health`
```json
{
  "status": "ok",
  "service": "Lunar Rover Path Planning API"
}
```

### 2. Terrain Data & Visual Layers
`GET /api/terrain`
Returns terrain dimensions, metric resolution, landmark positions, and base64-encoded PNG strings for each layer (`optical`, `elevation`, `slope`, `psr`).

### 3. Plan Traverse Route
`POST /api/plan`

#### Request Payload:
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
    "speed_m_per_s": 0.1,
    "recharge_threshold_pct": 20.0,
    "recharge_duration_hours": 0.5
  }
}
```

#### Response Payload:
```json
{
  "raw_path": [[46, 51], [47, 52], "..."],
  "smooth_path": [[46, 51], [58, 62], "..."],
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
  "total_distance_m": 1061.2,
  "total_time_hours": 3.21,
  "min_battery_pct": 78.2,
  "max_slope_deg": 8.4
}
```

---

## 🛰️ Data Ingestion & Real OHRC / DEM Support

This module supports seamless drag-and-drop ingestion of real Chandrayaan-2 Orbiter High Resolution Camera (OHRC) or LROC imagery:

1. Place any calibrated lunar surface image into the `data/` folder named as:
   - `data/ohrc_base.png` (or `.jpg`, `.jpeg`, `.npy`)
2. Restart the server or run `cli_demo.py`.
3. The loader in [`data/sample_maps.py`](data/sample_maps.py) automatically detects the file, resizes it to match grid coordinates, and uses it as the optical base layer.
4. If no custom file is provided, the system falls back to the deterministic Lommel-Seeliger synthetic polar crater simulation stored in `data/terrain_cache_256.npz`.
