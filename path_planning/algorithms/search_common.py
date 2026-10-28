"""
Shared Interfaces, Data Models, and Movement Kinematics for Path Planning
========================================================================
Defines the standard SearchResult schema, 8-connected neighbor expansion,
strict diagonal corner-cutting prevention, and path metric calculations.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict, Any
import math
import numpy as np


SQRT2 = math.sqrt(2.0)

# Deterministic 8-connected neighbor sequence:
# (dr, dc, distance_multiplier, name)
NEIGHBOR_OFFSETS_8: List[Tuple[int, int, float, str]] = [
    (-1, 0, 1.0, "N"),
    (1, 0, 1.0, "S"),
    (0, -1, 1.0, "W"),
    (0, 1, 1.0, "E"),
    (-1, -1, SQRT2, "NW"),
    (-1, 1, SQRT2, "NE"),
    (1, -1, SQRT2, "SW"),
    (1, 1, SQRT2, "SE"),
]


@dataclass
class SearchResult:
    """Standardized result structure for all search algorithms."""
    algorithm: str
    success: bool
    path: Optional[List[Tuple[int, int]]] = None
    path_length_steps: Optional[int] = None
    path_distance_m: Optional[float] = None
    terrain_cost: Optional[float] = None
    execution_time_ms: float = 0.0
    expanded_nodes: int = 0
    generated_nodes: int = 0
    peak_frontier_size: int = 0
    failure_reason: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a plain dictionary for JSON/CSV serialization."""
        data = asdict(self)
        return data


def validate_endpoints(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    obstacle_threshold: float = 1e5,
) -> Tuple[bool, Optional[str], Tuple[int, int], Tuple[int, int]]:
    """
    Validates start and goal coordinates against map bounds and obstacles.

    Returns:
    --------
    (is_valid, failure_reason, clean_start, clean_goal)
    """
    rows, cols = cost_map.shape
    try:
        s = (int(start[0]), int(start[1]))
        g = (int(goal[0]), int(goal[1]))
    except (TypeError, ValueError, IndexError):
        return False, "INVALID_COORDINATES", (0, 0), (0, 0)

    # In-bounds check
    if not (0 <= s[0] < rows and 0 <= s[1] < cols):
        return False, f"INVALID_COORDINATES: start {s} out of bounds ({rows}, {cols})", s, g
    if not (0 <= g[0] < rows and 0 <= g[1] < cols):
        return False, f"INVALID_COORDINATES: goal {g} out of bounds ({rows}, {cols})", s, g

    # Obstacle check
    if cost_map[s[0], s[1]] >= obstacle_threshold:
        return False, f"BLOCKED_START: start {s} cost {cost_map[s[0], s[1]]} >= {obstacle_threshold}", s, g
    if cost_map[g[0], g[1]] >= obstacle_threshold:
        return False, f"BLOCKED_GOAL: goal {g} cost {cost_map[g[0], g[1]]} >= {obstacle_threshold}", s, g

    return True, None, s, g


def get_valid_neighbors(
    node: Tuple[int, int],
    cost_map: np.ndarray,
    obstacle_threshold: float = 1e5,
    prevent_corner_cutting: bool = True,
) -> List[Tuple[Tuple[int, int], float, float]]:
    """
    Generates legal 8-connected neighbors from current node.

    Diagonal corner-cutting rule:
    For a diagonal move from (r, c) to (r+dr, c+dc), both adjacent orthogonal
    cells (r+dr, c) and (r, c+dc) must be within bounds and traversable.

    Returns:
    --------
    List of ((nr, nc), step_cost, dist_mult)
    """
    rows, cols = cost_map.shape
    r, c = node
    valid = []

    for dr, dc, dist_mult, _ in NEIGHBOR_OFFSETS_8:
        nr, nc = r + dr, c + dc

        # Bounds check
        if not (0 <= nr < rows and 0 <= nc < cols):
            continue

        # Obstacle check on target cell
        target_cost = cost_map[nr, nc]
        if target_cost >= obstacle_threshold:
            continue

        # Prevent diagonal corner-cutting
        if prevent_corner_cutting and dr != 0 and dc != 0:
            ortho1_r, ortho1_c = r + dr, c
            ortho2_r, ortho2_c = r, c + dc

            # If either adjacent orthogonal cell is out of bounds or impassable, reject diagonal
            if not (0 <= ortho1_r < rows and 0 <= ortho1_c < cols) or \
               not (0 <= ortho2_r < rows and 0 <= ortho2_c < cols):
                continue

            if cost_map[ortho1_r, ortho1_c] >= obstacle_threshold or \
               cost_map[ortho2_r, ortho2_c] >= obstacle_threshold:
                continue

        step_cost = float(target_cost) * dist_mult
        valid.append(((nr, nc), step_cost, dist_mult))

    return valid


def reconstruct_path(
    came_from: Dict[Tuple[int, int], Tuple[int, int]],
    start: Tuple[int, int],
    goal: Tuple[int, int],
) -> List[Tuple[int, int]]:
    """Reconstructs the node sequence from goal back to start."""
    if start == goal:
        return [start]
    if goal not in came_from:
        return []

    path = []
    curr = goal
    visited_in_path = set()
    while curr != start:
        if curr in visited_in_path or curr not in came_from:
            return []
        visited_in_path.add(curr)
        path.append(curr)
        curr = came_from[curr]
    path.append(start)
    path.reverse()
    return path



def compute_path_metrics(
    path: Optional[List[Tuple[int, int]]],
    cost_map: np.ndarray,
    pixel_size_m: float = 5.0,
) -> Tuple[int, float, float]:
    """
    Calculates step count (edges), physical distance in metres, and terrain cost.

    Returns:
    --------
    (path_length_steps, path_distance_m, terrain_cost)
    """
    if not path or len(path) <= 1:
        return 0, 0.0, 0.0

    steps = len(path) - 1
    total_dist_m = 0.0
    total_cost = 0.0

    for i in range(steps):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]

        dr = abs(r2 - r1)
        dc = abs(c2 - c1)
        is_diag = (dr == 1 and dc == 1)
        dist_mult = SQRT2 if is_diag else 1.0

        total_dist_m += dist_mult * pixel_size_m
        target_cost = float(cost_map[r2, c2])
        total_cost += target_cost * dist_mult

    return steps, round(total_dist_m, 3), round(total_cost, 3)
