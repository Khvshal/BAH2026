"""
FastAPI Server for Standalone Lunar Rover Path Planning
======================================================
Provides RESTful endpoints for terrain visualization, A* traverse computation,
and real-time energy telemetry. Serves the interactive web visualizer at `/`.
"""

import os
import sys
import io
import base64
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Add parent directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from algorithms import build_cost_map, weighted_astar, smooth_path_rdp, compute_energy_profile
from data import load_or_generate_terrain

app = FastAPI(
    title="Lunar Rover Path Planning API",
    description="Standalone microservice for lunar polar path planning, obstacle avoidance, and energy budget analysis.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache loaded terrain in memory
TERRAIN_CACHE = {}


def get_terrain() -> Dict[str, Any]:
    global TERRAIN_CACHE
    if not TERRAIN_CACHE:
        TERRAIN_CACHE = load_or_generate_terrain(size=256)
    return TERRAIN_CACHE


def array_to_base64_png(arr: np.ndarray, cmap: str = "terrain") -> str:
    """Converts a 2D float array into a color-mapped base64 PNG string."""
    norm = plt.Normalize(vmin=float(arr.min()), vmax=float(arr.max()))
    colored = plt.get_cmap(cmap)(norm(arr))
    img_bytes = (colored[:, :, :3] * 255).astype(np.uint8)
    img = Image.fromarray(img_bytes)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------
class RoverSpec(BaseModel):
    battery_wh: float = 500.0
    solar_panel_w: float = 150.0
    drive_power_w: float = 100.0
    speed_m_per_s: float = 0.1
    recharge_threshold_pct: float = 20.0
    recharge_duration_hours: float = 0.5


class PlanRequest(BaseModel):
    start: List[int] = [46, 51]   # [row, col]
    goal: List[int] = [174, 143]  # [row, col]
    w: float = 1.5                # Heuristic weight
    max_slope: float = 15.0       # Steepness hazard threshold
    rover_spec: Optional[RoverSpec] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Lunar Rover Path Planning API"}


@app.get("/api/terrain")
def get_terrain_data():
    """Returns terrain metadata, landmark options, and visual layer thumbnails."""
    t = get_terrain()
    slope = t["slope"]
    elevation = t["elevation"]
    psr = t["psr_mask"]
    pixel_size = t["pixel_size_m"]

    # Generate quick layer images
    elev_png = array_to_base64_png(elevation, cmap="terrain")
    slope_png = array_to_base64_png(slope, cmap="inferno")
    psr_png = array_to_base64_png(psr, cmap="Blues_r")

    return {
        "grid_shape": [int(slope.shape[0]), int(slope.shape[1])],
        "pixel_size_m": pixel_size,
        "landmarks": t["landmarks"],
        "layers": {
            "elevation": elev_png,
            "slope": slope_png,
            "psr": psr_png,
        },
    }


@app.post("/api/plan")
def plan_route(req: PlanRequest):
    """Computes optimal path and telemetry for given start/goal and rover specs."""
    t = get_terrain()
    slope = t["slope"]
    roughness = t["roughness"]
    psr = t["psr_mask"]
    pixel_size = t["pixel_size_m"]

    # Build cost surface
    cost_map = build_cost_map(
        slope,
        roughness,
        psr,
        pixel_size_m=pixel_size,
        max_slope_limit=req.max_slope,
    )

    start = (int(req.start[0]), int(req.start[1]))
    goal = (int(req.goal[0]), int(req.goal[1]))

    raw_path = weighted_astar(cost_map, start, goal, w=req.w)
    if not raw_path:
        raise HTTPException(
            status_code=400,
            detail="No navigable path found! Start or goal may be isolated by steep obstacles (> 15°).",
        )

    # Path simplification
    smooth_path = smooth_path_rdp(raw_path, epsilon=1.5)

    # Rover spec
    spec_dict = req.rover_spec.dict() if req.rover_spec else None
    energy_res = compute_energy_profile(
        raw_path,
        slope,
        psr,
        pixel_size_m=pixel_size,
        rover_spec=spec_dict,
    )

    # Format return
    return {
        "raw_path": [[int(r), int(c)] for r, c in raw_path],
        "smooth_path": [[int(r), int(c)] for r, c in smooth_path],
        "telemetry": energy_res["telemetry"],
        "total_distance_m": energy_res["total_distance_m"],
        "total_time_hours": energy_res["total_time_hours"],
        "min_battery_pct": energy_res["min_battery_pct"],
        "max_slope_deg": energy_res["max_slope_deg"],
    }


# ---------------------------------------------------------------------------
# UI Static Mounting
# ---------------------------------------------------------------------------
UI_DIR = os.path.join(BASE_DIR, "ui")
if os.path.exists(UI_DIR):
    app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

    @app.get("/")
    def serve_ui():
        return FileResponse(os.path.join(UI_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    # Pre-load terrain on launch
    get_terrain()
    print("[Server] Starting Lunar Rover Path Planning server on http://localhost:8500")
    uvicorn.run(app, host="0.0.0.0", port=8500)
