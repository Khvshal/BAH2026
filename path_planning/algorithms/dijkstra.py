"""
Dijkstra's Algorithm for 8-Connected Planetary Grid Navigation
=============================================================
Performs uniform-cost search over the 2D grid using a min-heap priority queue.

NOTE ON OPTIMALITY:
For non-negative edge costs, Dijkstra guarantees finding the strictly
minimum-cost path under the given graph and cost formulation. It serves as
the definitive cost-optimal ground truth reference baseline.
"""

import time
import heapq
from typing import Tuple, Optional, Dict, Any, List
import numpy as np

from .search_common import (
    SearchResult,
    validate_endpoints,
    get_valid_neighbors,
    reconstruct_path,
    compute_path_metrics,
)


def dijkstra_search(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    obstacle_threshold: float = 1e5,
    prevent_corner_cutting: bool = True,
    pixel_size_m: float = 5.0,
) -> SearchResult:
    """
    Executes Dijkstra's uniform-cost search from start to goal.

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
    SearchResult containing cost-optimal path, metrics, and diagnostics.
    """
    t0 = time.perf_counter()

    is_valid, fail_reason, s, g = validate_endpoints(
        cost_map, start, goal, obstacle_threshold=obstacle_threshold
    )
    if not is_valid:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="Dijkstra",
            success=False,
            failure_reason=fail_reason,
            execution_time_ms=round(t_ms, 3),
            parameters={"prevent_corner_cutting": prevent_corner_cutting},
        )

    # Edge case: start == goal
    if s == g:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="Dijkstra",
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

    # Priority queue stores (cost_g, tie_breaker, (row, col))
    tie_breaker = 0
    open_heap: List[Tuple[float, int, Tuple[int, int]]] = [(0.0, tie_breaker, s)]
    g_score: Dict[Tuple[int, int], float] = {s: 0.0}
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    closed = set()

    expanded_nodes = 0
    generated_nodes = 1
    peak_frontier_size = 1
    goal_found = False

    while open_heap:
        peak_frontier_size = max(peak_frontier_size, len(open_heap))
        cost_g, _, curr = heapq.heappop(open_heap)

        if curr in closed:
            continue
        closed.add(curr)
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

        for n_coord, step_cost, _ in neighbors:
            if n_coord in closed:
                continue

            tentative_g = cost_g + step_cost
            if n_coord not in g_score or tentative_g < g_score[n_coord]:
                g_score[n_coord] = tentative_g
                came_from[n_coord] = curr
                tie_breaker += 1
                heapq.heappush(open_heap, (tentative_g, tie_breaker, n_coord))
                generated_nodes += 1

    t_ms = (time.perf_counter() - t0) * 1000.0

    if not goal_found:
        return SearchResult(
            algorithm="Dijkstra",
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
        algorithm="Dijkstra",
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
