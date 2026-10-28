"""
Depth-Limited Search (DLS) for 8-Connected Planetary Grid Navigation
====================================================================
Performs iterative depth-limited depth-first search over the 2D grid.

TERMINATION SEMANTICS:
- Goal found: Returns path with success=True.
- Depth limit reached: Returns success=False, failure_reason="DEPTH_LIMIT_EXCEEDED".
  (Explicitly indicates search was cut off by depth constraint, NOT that no path exists).
- Space exhausted: Returns success=False, failure_reason="EXHAUSTED_NO_SOLUTION".
  (Search completed within the depth limit and proved goal is unreachable in that radius).
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


def dls_search(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    depth_limit: int,
    obstacle_threshold: float = 1e5,
    prevent_corner_cutting: bool = True,
    pixel_size_m: float = 5.0,
    max_expansions: int = 250000,
) -> SearchResult:
    """
    Executes iterative Depth-Limited Search from start to goal up to depth_limit.

    Parameters:
    -----------
    cost_map : np.ndarray (2D float)
        Traversal cost surface.
    start : (row, col)
        Origin coordinates.
    goal : (row, col)
        Target destination coordinates.
    depth_limit : int
        Maximum search depth (number of edges from start).
    obstacle_threshold : float
        Cells with cost >= threshold are impassable obstacles.
    prevent_corner_cutting : bool
        If True, rejects diagonal steps where either adjacent orthogonal cell is impassable.
    pixel_size_m : float
        Grid cell resolution in metres for distance metric.
    max_expansions : int
        Safety threshold to prevent pathological combinatorial explosion.

    Returns:
    --------
    SearchResult containing path, metrics, depth_limit, and termination diagnostics.
    """
    t0 = time.perf_counter()

    params: Dict[str, Any] = {
        "depth_limit": depth_limit,
        "prevent_corner_cutting": prevent_corner_cutting,
        "max_expansions": max_expansions,
    }


    if depth_limit < 0:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="DLS",
            success=False,
            failure_reason=f"INVALID_DEPTH_LIMIT: depth_limit ({depth_limit}) must be >= 0",
            execution_time_ms=round(t_ms, 3),
            parameters=params,
        )

    is_valid, fail_reason, s, g = validate_endpoints(
        cost_map, start, goal, obstacle_threshold=obstacle_threshold
    )
    if not is_valid:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="DLS",
            success=False,
            failure_reason=fail_reason,
            execution_time_ms=round(t_ms, 3),
            parameters=params,
        )

    # Edge case: start == goal
    if s == g:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="DLS",
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

    # Edge case: depth_limit == 0 and start != goal
    if depth_limit == 0:
        t_ms = (time.perf_counter() - t0) * 1000.0
        return SearchResult(
            algorithm="DLS",
            success=False,
            failure_reason="DEPTH_LIMIT_EXCEEDED",
            execution_time_ms=round(t_ms, 3),
            expanded_nodes=0,
            generated_nodes=1,
            peak_frontier_size=1,
            parameters=params,
        )

    # Stack holds (current_node, parent_link, current_depth)
    stack: List[Tuple[Tuple[int, int], Optional[Any], int]] = [(s, None, 0)]
    # best_depth records the shallowest depth at which a node has been queued or expanded
    best_depth: Dict[Tuple[int, int], int] = {s: 0}

    expanded_nodes = 0
    generated_nodes = 1
    peak_frontier_size = 1
    goal_found = False
    goal_link = None
    cutoff_occurred = False

    while stack:
        if expanded_nodes >= max_expansions:
            cutoff_occurred = True
            break

        peak_frontier_size = max(peak_frontier_size, len(stack))
        curr, parent_link, depth = stack.pop()


        # If a shallower path to curr was already processed, prune
        if depth > best_depth.get(curr, depth):
            continue

        expanded_nodes += 1

        if curr == g:
            goal_found = True
            goal_link = (curr, parent_link)
            break

        if depth < depth_limit:
            neighbors = get_valid_neighbors(
                curr,
                cost_map,
                obstacle_threshold=obstacle_threshold,
                prevent_corner_cutting=prevent_corner_cutting,
            )

            current_link = (curr, parent_link)
            for n_coord, _, _ in reversed(neighbors):
                next_depth = depth + 1
                if n_coord not in best_depth or next_depth < best_depth[n_coord]:
                    best_depth[n_coord] = next_depth
                    stack.append((n_coord, current_link, next_depth))
                    generated_nodes += 1
        else:
            # Depth limit reached for this node; deeper children exist but were pruned
            cutoff_occurred = True


    t_ms = (time.perf_counter() - t0) * 1000.0

    if not goal_found:
        reason = "DEPTH_LIMIT_EXCEEDED" if cutoff_occurred else "EXHAUSTED_NO_SOLUTION"
        return SearchResult(
            algorithm="DLS",
            success=False,
            failure_reason=reason,
            execution_time_ms=round(t_ms, 3),
            expanded_nodes=expanded_nodes,
            generated_nodes=generated_nodes,
            peak_frontier_size=peak_frontier_size,
            parameters=params,
        )

    # Reconstruct path from linked chain
    path = []
    p = goal_link
    while p is not None:
        path.append(p[0])
        p = p[1]
    path.reverse()

    steps, dist_m, cost = compute_path_metrics(path, cost_map, pixel_size_m=pixel_size_m)


    return SearchResult(
        algorithm="DLS",
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
