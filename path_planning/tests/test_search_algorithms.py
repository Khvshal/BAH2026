"""
Unit Tests for Lunar Rover Path Planning Search Algorithms
===========================================================
Tests all search algorithms (BFS, DFS, DLS, Dijkstra, Weighted A*),
the shared search interface, path metrics calculation, corner-cutting logic,
and independent path validator across edge cases and controlled scenarios.
"""

import math
import pytest
import numpy as np

from algorithms import (
    SearchResult,
    bfs_search,
    dfs_search,
    dls_search,
    dijkstra_search,
    astar_search,
    weighted_astar,
    build_cost_map,
)
from algorithms.search_common import (
    validate_endpoints,
    get_valid_neighbors,
    reconstruct_path,
    compute_path_metrics,
    SQRT2,
)
from experiments.evaluate_path import validate_path


# ===========================================================================
# 1. Edge Case: Start Equals Goal
# ===========================================================================
@pytest.mark.parametrize("search_func,algo_name", [
    (bfs_search, "BFS"),
    (dfs_search, "DFS"),
    (lambda cm, s, g: dls_search(cm, s, g, depth_limit=10), "DLS"),
    (dijkstra_search, "Dijkstra"),
    (astar_search, "Weighted A*"),
])
def test_start_equals_goal(search_func, algo_name):
    cost_map = np.ones((10, 10), dtype=np.float64)
    coord = (4, 4)

    res = search_func(cost_map, coord, coord)
    assert res.success is True, f"{algo_name} failed on start == goal"
    assert res.path == [coord]
    assert res.path_length_steps == 0
    assert res.path_distance_m == 0.0
    assert res.terrain_cost == 0.0


# ===========================================================================
# 2. Edge Case: Invalid Start or Goal (Out of Bounds / Negative)
# ===========================================================================
@pytest.mark.parametrize("search_func", [
    bfs_search,
    dfs_search,
    lambda cm, s, g: dls_search(cm, s, g, depth_limit=10),
    dijkstra_search,
    astar_search,
])
def test_invalid_start_or_goal(search_func):
    cost_map = np.ones((10, 10), dtype=np.float64)

    # Start out of bounds
    res1 = search_func(cost_map, (-1, 5), (5, 5))
    assert res1.success is False
    assert "INVALID_COORDINATES" in str(res1.failure_reason)

    # Goal out of bounds
    res2 = search_func(cost_map, (0, 0), (10, 10))
    assert res2.success is False
    assert "INVALID_COORDINATES" in str(res2.failure_reason)


# ===========================================================================
# 3. Edge Case: Blocked Start or Goal
# ===========================================================================
@pytest.mark.parametrize("search_func", [
    bfs_search,
    dfs_search,
    lambda cm, s, g: dls_search(cm, s, g, depth_limit=10),
    dijkstra_search,
    astar_search,
])
def test_blocked_start_or_goal(search_func):
    cost_map = np.ones((10, 10), dtype=np.float64)
    cost_map[2, 2] = 1e6  # Impassable obstacle

    # Blocked start
    res1 = search_func(cost_map, (2, 2), (5, 5))
    assert res1.success is False
    assert "BLOCKED_START" in str(res1.failure_reason)

    # Blocked goal
    res2 = search_func(cost_map, (0, 0), (2, 2))
    assert res2.success is False
    assert "BLOCKED_GOAL" in str(res2.failure_reason)


# ===========================================================================
# 4. Edge Case: Completely Unreachable Goal
# ===========================================================================
@pytest.mark.parametrize("search_func", [
    bfs_search,
    dfs_search,
    lambda cm, s, g: dls_search(cm, s, g, depth_limit=50),
    dijkstra_search,
    astar_search,
])
def test_unreachable_goal(search_func):
    # Enclose goal (5, 5) completely inside a wall of obstacles
    cost_map = np.ones((11, 11), dtype=np.float64)
    for r in range(4, 7):
        for c in range(4, 7):
            if (r, c) != (5, 5):
                cost_map[r, c] = 1e6

    res = search_func(cost_map, (0, 0), (5, 5))
    assert res.success is False
    assert res.path is None
    # For DLS it could be EXHAUSTED_NO_SOLUTION or UNREACHABLE_GOAL
    assert res.failure_reason in ("UNREACHABLE_GOAL", "EXHAUSTED_NO_SOLUTION", "DEPTH_LIMIT_EXCEEDED")


