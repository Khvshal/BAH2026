"""
Common Path Validation, Terrain Analysis, and Energy Evaluation
================================================================
Independent validator and telemetry evaluator for lunar rover paths.
Validates path integrity, obstacle clearance, corner-cutting rules,
recalculates geometric and terrain metrics, and simulates energy profile.
"""

import math
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from algorithms.search_common import SQRT2
from algorithms.smoother import smooth_path_rdp, resample_path
from algorithms.energy_model import compute_energy_profile, DEFAULT_ROVER_SPEC


def validate_path(
    path: Optional[List[Tuple[int, int]]],
    start: Tuple[int, int],
    goal: Tuple[int, int],
    cost_map: np.ndarray,
    slope_map: Optional[np.ndarray] = None,
    obstacle_threshold: float = 1e5,
    max_slope_limit: float = 15.0,
    prevent_corner_cutting: bool = True,
) -> Tuple[bool, Optional[str]]:
    """
    Independently verifies path validity against physical and kinematic constraints:
    1. Path exists and is non-empty.
    2. Start matches requested start, goal matches requested goal.
    3. Every waypoint is in-bounds and traversable (< obstacle_threshold).
    4. Consecutive steps are legal 8-connected transitions (dx, dy in {-1, 0, 1}).
    5. Diagonal moves adhere to corner-cutting prevention rules.
    6. If slope_map is provided, ensures no cell exceeds max_slope_limit.

    Returns:
    --------
    (is_valid: bool, error_message: Optional[str])
    """
    if not path or len(path) == 0:
        return False, "EMPTY_PATH"

    rows, cols = cost_map.shape
    s = (int(start[0]), int(start[1]))
    g = (int(goal[0]), int(goal[1]))

    # Check endpoints
    if tuple(path[0]) != s:
        return False, f"START_MISMATCH: expected {s}, got {path[0]}"
    if tuple(path[-1]) != g:
        return False, f"GOAL_MISMATCH: expected {g}, got {path[-1]}"

    # Single-point path (start == goal)
    if len(path) == 1:
        r, c = path[0]
        if not (0 <= r < rows and 0 <= c < cols):
            return False, f"OUT_OF_BOUNDS: cell ({r}, {c})"
        if cost_map[r, c] >= obstacle_threshold:
            return False, f"OBSTACLE_COLLISION: cell ({r}, {c}) cost={cost_map[r, c]}"
        return True, None

    # Step-by-step validation
    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]

        # Bounds
        if not (0 <= r1 < rows and 0 <= c1 < cols):
            return False, f"OUT_OF_BOUNDS: cell ({r1}, {c1}) at step {i}"
        if not (0 <= r2 < rows and 0 <= c2 < cols):
            return False, f"OUT_OF_BOUNDS: cell ({r2}, {c2}) at step {i+1}"

        # Obstacle check on target
        if cost_map[r2, c2] >= obstacle_threshold:
            return False, f"OBSTACLE_COLLISION: cell ({r2}, {c2}) at step {i+1} has cost {cost_map[r2, c2]}"

        if slope_map is not None and slope_map[r2, c2] > max_slope_limit:
            return False, f"EXCESSIVE_SLOPE: cell ({r2}, {c2}) slope={slope_map[r2, c2]:.1f}° > {max_slope_limit}°"

        dr = r2 - r1
        dc = c2 - c1

        # Must be valid 8-connected move
        if abs(dr) > 1 or abs(dc) > 1 or (dr == 0 and dc == 0):
            return False, f"ILLEGAL_TRANSITION: step {i}->{i+1} move ({dr}, {dc}) not 8-connected"

        # Corner cutting check on diagonals
        if prevent_corner_cutting and dr != 0 and dc != 0:
            ortho1_r, ortho1_c = r1 + dr, c1
            ortho2_r, ortho2_c = r1, c1 + dc

            if not (0 <= ortho1_r < rows and 0 <= ortho1_c < cols) or \
               not (0 <= ortho2_r < rows and 0 <= ortho2_c < cols):
                return False, f"CORNER_CUT_OUT_OF_BOUNDS: step {i}->{i+1}"

            if cost_map[ortho1_r, ortho1_c] >= obstacle_threshold or \
               cost_map[ortho2_r, ortho2_c] >= obstacle_threshold:
                return False, f"ILLEGAL_CORNER_CUT: step {i}->{i+1} ({r1},{c1})->({r2},{c2}) cuts through blocked orthogonal cell"

    return True, None


def validate_smoothed_path(
    smooth_path: List[Tuple[int, int]],
    cost_map: np.ndarray,
    slope_map: Optional[np.ndarray] = None,
    obstacle_threshold: float = 1e5,
    max_slope_limit: float = 15.0,
    resample_step: float = 0.5,
) -> Tuple[bool, Optional[str]]:
    """
    Validates whether path smoothing (RDP) introduced any unsafe shortcut
    crossing through obstacles or impassable terrain.
    """
    if not smooth_path or len(smooth_path) < 2:
        return True, None

    rows, cols = cost_map.shape
    dense = resample_path(smooth_path, step_size=resample_step)

    for i, (r_f, c_f) in enumerate(dense):
        r = int(round(r_f))
        c = int(round(c_f))

        if not (0 <= r < rows and 0 <= c < cols):
            return False, f"SMOOTH_OUT_OF_BOUNDS: resampled pt {i} ({r_f:.1f}, {c_f:.1f})"

        if cost_map[r, c] >= obstacle_threshold:
            return False, f"SMOOTH_CROSSES_OBSTACLE: resampled pt {i} ({r}, {c}) cost={cost_map[r, c]}"

        if slope_map is not None and slope_map[r, c] > max_slope_limit:
            return False, f"SMOOTH_CROSSES_HAZARD_SLOPE: resampled pt {i} ({r}, {c}) slope={slope_map[r, c]:.1f}°"

    return True, None


