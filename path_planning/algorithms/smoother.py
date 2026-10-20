"""
Path Smoothing and Simplification
================================
Ramer-Douglas-Peucker (RDP) algorithm and path resampling for rover navigation.
Reduces zigzag micro-steps into clean rover drive waypoints.
"""

from typing import List, Tuple
import numpy as np


def smooth_path_rdp(path: List[Tuple[int, int]], epsilon: float = 1.5) -> List[Tuple[int, int]]:
    """
    Simplifies a discrete grid path using the Ramer-Douglas-Peucker algorithm.

    Parameters:
    -----------
    path : List of (row, col)
        Discrete waypoints from A*.
    epsilon : float
        Tolerance threshold for point elimination (distance in pixels).

    Returns:
    --------
    List of simplified (row, col) waypoints.
    """
    if len(path) < 3:
        return path

    start = np.array(path[0], dtype=np.float64)
    end = np.array(path[-1], dtype=np.float64)
    line_vec = end - start
    line_len = np.linalg.norm(line_vec)

    if line_len == 0.0:
        return [path[0], path[-1]]

    # Compute perpendicular distance of all intermediate points from segment
    unit_line = line_vec / line_len
    distances = []
    for pt in path[1:-1]:
        p = np.array(pt, dtype=np.float64)
        proj = np.dot(p - start, unit_line)
        nearest = start + proj * unit_line
        dist = np.linalg.norm(p - nearest)
        distances.append(dist)

    max_dist = max(distances)
    max_idx = distances.index(max_dist) + 1

    if max_dist > epsilon:
        # Recursively simplify both halves
        left = smooth_path_rdp(path[: max_idx + 1], epsilon)
        right = smooth_path_rdp(path[max_idx:], epsilon)
        return left[:-1] + right
    else:
        return [path[0], path[-1]]


def resample_path(path: List[Tuple[int, int]], step_size: float = 1.0) -> List[Tuple[float, float]]:
    """
    Linearly resamples a simplified waypoint path into evenly spaced discrete points.
    Useful for dense kinematic simulation and energy evaluation.
    """
    if len(path) < 2:
        return [(float(r), float(c)) for r, c in path]

    resampled = [(float(path[0][0]), float(path[0][1]))]
    for i in range(len(path) - 1):
        p1 = np.array(path[i], dtype=np.float64)
        p2 = np.array(path[i + 1], dtype=np.float64)
        dist = np.linalg.norm(p2 - p1)
        if dist <= step_size:
            resampled.append((float(p2[0]), float(p2[1])))
            continue

        num_steps = int(np.ceil(dist / step_size))
        for step in range(1, num_steps + 1):
            t = step / num_steps
            interp = p1 + t * (p2 - p1)
            resampled.append((float(interp[0]), float(interp[1])))

    return resampled
