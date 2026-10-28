"""
Weighted A* Pathfinding on 2D Traversal Cost Grids
=================================================
Optimized graph search for planetary rover navigation using an admissible
or weighted Euclidean distance heuristic over an 8-connected grid.

NOTE ON OPTIMALITY:
When w = 1.0, A* finds a cost-optimal path (equivalent to Dijkstra with pruning).
When w > 1.0, Weighted A* trades strict cost-optimality for substantial speedups
in search convergence and node expansion efficiency.
"""

import time
import math
import heapq
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

from .search_common import (
    SearchResult,
    validate_endpoints,
    get_valid_neighbors,
    reconstruct_path,
    compute_path_metrics,
)


def astar_search(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    w: float = 1.5,
    obstacle_threshold: float = 1e5,
    prevent_corner_cutting: bool = True,
    pixel_size_m: float = 5.0,
) -> SearchResult:
    """
    Executes Weighted A* search from start to goal.

    Parameters:
    -----------
    cost_map : np.ndarray (2D float)
        Traversal cost surface.
    start : (row, col)
        Origin coordinates.
    goal : (row, col)
        Target destination coordinates.
    w : float
        Heuristic weight (w=1.0 is admissible/optimal, w>1.0 speeds up search).
    obstacle_threshold : float
        Cells with cost >= threshold are impassable obstacles.
    prevent_corner_cutting : bool
        If True, rejects diagonal steps where either adjacent orthogonal cell is impassable.
    pixel_size_m : float
        Grid cell resolution in metres for distance metric.

    Returns:
    --------
    SearchResult containing path, metrics, and diagnostics.
    """
    t0 = time.perf_counter()

    params: Dict[str, Any] = {
        "w": float(w),
        "prevent_corner_cutting": prevent_corner_cutting,
    }

    is_valid, fail_reason, s, g = validate_endpoints(
        cost_map, start, goal, obstacle_threshold=obstacle_threshold
    )
    if not is_valid:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="Weighted A*",
            success=False,
            failure_reason=fail_reason,
            execution_time_ms=round(t_ms, 3),
            parameters=params,
        )

    # Edge case: start == goal
    if s == g:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="Weighted A*",
            success=True,
            path=[s],
            path_length_steps=0,
            path_distance_m=0.0,
            terrain_cost=0.0,
            execution_time_ms=round(t_ms, 3),
            expanded_nodes=0,
            generated_nodes=1,
            peak_frontier_size=1,
            parameters=params,
        )

    passable_costs = cost_map[cost_map < obstacle_threshold]
    min_cost = float(passable_costs.min()) if passable_costs.size > 0 else 1.0

    def heuristic(pos: Tuple[int, int]) -> float:
        dr = pos[0] - g[0]
        dc = pos[1] - g[1]
        return w * min_cost * math.hypot(dr, dc)

    tie_breaker = 0
    # (f_score, g_score, tie_breaker, (row, col))
    open_heap: List[Tuple[float, float, int, Tuple[int, int]]] = [
        (heuristic(s), 0.0, tie_breaker, s)
    ]
    g_score: Dict[Tuple[int, int], float] = {s: 0.0}
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    closed = set()

    expanded_nodes = 0
    generated_nodes = 1
    peak_frontier_size = 1
    goal_found = False

    while open_heap:
        peak_frontier_size = max(peak_frontier_size, len(open_heap))
        f, g_val, _, curr = heapq.heappop(open_heap)

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

            tentative_g = g_val + step_cost
            if n_coord not in g_score or tentative_g < g_score[n_coord]:
                g_score[n_coord] = tentative_g
                came_from[n_coord] = curr
                f_new = tentative_g + heuristic(n_coord)
                tie_breaker += 1
                heapq.heappush(open_heap, (f_new, tentative_g, tie_breaker, n_coord))
                generated_nodes += 1

    t_ms = (time.perf_counter() - t0) * 1000.0

    if not goal_found:
        return SearchResult(
            algorithm="Weighted A*",
            success=False,
            failure_reason="UNREACHABLE_GOAL",
            execution_time_ms=round(t_ms, 3),
            expanded_nodes=expanded_nodes,
            generated_nodes=generated_nodes,
            peak_frontier_size=peak_frontier_size,
            parameters=params,
        )

    path = reconstruct_path(came_from, s, g)
    steps, dist_m, cost = compute_path_metrics(path, cost_map, pixel_size_m=pixel_size_m)

    return SearchResult(
        algorithm="Weighted A*",
        success=True,
        path=path,
        path_length_steps=steps,
        path_distance_m=dist_m,
        terrain_cost=cost,
        execution_time_ms=round(t_ms, 3),
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        peak_frontier_size=peak_frontier_size,
        parameters=params,
    )


def weighted_astar(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    w: float = 1.5,
    obstacle_threshold: float = 1e5,
    auto_relocate: bool = True,
    prevent_corner_cutting: bool = True,
) -> Optional[List[Tuple[int, int]]]:
    """
    Backwards-compatible public interface returning Optional[List[Tuple[int, int]]].
    Preserves exact existing behavior for cli_demo.py and api/server.py.
    """
    rows, cols = cost_map.shape
    s = (int(start[0]), int(start[1]))
    g = (int(goal[0]), int(goal[1]))

    # Bounds check
    if not (0 <= s[0] < rows and 0 <= s[1] < cols):
        raise ValueError(f"Start coordinate {s} is out of map bounds ({rows}, {cols})")
    if not (0 <= g[0] < rows and 0 <= g[1] < cols):
        raise ValueError(f"Goal coordinate {g} is out of map bounds ({rows}, {cols})")

    # If start or goal is blocked, optionally relocate to nearest passable (UI behavior)
    if auto_relocate:
        def find_nearest_passable(pt: Tuple[int, int]) -> Tuple[int, int]:
            if cost_map[pt[0], pt[1]] < obstacle_threshold:
                return pt
            for radius in range(1, 20):
                for dr in range(-radius, radius + 1):
                    for dc in range(-radius, radius + 1):
                        nr, nc = pt[0] + dr, pt[1] + dc
                        if 0 <= nr < rows and 0 <= nc < cols and cost_map[nr, nc] < obstacle_threshold:
                            return (nr, nc)
            return pt

        s = find_nearest_passable(s)
        g = find_nearest_passable(g)

    result = astar_search(
        cost_map,
        s,
        g,
        w=w,
        obstacle_threshold=obstacle_threshold,
        prevent_corner_cutting=prevent_corner_cutting,
    )
    return result.path if result.success else None
