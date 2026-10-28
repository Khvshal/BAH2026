"""
Benchmark Dataset Generator & Verifier
======================================
Curates and verifies 15 diverse, stratified start-goal route pairs
on the 256x256 lunar south pole terrain map.
Guarantees feasibility using Dijkstra optimal ground truth,
records terrain difficulty characteristics, and saves benchmark_config.json.
"""

import json
import os
import sys
import numpy as np

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.sample_maps import load_or_generate_terrain
from algorithms.cost_map import build_cost_map
from algorithms.dijkstra import dijkstra_search
from algorithms.search_common import validate_endpoints


def select_benchmark_pairs():
    terrain = load_or_generate_terrain(size=256)
    slope = terrain["slope"]
    roughness = terrain["roughness"]
    psr = terrain["psr_mask"]
    pixel_size = float(terrain["pixel_size_m"])

    cost_map = build_cost_map(slope, roughness, psr, pixel_size_m=pixel_size, max_slope_limit=15.0)

    # 15 Stratified candidate pairs designed for meaningful benchmark diversity:
    # Categories: Short (S), Medium (M), Long (L), Obstacle-Circumvention (O), PSR-Shadow (P), Steep-Margin (T)
    candidates = [
        # --- Short Distance (20 - 45 cells) ---
        {
            "id": "PAIR_01",
            "name": "Alpha Ridge Local Survey",
            "category": "SHORT",
            "start": [46, 51],
            "goal": [58, 68],
            "description": "Short traverse across gently undulating highland regolith near primary landing site.",
        },
        {
            "id": "PAIR_02",
            "name": "North Plate Station Scouting",
            "category": "SHORT",
            "start": [38, 199],
            "goal": [52, 185],
            "description": "Short station traverse on northern plateau avoiding localized boulder fields.",
        },
        {
            "id": "PAIR_03",
            "name": "Northwest Breach Approach",
            "category": "SHORT",
            "start": [75, 70],
            "goal": [92, 85],
            "description": "Short approach along the navigable crater entry ramp on the northwest rim.",
        },

        # --- Medium Distance (50 - 110 cells) ---
        {
            "id": "PAIR_04",
            "name": "Alpha Ridge to Northwest Rim Outcrop",
            "category": "MEDIUM",
            "start": [46, 51],
            "goal": [81, 76],
            "description": "Descent from landing ridge towards geologic rim outcrop.",
        },
        {
            "id": "PAIR_05",
            "name": "North Plate to Central Ridge",
            "category": "MEDIUM",
            "start": [38, 199],
            "goal": [85, 145],
            "description": "Incline transition from northern sunlit plateau down toward northern crater terrace.",
        },
        {
            "id": "PAIR_06",
            "name": "Northwest Ramp to Crater Floor Mound",
            "category": "MEDIUM",
            "start": [81, 76],
            "goal": [134, 124],
            "description": "Transverse route down the entry ramp to the central crater floor peak.",
        },
        {
            "id": "PAIR_07",
            "name": "East Terrace Cross-Basin",
            "category": "MEDIUM",
            "start": [166, 225],
            "goal": [195, 180],
            "description": "Southeastern terrace passage skirting secondary crater ejecta mounds.",
        },

        # --- Long Distance (120 - 200 cells) ---
        {
            "id": "PAIR_08",
            "name": "Trans-Crater Rim Traverse (North to South)",
            "category": "LONG",
            "start": [35, 128],
            "goal": [220, 130],
            "description": "Major longitudinal trek navigating around deep crater bowl and southern high-slope rim.",
        },
        {
            "id": "PAIR_09",
            "name": "Alpha Ridge to East Terrace Overland",
            "category": "LONG",
            "start": [46, 51],
            "goal": [166, 225],
            "description": "Major diagonal traverse spanning northwestern landing highlands to southeastern terrace.",
        },
        {
            "id": "PAIR_10",
            "name": "Southwest Highland to Northeast Basin",
            "category": "LONG",
            "start": [215, 45],
            "goal": [40, 210],
            "description": "Extreme diagonal corridor through varied slope regimes and highland ridges.",
        },

        # --- Obstacle Avoidance & Steep Terrain Circumvention ---
        {
            "id": "PAIR_11",
            "name": "South Rim Wall Obstacle Detour",
            "category": "OBSTACLE_DETOUR",
            "start": [180, 69],
            "goal": [184, 161],
            "description": "Direct line blocked by steep >15° southern rim wall; requires lateral circumvention.",
        },
        {
            "id": "PAIR_12",
            "name": "Secondary Crater Bypass Corridor",
            "category": "OBSTACLE_DETOUR",
            "start": [60, 60],
            "goal": [75, 100],
            "description": "Navigates between two hazardous secondary impact craters with slope barriers.",
        },
        {
            "id": "PAIR_13",
            "name": "Central Mound Steep Gradient Skirt",
            "category": "STEEP_MARGIN",
            "start": [120, 95],
            "goal": [145, 150],
            "description": "Routes past the foot of the central uplift mound where slopes hover near caution limits.",
        },

        # --- PSR (Cold Trap / Shadow) Exploration Routes ---
        {
            "id": "PAIR_14",
            "name": "Shoemaker Deep PSR Penetration",
            "category": "PSR_COLD_TRAP",
            "start": [114, 119],
            "goal": [158, 137],
            "description": "Enters permanently shadowed cold-trap depression to sample high-probability volatile ice.",
        },
        {
            "id": "PAIR_15",
            "name": "PSR Cross-Shadow Transit",
            "category": "PSR_COLD_TRAP",
            "start": [133, 103],
            "goal": [165, 145],
            "description": "Traverses deep shadow region requiring energy management against battery depletion.",
        },


    ]

    print(f"Verifying {len(candidates)} candidate benchmark pairs against cost map...")
    verified_pairs = []

    for item in candidates:
        s = tuple(item["start"])
        g = tuple(item["goal"])

        is_valid, reason, clean_s, clean_g = validate_endpoints(cost_map, s, g)
        if not is_valid:
            raise ValueError(f"Endpoint invalid for {item['id']}: {reason}")

        # Check feasibility with Dijkstra (ground truth optimal)
        dijk_res = dijkstra_search(cost_map, clean_s, clean_g)
        if not dijk_res.success:
            raise RuntimeError(f"Candidate {item['id']} ({item['name']}) has no traversable path! Reason: {dijk_res.failure_reason}")

        # Compute Euclidean metrics
        dr = g[0] - s[0]
        dc = g[1] - s[1]
        euclid_cells = float(np.hypot(dr, dc))
        euclid_dist_m = euclid_cells * pixel_size

        pair_meta = {
            **item,
            "start": [int(clean_s[0]), int(clean_s[1])],
            "goal": [int(clean_g[0]), int(clean_g[1])],
            "euclidean_distance_cells": round(euclid_cells, 2),
            "euclidean_distance_m": round(euclid_dist_m, 2),
            "dijkstra_optimal_steps": dijk_res.path_length_steps,
            "dijkstra_optimal_dist_m": dijk_res.path_distance_m,
            "dijkstra_optimal_cost": dijk_res.terrain_cost,
        }
        verified_pairs.append(pair_meta)
        print(f"  [OK] {item['id']:<8} | {item['category']:<15} | Steps={dijk_res.path_length_steps:<4} | Dist={dijk_res.path_distance_m:<6.1f}m | Cost={dijk_res.terrain_cost:<7.1f} | {item['name']}")

    assert len(verified_pairs) == 15, f"Expected 15 pairs, got {len(verified_pairs)}"

    config = {
        "benchmark_title": "Lunar South Pole Rover Path Planning Benchmark",
        "terrain_map_id": "synthetic_polar_crater_256",
        "grid_shape": [256, 256],
        "pixel_size_m": pixel_size,
        "max_slope_limit_deg": 15.0,
        "warning_slope_deg": 10.0,
        "obstacle_cost_threshold": 100000.0,
        "random_seed": 42,
        "dls_depth_limits": [25, 50, 100, 200, 350],
        "astar_heuristic_weights": [1.5],
        "algorithms": ["BFS", "DFS", "DLS", "Dijkstra", "Weighted A*"],
        "num_pairs": len(verified_pairs),
        "pairs": verified_pairs,
    }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_config.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"\nSuccessfully generated and saved verified benchmark config to: {out_path}")
    return config


if __name__ == "__main__":
    select_benchmark_pairs()