# ===========================================================================
# 5. Simple Straight Corridor
# ===========================================================================
def test_straight_corridor():
    # 1 x 5 horizontal corridor: row 1, cols 0..4
    cost_map = np.full((3, 5), 1e6, dtype=np.float64)
    cost_map[1, :] = 1.0  # Passable path

    for algo in [bfs_search, dijkstra_search, astar_search]:
        res = algo(cost_map, (1, 0), (1, 4), pixel_size_m=5.0)
        assert res.success is True
        assert res.path_length_steps == 4
        assert res.path_distance_m == 20.0  # 4 steps * 5m
        assert res.path == [(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)]


# ===========================================================================
# 6. Map With Obstacle Requiring Detouring
# ===========================================================================
def test_detour_around_wall():
    # 7 x 7 grid, vertical wall at col 3 with gap at row 0
    cost_map = np.ones((7, 7), dtype=np.float64)
    cost_map[1:, 3] = 1e6  # Wall from row 1 to 6 at col 3

    start = (3, 1)
    goal = (3, 5)

    for algo in [bfs_search, dijkstra_search, astar_search, dfs_search]:
        res = algo(cost_map, start, goal)
        assert res.success is True, f"{res.algorithm} failed to detour"
        is_valid, err = validate_path(res.path, start, goal, cost_map)
        assert is_valid is True, f"Detour path invalid for {res.algorithm}: {err}"


# ===========================================================================
# 7. Diagonal Movement & Corner-Cutting Prevention Case
# ===========================================================================
def test_corner_cutting_prevention():
    # Diagonal step from (0, 0) to (1, 1).
    # Orthogonal neighbors are (0, 1) and (1, 0).
    cost_map = np.ones((3, 3), dtype=np.float64)
    cost_map[0, 1] = 1e6  # Block one orthogonal cell

    # Test get_valid_neighbors
    neighbors_strict = get_valid_neighbors((0, 0), cost_map, prevent_corner_cutting=True)
    coords_strict = [n[0] for n in neighbors_strict]
    assert (1, 1) not in coords_strict, "Diagonal move (1, 1) should be rejected due to blocked (0, 1)"

    # With prevent_corner_cutting=False, diagonal is allowed
    neighbors_permissive = get_valid_neighbors((0, 0), cost_map, prevent_corner_cutting=False)
    coords_permissive = [n[0] for n in neighbors_permissive]
    assert (1, 1) in coords_permissive, "Diagonal move (1, 1) should be permitted when corner-cutting allowed"


# ===========================================================================
# 8. BFS Path-Edge Optimality on Unweighted Graph
# ===========================================================================
def test_bfs_edge_count_optimality():
    # Create a grid where diagonal is longer in terrain cost but fewer or equal edges
    cost_map = np.ones((5, 5), dtype=np.float64)
    res = bfs_search(cost_map, (0, 0), (4, 4))
    assert res.success is True
    # 4 diagonal steps reach (4, 4) from (0, 0) in 8-connected grid
    assert res.path_length_steps == 4
    assert res.path == [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]


# ===========================================================================
# 9. DFS Path Validity Without Assuming Shortest Path
# ===========================================================================
def test_dfs_path_validity():
    cost_map = np.ones((8, 8), dtype=np.float64)
    start = (1, 1)
    goal = (6, 6)

    res = dfs_search(cost_map, start, goal)
    assert res.success is True
    assert res.path is not None
    is_valid, err = validate_path(res.path, start, goal, cost_map)
    assert is_valid is True, f"DFS produced invalid path: {err}"
    assert res.path[0] == start
    assert res.path[-1] == goal


# ===========================================================================
# 10. DLS Success at Sufficient Depth vs Failure at Insufficient Depth
# ===========================================================================
def test_dls_depth_cutoff_behavior():
    cost_map = np.ones((10, 10), dtype=np.float64)
    start = (0, 0)
    goal = (0, 6)  # Exactly 6 steps along row 0

    # Insufficient depth limit = 4: goal is 6 steps away
    res_shallow = dls_search(cost_map, start, goal, depth_limit=4)
    assert res_shallow.success is False
    assert res_shallow.failure_reason == "DEPTH_LIMIT_EXCEEDED"
    assert res_shallow.expanded_nodes > 0

    # Sufficient depth limit = 8: goal is reached
    res_deep = dls_search(cost_map, start, goal, depth_limit=8)
    assert res_deep.success is True
    assert res_deep.path is not None
    assert res_deep.path[0] == start
    assert res_deep.path[-1] == goal


