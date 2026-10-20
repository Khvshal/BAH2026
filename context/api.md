# POLARIS API Specification (v1)

This file documents the REST endpoints and WebSockets available in the POLARIS FastAPI backend server.

## Binds
* **Host**: `0.0.0.0` or `localhost`
* **Port**: `8000`
* **Base URL**: `http://localhost:8000/api/v1`

---

## 1. General & System Status

### `GET /`
Returns the status of the API and database integration.
* **Response**:
  ```json
  {
    "status": "POLARIS API v1 is running",
    "data_source": "real",
    "database": "PostgreSQL + PostGIS connected"
  }
  ```

---

## 2. Terrain & PSR Mapping

### `POST /api/v1/psr/compute`
Triggers the end-to-end PSR and terrain morphology analysis (LOLA DEM + OHRC images). Runs asynchronously. Logs progress via WebSocket.
* **Response**:
  ```json
  {
    "status": "processing_started"
  }
  ```

### `GET /api/v1/psr/craters`
Retrieves the list of detected craters and Permanently Shadowed Regions from PostgreSQL (spatial queries).
* **Response**:
  ```json
  [
    {
      "id": 1,
      "name": "PSR-SouthPole-01",
      "longitude": 25.41928,
      "latitude": -84.9016,
      "area_km2": 70.95,
      "depth_m": 2218.38,
      "diameter_m": 9504.7,
      "min_illumination_pct": 0.0,
      "estimated_temp_k": 40.0,
      "aif": 0.0
    }
  ]
  ```

---

## 3. Polarimetry & Radar Processing

### `POST /api/v1/radar/process`
Triggers the DFSAR polarimetric calibration pipeline (S-band + L-band complex matrix). Runs asynchronously.
* **Response**:
  ```json
  {
    "status": "radar_processing_started"
  }
  ```

### `GET /api/maps/psr`
Retrieves base64-encoded PNG visualizations of terrain parameters.
* **Response**:
  ```json
  {
    "slope_img": "data:image/png;base64,...",
    "psr_img": "data:image/png;base64,...",
    "hazard_img": "data:image/png;base64,...",
    "dsc_img": "data:image/png;base64,...",
    "dem_img": "data:image/png;base64,...",
    "roughness_img": "data:image/png;base64,...",
    "ohrc_img": "data:image/png;base64..."
  }
  ```

### `GET /api/maps/ice`
Retrieves base64-encoded PNG visualizations of polarimetric ice signals.
* **Response**:
  ```json
  {
    "cpr_img": "data:image/png;base64,...",
    "dop_img": "data:image/png;base64,...",
    "ice_prob_img": "data:image/png;base64..."
  }
  ```

### `GET /api/v1/radar/mchi`
Retrieves the Raney m-chi RGB composite base64 PNG.
* **Response**:
  ```json
  {
    "mchi_img": "data:image/png;base64..."
  }
  ```

---

## 4. AI Classifier & Explainability

### `POST /api/v1/ice/classify`
Runs the U-Net++ AI classification model to determine per-pixel ice probability.
* **Response**:
  ```json
  {
    "status": "ice_classification_started"
  }
  ```

### `GET /api/v1/ice/probability`
Retrieves the base64 ice probability map.

### `GET /api/v1/ice/explain/{pixel_x},{pixel_y}`
Computes a dynamic SHAP feature importance explanation for a specific clicked grid pixel.
* **Response**:
  ```json
  {
    "coordinates": { "x": 512, "y": 420 },
    "features": {
      "cpr": 1.45,
      "dop": 0.09,
      "slope_deg": 3.2,
      "roughness_m": 0.45
    },
    "shap_values": {
      "CPR Value": 0.41,
      "DOP Value": 0.35,
      "Slope Constraint": 0.12,
      "Roughness Metric": 0.12
    },
    "verdict": "HIGH CONFIDENCE ICE",
    "probability": 87.3
  }
  ```

---

