"""
Lunar Rover Energy and Telemetry Simulation
==========================================
Simulates power generation, mechanical locomotion draw, battery State-of-Charge (SoC),
and autonomous recharge stops along a traversed lunar path.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np


DEFAULT_ROVER_SPEC = {
    "battery_wh": 500.0,         # Total battery capacity in Watt-hours
    "solar_panel_w": 150.0,      # Peak solar panel generation in full sunlight
    "drive_power_w": 100.0,      # Baseline flat-ground locomotion power
    "speed_m_per_s": 0.1,        # Nominal rover velocity (10 cm/s)
    "recharge_threshold_pct": 20.0,  # Battery % trigger for emergency solar recharge stop
    "recharge_duration_hours": 0.5,  # Time spent recharging when stopped
}


def compute_energy_profile(
    path: List[Tuple[float, float]],
    slope_map: np.ndarray,
    psr_mask: np.ndarray,
    pixel_size_m: float = 5.0,
    rover_spec: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Computes step-by-step energy profile and telemetry along a planned path.

    Parameters:
    -----------
    path : List of (row, col)
        Waypoints or resampled steps along the traverse.
    slope_map : np.ndarray (2D float)
        Terrain slope in degrees.
    psr_mask : np.ndarray (2D int/bool)
        1 for shadow, 0 for sunlight.
    pixel_size_m : float
        Resolution of each grid cell in metres.
    rover_spec : dict, optional
        Rover hardware parameters.

    Returns:
    --------
    dict containing:
        - telemetry: List of per-waypoint metrics (battery_pct, drive_w, solar_in_w, status, etc.)
        - total_distance_m: Total physical traverse length
        - total_time_hours: Total mission elapsed time including recharge halts
        - min_battery_pct: Lowest battery level reached
        - max_slope_deg: Steepest slope encountered
    """
    spec = {**DEFAULT_ROVER_SPEC, **(rover_spec or {})}

    max_battery = float(spec["battery_wh"])
    battery = max_battery
    solar_peak = float(spec["solar_panel_w"])
    base_drive = float(spec["drive_power_w"])
    speed = float(spec["speed_m_per_s"])
    recharge_thresh = float(spec["recharge_threshold_pct"])
    recharge_duration = float(spec["recharge_duration_hours"])

    rows, cols = slope_map.shape
    telemetry = []

    cumulative_distance = 0.0
    cumulative_time_hours = 0.0
    max_slope_deg = 0.0
    min_battery_pct = 100.0

    for i, (r_raw, c_raw) in enumerate(path):
        r = min(max(0, int(round(r_raw))), rows - 1)
        c = min(max(0, int(round(c_raw))), cols - 1)

        slope = float(slope_map[r, c])
        max_slope_deg = max(max_slope_deg, slope)

        # Drive power draw: increases on positive incline
        drive_watts = base_drive + base_drive * 2.0 * np.sin(np.radians(max(0.0, slope)))

        # Solar power: 0 inside PSR (shadow), peak solar when illuminated
        is_sunlit = 1.0 - float(psr_mask[r, c])
        solar_in = solar_peak * is_sunlit

        # Segment distance calculation
        if i == 0:
            seg_dist = 0.0
        else:
            prev_r, prev_c = path[i - 1]
            seg_dist = np.hypot(r_raw - prev_r, c_raw - prev_c) * pixel_size_m

        cumulative_distance += seg_dist
        step_drive_time_hours = (seg_dist / speed) / 3600.0 if speed > 0 else 0.0

        # Energy delta while driving
        net_power = solar_in - drive_watts  # Watts
        battery += net_power * step_drive_time_hours
        battery = np.clip(battery, 0.0, max_battery)
        cumulative_time_hours += step_drive_time_hours

        battery_pct = (battery / max_battery) * 100.0
        min_battery_pct = min(min_battery_pct, battery_pct)

        status = "DRIVING"

        # Check if battery triggers recharge stop (only effective if in sunlight)
        if battery_pct < recharge_thresh:
            if is_sunlit > 0.5:
                status = "RECHARGE_STOP"
                # Solar recharging while stationary
                recharge_energy = solar_peak * recharge_duration
                battery = min(max_battery, battery + recharge_energy)
                cumulative_time_hours += recharge_duration
                battery_pct = (battery / max_battery) * 100.0
            else:
                status = "CRITICAL_LOW_POWER"

        telemetry.append({
            "step": i,
            "grid_r": r,
            "grid_c": c,
            "slope_deg": round(slope, 2),
            "status": status,
            "is_sunlit": bool(is_sunlit > 0.5),
            "battery_pct": round(float(battery_pct), 2),
            "solar_in_w": round(float(solar_in), 2),
            "drive_w": round(float(drive_watts), 2),
            "net_w": round(float(net_power), 2),
            "distance_m": round(float(cumulative_distance), 2),
            "elapsed_hours": round(float(cumulative_time_hours), 2),
        })

    return {
        "telemetry": telemetry,
        "total_distance_m": round(float(cumulative_distance), 2),
        "total_time_hours": round(float(cumulative_time_hours), 2),
        "min_battery_pct": round(float(min_battery_pct), 2),
        "max_slope_deg": round(float(max_slope_deg), 2),
    }
