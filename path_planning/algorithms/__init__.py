"""
Lunar Rover Path Planning Algorithms
====================================
Modular path planning toolkit for lunar south pole exploration:
- Cost surface generation from slope, roughness, and PSR masks
- Weighted A* optimal graph search
- Ramer-Douglas-Peucker (RDP) path smoothing
- Energy and solar budget simulation
"""

from .cost_map import build_cost_map
from .search_common import SearchResult
from .astar import astar_search, weighted_astar
from .bfs import bfs_search
from .dfs import dfs_search
from .dls import dls_search
from .dijkstra import dijkstra_search
from .smoother import smooth_path_rdp
from .energy_model import compute_energy_profile

__all__ = [
    "build_cost_map",
    "SearchResult",
    "astar_search",
    "weighted_astar",
    "bfs_search",
    "dfs_search",
    "dls_search",
    "dijkstra_search",
    "smooth_path_rdp",
    "compute_energy_profile",
]