## 5. Landing Site & Traverse Planning

### `POST /api/v1/landing/score`
Receives custom MCDA weights, recalculates candidate scoring, updates PostgreSQL `landing_sites` table, and returns re-ranked candidates list.
* **Request**:
  ```json
  {
    "ice_proximity_weight": 0.4,
    "terrain_safety_weight": 0.3,
    "solar_illumination_weight": 0.2,
    "dsc_access_weight": 0.05,
    "comm_los_weight": 0.05
  }
  ```
* **Response**: List of candidate landing sites with rank and coordinates.

### `GET /api/v1/landing/top3`
Fetches top landing site candidates from PostgreSQL.

### `POST /api/v1/traverse/plan`
Executes Weighted A* pathfinding on the blended cost grid from a start landing site rank to a target crater. Stores results in `rover_traversals` table.
* **Request**:
  ```json
  {
    "landing_site_rank": 1,
    "crater_id": 1
  }
  ```
* **Response**:
  ```json
  {
    "distance_m": 4320.0,
    "estimated_time_hours": 12.0,
    "max_slope_deg": 8.5,
    "path": [
      { "longitude": 24.99, "latitude": -84.62 },
      ...
    ],
    "energy_profile": [
      { "waypoint": 0, "grid_x": 100, "grid_y": 120, "battery_pct": 100.0, "status": "DRIVING", "solar_in_w": 150.0, "drive_w": 100.0 },
      ...
    ]
  }
  ```

---

## 6. Volumetric Reserves & ISRU

### `POST /api/v1/volume/estimate`
Calculates 3D ice volume and ISRU metrics inside target craters using the Tiuri-Looyenga mixing model. Updates `ice_volume_estimates` database table.
* **Request**:
  ```json
  {
    "crater_id": 1,
    "depth_m": 5.0,
    "baseline_cpr": 0.35
  }
  ```
* **Response**:
  ```json
  {
    "volume_m3": 47200.0,
    "volume_km3": 0.000047,
    "uncertainty_m3": 16500.0,
    "ice_area_km2": 3.74,
    "mean_ice_fraction_pct": 24.3,
    "depth_m": 5.0,
    "water_mass_kg": 43282400.0,
    "astronaut_days": 39400,
    "rocket_propellant_kg": 370000.0
  }
  ```

---

## 7. WebSockets Progress Telemetry

### `WS /ws/processing`
Enables clients to connect to receive progress JSON updates during execution runs (craters compute, radar processing, classifier runs).
* **Outgoing Frame**:
  ```json
  {
    "step": "2/5",
    "progress": 30,
    "message": "Calculating slope and aspect matrices..."
  }
  ```

---

## 8. Standalone Path Planning Microservice (`path_planning/api/server.py`)

* **Binds**: `http://localhost:8500`
* **Static UI**: `http://localhost:8500/`

### `GET /api/health`
Health check for standalone service.
* **Response**: `{"status": "ok", "service": "Lunar Rover Path Planning API"}`

### `GET /api/terrain`
Returns terrain metadata, landmark options, and base64 preview layers.
* **Response**:
  ```json
  {
    "grid_shape": [256, 256],
    "pixel_size_m": 5.0,
    "landmarks": { "landing_sites": [...], "science_targets": [...] },
    "layers": { "elevation": "data:image/png;base64,...", "slope": "...", "psr": "..." }
  }
  ```

### `POST /api/plan`
Executes Weighted A* path planning, RDP smoothing, and full solar/energy telemetry.
* **Request**:
  ```json
  {
    "start": [46, 51],
    "goal": [158, 130],
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
* **Response**:
  ```json
  {
    "raw_path": [[46, 51], ...],
    "smooth_path": [[46, 51], ...],
    "telemetry": [...],
    "total_distance_m": 899.1,
    "total_time_hours": 2.50,
    "min_battery_pct": 100.0,
    "max_slope_deg": 10.0
  }
  ```

