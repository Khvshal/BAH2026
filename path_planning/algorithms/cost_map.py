"""
Cost Map Generation for Lunar Rover Traversals
Combines terrain slope, roughness, and illumination into a traversability cost surface.
"""

import numpy as np


def build_cost_map(
    slope_map: np.ndarray,
    roughness_map: np.ndarray,
    psr_mask: np.ndarray,
    pixel_size_m: float = 5.0,
    max_slope_limit: float = 15.0,
    warning_slope: float = 10.0,
    slope_weight: float = 8.0,
    roughness_weight: float = 10.0,
    shadow_penalty: float = 5.0,
    sun_bonus: float = -1.0,
) -> np.ndarray:
    """
    Computes a per-pixel traversal cost map for a lunar rover.

    Parameters:
    -----------
    slope_map : np.ndarray (2D float)
        Terrain inclination in degrees.
    roughness_map : np.ndarray (2D float)
        Surface RMS roughness or obstacle metric (normalized 0..1).
    psr_mask : np.ndarray (2D int/bool)
        1 for Permanently Shadowed Regions (PSR), 0 for illuminated terrain.
    pixel_size_m : float
        Grid resolution in metres (default 5.0m).
    max_slope_limit : float
        Strict physical incline limit for rover rollover hazard (degrees).
    warning_slope : float
        Slope above which an extra steepness penalty applies.
    slope_weight : float
        Weight scalar for inclination power draw.
    roughness_weight : float
        Weight scalar for surface friction and rock avoidance.
    shadow_penalty : float
        Cost penalty for traveling inside dark cold-traps.
    sun_bonus : float
        Cost adjustment for illuminated areas (negative acts as a reward).

    Returns:
    --------
    np.ndarray (2D float): Traversal cost map where >= 1e5 indicates impassable obstacles.
    """
    # Base energy cost proportional to uphill/incline mechanical resistance
    energy_cost = 1.0 + slope_weight * np.sin(np.radians(np.clip(slope_map, 0.0, 90.0)))

    # Safety penalty: hard barriers and soft friction
    safety_penalty = np.zeros_like(slope_map, dtype=np.float64)

    # Impassable slopes (rollover risk)
    safety_penalty[slope_map > max_slope_limit] = 1e6

    # Moderate slope caution zone
    caution_mask = (slope_map > warning_slope) & (slope_map <= max_slope_limit)
    safety_penalty[caution_mask] += 50.0

    # Surface roughness / boulder friction
    safety_penalty += roughness_map * roughness_weight

    # Solar illumination preference
    solar_cost = np.where(psr_mask == 1, shadow_penalty, sun_bonus)

    # Combined composite cost
    cost_map = energy_cost + safety_penalty + solar_cost
    cost_map = np.clip(cost_map, 1.0, 1e6)

    return cost_map
