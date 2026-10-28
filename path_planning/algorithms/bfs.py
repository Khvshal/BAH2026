"""
Breadth-First Search (BFS) for 8-Connected Planetary Grid Navigation
====================================================================
Performs unweighted graph search over the 2D grid using a FIFO queue.

NOTE ON OPTIMALITY:
BFS guarantees finding a path with the minimum number of GRAPH EDGES
(hop count) on an unweighted graph. It does NOT optimize physical metric
distance (since diagonal steps have length sqrt(2)) nor does it optimize
terrain-weighted cost.
"""

import time
from collections import deque
from typing import Tuple, Optional, Dict, Any
import numpy as np

from .search_common import (
    SearchResult,
    validate_endpoints,
    get_valid_neighbors,
    reconstruct_path,
    compute_path_metrics,
)


def bfs_search(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    obstacle_threshold: float = 1e5,
    prevent_corner_cutting: bool = True,
    pixel_size_m: float = 5.0,
) -> SearchResult:
    """
    Executes Breadth-First Search from start to goal.

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
            algorithm="BFS",
            success=False,
            failure_reason=fail_reason,
            execution_time_ms=round(t_ms, 3),
            parameters={"prevent_corner_cutting": prevent_corner_cutting},
        )

    # Edge case: start == goal
    if s == g:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="BFS",
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

    queue = deque([s])
    visited = {s}
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}

    expanded_nodes = 0
    generated_nodes = 1
    peak_frontier_size = 1
    goal_found = False

    while queue:
        peak_frontier_size = max(peak_frontier_size, len(queue))
        curr = queue.popleft()
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

        for n_coord, _, _ in neighbors:
            if n_coord not in visited:
                visited.add(n_coord)
                came_from[n_coord] = curr
                queue.append(n_coord)
                generated_nodes += 1

                # Early goal check optimization
                if n_coord == g:
                    goal_found = True
                    break

        if goal_found:
            break

    t_ms = (time.perf_counter() - t0) * 1000.0

    if not goal_found:
        return SearchResult(
            algorithm="BFS",
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
        algorithm="BFS",
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
