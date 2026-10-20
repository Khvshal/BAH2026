"""
Weighted A* Pathfinding on 2D Traversal Cost Grids
=================================================
Optimized graph search for planetary rover navigation.
Uses 8-directional kinematics and admissible/weighted heuristics.
"""

import heapq
import math
from typing import List, Tuple, Optional
import numpy as np


def weighted_astar(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    w: float = 1.5,
    obstacle_threshold: float = 1e5,
) -> Optional[List[Tuple[int, int]]]:
    """
    Computes an energy/safety-optimal 2D path between start and goal using Weighted A*.

    Parameters:
    -----------
    cost_map : np.ndarray (2D float)
        Traversability cost per cell.
    start : (row, col)
        Start pixel coordinates.
    goal : (row, col)
        Target destination pixel coordinates.
    w : float
        Heuristic weight (w=1.0 is standard optimal A*, w>1.0 speeds up search).
    obstacle_threshold : float
        Cost above which cells are treated as impassable.

    Returns:
    --------
    List of (row, col) coordinates representing the path, or None if unreachable.
    """
    rows, cols = cost_map.shape
    start = (int(start[0]), int(start[1]))
    goal = (int(goal[0]), int(goal[1]))

    # Bounds check
    if not (0 <= start[0] < rows and 0 <= start[1] < cols):
        raise ValueError(f"Start coordinate {start} is out of map bounds ({rows}, {cols})")
    if not (0 <= goal[0] < rows and 0 <= goal[1] < cols):
        raise ValueError(f"Goal coordinate {goal} is out of map bounds ({rows}, {cols})")

    # If start or goal is inside an impassable obstacle, find nearest passable cell
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

    start = find_nearest_passable(start)
    goal = find_nearest_passable(goal)

    passable_costs = cost_map[cost_map < obstacle_threshold]
    min_cost = float(passable_costs.min()) if passable_costs.size > 0 else 1.0

    def heuristic(pos: Tuple[int, int]) -> float:
        dr = pos[0] - goal[0]
        dc = pos[1] - goal[1]
        return w * min_cost * math.hypot(dr, dc)

    # 8-connected neighbors with geometric step lengths
    sqrt2 = math.sqrt(2.0)
    neighbors = [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, sqrt2),
        (-1, 1, sqrt2),
        (1, -1, sqrt2),
        (1, 1, sqrt2),
    ]

    open_heap = []
    # (f_score, g_score, (r, c))
    heapq.heappush(open_heap, (heuristic(start), 0.0, start))

    came_from = {}
    g_score = {start: 0.0}
    closed = set()

    while open_heap:
        f, g, current = heapq.heappop(open_heap)

        if current in closed:
            continue
        closed.add(current)

        if current == goal:
            # Reconstruct path
            path = []
            curr = current
            while curr in came_from:
                path.append(curr)
                curr = came_from[curr]
            path.append(start)
            return path[::-1]

        for dr, dc, dist_mult in neighbors:
            nr, nc = current[0] + dr, current[1] + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if (nr, nc) in closed:
                continue

            cell_cost = cost_map[nr, nc]
            if cell_cost >= obstacle_threshold:
                continue

            # Traversal step cost
            step_cost = cell_cost * dist_mult
            tentative_g = g + step_cost

            if (nr, nc) not in g_score or tentative_g < g_score[(nr, nc)]:
                g_score[(nr, nc)] = tentative_g
                came_from[(nr, nc)] = current
                f_new = tentative_g + heuristic((nr, nc))
                heapq.heappush(open_heap, (f_new, tentative_g, (nr, nc)))

    return None