def evaluate_full_path(
    path: Optional[List[Tuple[int, int]]],
    start: Tuple[int, int],
    goal: Tuple[int, int],
    cost_map: np.ndarray,
    slope_map: np.ndarray,
    roughness_map: np.ndarray,
    psr_mask: np.ndarray,
    pixel_size_m: float = 5.0,
    obstacle_threshold: float = 1e5,
    max_slope_limit: float = 15.0,
    prevent_corner_cutting: bool = True,
    rover_spec: Optional[Dict[str, float]] = None,
    rdp_epsilon: float = 1.5,
) -> Dict[str, Any]:
    """
    Comprehensive evaluation pipeline for a planned path.

    Returns dictionary containing validation status, terrain metrics,
    energy telemetry, and smoothing evaluation.
    """
    if path is None or len(path) == 0:
        return {
            "path_valid": False,
            "path_validation_error": "NO_PATH_RETURNED",
            "path_edge_count": None,
            "path_distance_m": None,
            "terrain_cost": None,
            "max_slope_deg": None,
            "mean_slope_deg": None,
            "mean_roughness": None,
            "psr_fraction": None,
            "mission_duration_hours": None,
            "energy_consumed_wh": None,
            "solar_generated_wh": None,
            "min_battery_soc": None,
            "final_battery_soc": None,
            "recharge_stops": None,
            "battery_safe": None,
            "smooth_path": None,
            "smooth_valid": None,
            "smooth_validation_error": None,
        }

    is_valid, val_err = validate_path(
        path,
        start,
        goal,
        cost_map,
        slope_map=slope_map,
        obstacle_threshold=obstacle_threshold,
        max_slope_limit=max_slope_limit,
        prevent_corner_cutting=prevent_corner_cutting,
    )

    # Recalculate metrics
    steps = len(path) - 1
    total_dist_m = 0.0
    accumulated_cost = 0.0

    path_slopes = []
    path_roughness = []
    path_psr = []

    for i in range(len(path)):
        r, c = path[i]
        path_slopes.append(float(slope_map[r, c]))
        path_roughness.append(float(roughness_map[r, c]))
        path_psr.append(int(psr_mask[r, c]))

        if i > 0:
            pr, pc = path[i - 1]
            dr = abs(r - pr)
            dc = abs(c - pc)
            is_diag = (dr == 1 and dc == 1)
            dist_mult = SQRT2 if is_diag else 1.0

            total_dist_m += dist_mult * pixel_size_m
            target_cost = float(cost_map[r, c])
            accumulated_cost += target_cost * dist_mult

    max_slope = float(np.max(path_slopes)) if path_slopes else 0.0
    mean_slope = float(np.mean(path_slopes)) if path_slopes else 0.0
    mean_roughness = float(np.mean(path_roughness)) if path_roughness else 0.0
    psr_fraction = float(np.mean(path_psr)) if path_psr else 0.0

    # Smooth path & validate smoothing
    smooth_path = smooth_path_rdp(path, epsilon=rdp_epsilon)
    smooth_valid, smooth_err = validate_smoothed_path(
        smooth_path,
        cost_map,
        slope_map=slope_map,
        obstacle_threshold=obstacle_threshold,
        max_slope_limit=max_slope_limit,
    )

    # Energy model simulation
    spec = {**DEFAULT_ROVER_SPEC, **(rover_spec or {})}
    energy_res = compute_energy_profile(
        path,
        slope_map,
        psr_mask,
        pixel_size_m=pixel_size_m,
        rover_spec=spec,
    )

    telemetry = energy_res["telemetry"]
    recharge_stops = sum(1 for t in telemetry if t["status"] == "RECHARGE_STOP")

    # Detailed Wh integration
    total_drive_wh = 0.0
    total_solar_wh = 0.0
    speed = float(spec["speed_m_per_s"])
    solar_peak = float(spec["solar_panel_w"])
    recharge_dur = float(spec["recharge_duration_hours"])

    for i, t in enumerate(telemetry):
        if i > 0:
            pr, pc = path[i - 1]
            r, c = path[i]
            seg_m = np.hypot(r - pr, c - pc) * pixel_size_m
            step_hours = (seg_m / speed) / 3600.0 if speed > 0 else 0.0
            total_drive_wh += t["drive_w"] * step_hours
            total_solar_wh += t["solar_in_w"] * step_hours

        if t["status"] == "RECHARGE_STOP":
            total_solar_wh += solar_peak * recharge_dur

    final_soc = telemetry[-1]["battery_pct"] if telemetry else 100.0
    min_soc = energy_res["min_battery_pct"]
    battery_safe = bool(min_soc >= spec["recharge_threshold_pct"] and not any(t["status"] == "CRITICAL_LOW_POWER" for t in telemetry))

    return {
        "path_valid": is_valid,
        "path_validation_error": val_err,
        "path_edge_count": steps,
        "path_distance_m": round(total_dist_m, 3),
        "terrain_cost": round(accumulated_cost, 3),
        "max_slope_deg": round(max_slope, 2),
        "mean_slope_deg": round(mean_slope, 2),
        "mean_roughness": round(mean_roughness, 4),
        "psr_fraction": round(psr_fraction, 4),
        "mission_duration_hours": energy_res["total_time_hours"],
        "energy_consumed_wh": round(total_drive_wh, 2),
        "solar_generated_wh": round(total_solar_wh, 2),
        "min_battery_soc": min_soc,
        "final_battery_soc": final_soc,
        "recharge_stops": recharge_stops,
        "battery_safe": battery_safe,
        "smooth_path": smooth_path,
        "smooth_valid": smooth_valid,
        "smooth_validation_error": smooth_err,
    }
