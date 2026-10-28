"""
Depth-First Search (DFS) for 8-Connected Planetary Grid Navigation
==================================================================
Performs uninformed depth-first graph search over the 2D grid using
an iterative LIFO stack to eliminate Python recursion limit constraints.

NOTE ON OPTIMALITY:
DFS does NOT guarantee a shortest path, minimal hop count, or minimal
terrain cost. On 2D spatial grids, DFS frequently produces deep, winding,
circuitous routes with high terrain cost. It serves as an unguided baseline.
"""

import time
from typing import Tuple, Optional, Dict, Any, List
import numpy as np

from .search_common import (
    SearchResult,
    validate_endpoints,
    get_valid_neighbors,
    reconstruct_path,
    compute_path_metrics,
)


def dfs_search(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    obstacle_threshold: float = 1e5,
    prevent_corner_cutting: bool = True,
    pixel_size_m: float = 5.0,
) -> SearchResult:
    """
    Executes iterative Depth-First Search from start to goal.

    Parameters:
    -----------
    cost_map : np.ndarray (2D float)
        Traversal cost surface.
    start : (row, col)
        Origin coordinates.
    goal : (row, col)
        Target destination coordinates.
    obstacle_threshold : float
        Cells with cost >= threshold are impassable obstacles.
    prevent_corner_cutting : bool
        If True, rejects diagonal steps where either adjacent orthogonal cell is impassable.
    pixel_size_m : float
        Grid cell resolution in metres for distance metric.

    Returns:
    --------
    SearchResult containing the path, metrics, and execution diagnostics.
    """
    t0 = time.perf_counter()

    is_valid, fail_reason, s, g = validate_endpoints(
        cost_map, start, goal, obstacle_threshold=obstacle_threshold
    )
    if not is_valid:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="DFS",
            success=False,
            failure_reason=fail_reason,
            execution_time_ms=round(t_ms, 3),
            parameters={"prevent_corner_cutting": prevent_corner_cutting},
        )

    # Edge case: start == goal
    if s == g:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="DFS",
            success=True,
            path=[s],
            path_length_steps=0,
            path_distance_m=0.0,
            terrain_cost=0.0,
            execution_time_ms=round(t_ms, 3),
            expanded_nodes=0,
            generated_nodes=1,
            peak_frontier_size=1,
            parameters={"prevent_corner_cutting": prevent_corner_cutting},
        )

    # Stack holds (current_node, parent_node)
    stack: List[Tuple[Tuple[int, int], Optional[Tuple[int, int]]]] = [(s, None)]
    visited = set()
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}

    expanded_nodes = 0
    generated_nodes = 1
    peak_frontier_size = 1
    goal_found = False

    while stack:
        peak_frontier_size = max(peak_frontier_size, len(stack))
        curr, parent = stack.pop()

        if curr in visited:
            continue

        visited.add(curr)
        if parent is not None:
            came_from[curr] = parent

        expanded_nodes += 1

        if curr == g:
            goal_found = True
            break

        neighbors = get_valid_neighbors(
            curr,
            cost_map,
            obstacle_threshold=obstacle_threshold,
            prevent_corner_cutting=prevent_corner_cutting,
        )

        # Push in reversed order so first neighbor in NEIGHBOR_OFFSETS_8 is popped first
        for n_coord, _, _ in reversed(neighbors):
            if n_coord not in visited:
                stack.append((n_coord, curr))
                generated_nodes += 1

    t_ms = (time.perf_counter() - t0) * 1000.0

    if not goal_found:
        return SearchResult(
            algorithm="DFS",
            success=False,
            failure_reason="UNREACHABLE_GOAL",
            execution_time_ms=round(t_ms, 3),
            expanded_nodes=expanded_nodes,
            generated_nodes=generated_nodes,
            peak_frontier_size=peak_frontier_size,
            parameters={"prevent_corner_cutting": prevent_corner_cutting},
        )

    path = reconstruct_path(came_from, s, g)
    steps, dist_m, cost = compute_path_metrics(path, cost_map, pixel_size_m=pixel_size_m)

    return SearchResult(
        algorithm="DFS",
        success=True,
        path=path,
        path_length_steps=steps,
        path_distance_m=dist_m,
        terrain_cost=cost,
        execution_time_ms=round(t_ms, 3),
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        peak_frontier_size=peak_frontier_size,
        parameters={"prevent_corner_cutting": prevent_corner_cutting},
    )