# ===========================================================================
# 11. DLS Depth Zero Behavior & Invalid Limits
# ===========================================================================
def test_dls_depth_zero_and_negative():
    cost_map = np.ones((5, 5), dtype=np.float64)

    # depth_limit = 0 with start == goal -> Success
    res1 = dls_search(cost_map, (2, 2), (2, 2), depth_limit=0)
    assert res1.success is True
    assert res1.path == [(2, 2)]

    # depth_limit = 0 with start != goal -> Cutoff
    res2 = dls_search(cost_map, (1, 1), (3, 3), depth_limit=0)
    assert res2.success is False
    assert res2.failure_reason == "DEPTH_LIMIT_EXCEEDED"

    # Negative depth limit -> Invalid
    res3 = dls_search(cost_map, (1, 1), (3, 3), depth_limit=-1)
    assert res3.success is False
    assert "INVALID_DEPTH_LIMIT" in str(res3.failure_reason)


# ===========================================================================
# 12. Path Reconstruction Correctness & Cycle Guard
# ===========================================================================
def test_path_reconstruction():
    came_from = {
        (1, 1): (0, 0),
        (2, 2): (1, 1),
        (3, 3): (2, 2),
    }
    path = reconstruct_path(came_from, (0, 0), (3, 3))
    assert path == [(0, 0), (1, 1), (2, 2), (3, 3)]

    # Cycle guard test: disconnected / cyclic came_from
    cycle_came_from = {
        (2, 2): (1, 1),
        (1, 1): (2, 2),
    }
    bad_path = reconstruct_path(cycle_came_from, (0, 0), (2, 2))
    assert bad_path == []


# ===========================================================================
# 13. Terrain Cost and Distance Calculation Correctness
# ===========================================================================
def test_path_metrics_calculation():
    # 3x3 map where diagonal step cost and orthogonal cost are known
    cost_map = np.ones((3, 3), dtype=np.float64)
    cost_map[1, 1] = 4.0

    path = [(0, 0), (1, 1), (1, 2)]
    # Step 1: (0,0)->(1,1) diagonal (cost=4.0 * sqrt(2), dist = 5.0 * sqrt(2))
    # Step 2: (1,1)->(1,2) orthogonal (cost=1.0 * 1.0, dist = 5.0 * 1.0)
    steps, dist_m, cost = compute_path_metrics(path, cost_map, pixel_size_m=5.0)

    expected_dist = 5.0 * SQRT2 + 5.0
    expected_cost = 4.0 * SQRT2 + 1.0

    assert steps == 2
    assert math.isclose(dist_m, expected_dist, rel_tol=1e-3)
    assert math.isclose(cost, expected_cost, rel_tol=1e-3)


# ===========================================================================
# 14. Deterministic Behavior Under Fixed Settings
# ===========================================================================
def test_search_determinism():
    cost_map = np.ones((20, 20), dtype=np.float64)
    start = (2, 3)
    goal = (17, 16)

    for search_func in [bfs_search, dfs_search, dijkstra_search, astar_search]:
        res1 = search_func(cost_map, start, goal)
        res2 = search_func(cost_map, start, goal)
        assert res1.success == res2.success
        assert res1.path == res2.path
        assert res1.expanded_nodes == res2.expanded_nodes


# ===========================================================================
# 15. Compatibility With Existing weighted_astar Interface
# ===========================================================================
def test_weighted_astar_backwards_compatibility():
    cost_map = np.ones((10, 10), dtype=np.float64)
    start = (1, 1)
    goal = (8, 8)

    # Legacy interface returns Optional[List[Tuple[int, int]]]
    path = weighted_astar(cost_map, start, goal, w=1.5)
    assert isinstance(path, list)
    assert path[0] == start
    assert path[-1] == goal

    # Blocked goal returns None or relocated if auto_relocate=False
    cost_map[8, 8] = 1e6
    path_blocked = weighted_astar(cost_map, start, goal, auto_relocate=False)
    assert path_blocked is None
