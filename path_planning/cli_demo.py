"""
Lunar Rover Path Planning — CLI Demonstration & Matplotlib Visualizer
=====================================================================
Executes the full pipeline:
  1. Load/synthesize lunar DEM, slope, roughness, and PSR maps
  2. Generate composite traversability cost surface
  3. Execute Weighted A* search
  4. Perform RDP path simplification
  5. Simulate rover energy and solar recharge telemetry
  6. Generate a 4-panel diagnostic plot saved to disk
"""

import os
import sys
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt

# Ensure local modules are accessible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from algorithms import build_cost_map, weighted_astar, smooth_path_rdp, compute_energy_profile
from data import load_or_generate_terrain


def run_demo(start_coord=None, goal_coord=None, output_image="traverse_plan_result.png"):
    print("=" * 65)
    print("      LUNAR ROVER PATH PLANNING & ENERGY TELEMETRY PIPELINE")
    print("=" * 65)

    # 1. Load terrain
    print("\n[1/5] Ingesting lunar polar terrain maps...")
    terrain = load_or_generate_terrain(size=256)
    slope = terrain["slope"]
    roughness = terrain["roughness"]
    psr_mask = terrain["psr_mask"]
    elevation = terrain["elevation"]
    landmarks = terrain["landmarks"]
    pixel_size = terrain["pixel_size_m"]

    # Choose start and goal
    if start_coord is None:
        site = landmarks["landing_sites"][0]
        start = (site["r"], site["c"])
        start_label = site["name"]
    else:
        start = tuple(start_coord)
        start_label = f"Coord {start}"

    if goal_coord is None:
        target = landmarks["science_targets"][0]
        goal = (target["r"], target["c"])
        goal_label = target["name"]
    else:
        goal = tuple(goal_coord)
        goal_label = f"Coord {goal}"

    print(f"  * Origin: {start_label} at grid {start}")
    print(f"  * Destination: {goal_label} at grid {goal}")
    print(f"  * Terrain Grid Size: {slope.shape[0]}x{slope.shape[1]} (pixel res = {pixel_size}m)")

    # 2. Build cost map
    print("\n[2/5] Building composite traversability cost surface...")
    cost_map = build_cost_map(slope, roughness, psr_mask, pixel_size_m=pixel_size)
    passable_ratio = (cost_map < 1e5).sum() / cost_map.size * 100.0
    print(f"  * Safe navigable terrain: {passable_ratio:.1f}%")
    print(f"  * Hazardous/Impassable (>15° slope): {100.0 - passable_ratio:.1f}%")

    # 3. Plan path with Weighted A*
    print("\n[3/5] Executing Weighted A* graph search (w=1.5)...")
    raw_path = weighted_astar(cost_map, start, goal, w=1.5)

    if not raw_path:
        print("  [ERROR] No traversable path found between start and destination!")
        return

    print(f"  * Raw A* path found: {len(raw_path)} grid steps.")

    # 4. Smooth path
    print("\n[4/5] Smoothing path via Ramer-Douglas-Peucker (RDP)...")
    smooth_path = smooth_path_rdp(raw_path, epsilon=1.5)
    print(f"  * Path simplified to: {len(smooth_path)} primary drive waypoints.")

    # 5. Energy and telemetry simulation
    print("\n[5/5] Simulating rover battery discharge and solar charging...")
    plan_result = compute_energy_profile(raw_path, slope, psr_mask, pixel_size_m=pixel_size)
    telemetry = plan_result["telemetry"]

    # Output Summary
    print("\n" + "-" * 40)
    print("      MISSION TRAVERSE SUMMARY")
    print("-" * 40)
    print(f"  Total Distance Traversed : {plan_result['total_distance_m']:.1f} m ({plan_result['total_distance_m']/1000.0:.2f} km)")
    print(f"  Total Mission Time       : {plan_result['total_time_hours']:.2f} hours")
    print(f"  Maximum Slope Encountered: {plan_result['max_slope_deg']:.1f}°")
    print(f"  Minimum Battery Reserve  : {plan_result['min_battery_pct']:.1f}%")
    recharge_count = sum(1 for t in telemetry if t["status"] == "RECHARGE_STOP")
    print(f"  Solar Recharge Halts     : {recharge_count}")
    print("-" * 40)

    # 6. Plotting
    print(f"\n[Plotting] Generating 4-panel diagnostic visualization -> {output_image}")
    fig, axes = plt.subplots(2, 2, figsize=(14, 12), dpi=150)

    # Panel A: OHRC Optical Imagery + Rover Path
    ax1 = axes[0, 0]
    ohrc_opt = terrain.get("ohrc_optical", elevation)
    source_tag = "Real ISRO" if terrain.get("is_real_ohrc") else "Photometric"
    im1 = ax1.imshow(ohrc_opt, cmap="gray", origin="upper")
    ax1.set_title(f"OHRC Optical Image ({source_tag}) & Planned Route", fontsize=12, fontweight="bold")
    plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04, label="Reflectance (DN)")
    
    path_r = [p[0] for p in raw_path]
    path_c = [p[1] for p in raw_path]
    # Overlay subtle hazard mask
    steep_mask_a = np.ma.masked_where(slope <= 15.0, slope)
    ax1.imshow(steep_mask_a, cmap="Reds", alpha=0.35, origin="upper")

    ax1.plot(path_c, path_r, color="cyan", linewidth=2.5, label="Planned Route")
    ax1.scatter([start[1]], [start[0]], color="lime", s=90, edgecolors="black", zorder=5, label="Start (Landing Site)")
    ax1.scatter([goal[1]], [goal[0]], color="red", s=90, edgecolors="white", marker="*", zorder=5, label="Goal (Science Target)")
    ax1.legend(loc="upper right", fontsize=8)

    # Panel B: Slope & Obstacles
    ax2 = axes[0, 1]
    im2 = ax2.imshow(slope, cmap="inferno", origin="upper")
    ax2.set_title("Terrain Slope (deg) & Incline Hazard", fontsize=12, fontweight="bold")
    plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04, label="Slope (deg)")
    ax2.plot(path_c, path_r, color="white", linewidth=1.8, linestyle="--")
    # Highlight steep slopes
    steep_mask = np.ma.masked_where(slope <= 15.0, slope)
    ax2.imshow(steep_mask, cmap="Reds", alpha=0.5, origin="upper")

    # Panel C: Cost Surface & PSR Shadow
    ax3 = axes[1, 0]
    im3 = ax3.imshow(np.log1p(cost_map), cmap="viridis", origin="upper")
    ax3.set_title("Traversability Cost Map (log scale) & PSR", fontsize=12, fontweight="bold")
    plt.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04, label="log(1 + Cost)")
    # Overlay PSR mask
    psr_overlay = np.ma.masked_where(psr_mask == 0, psr_mask)
    ax3.imshow(psr_overlay, cmap="cool", alpha=0.35, origin="upper")
    ax3.plot(path_c, path_r, color="yellow", linewidth=2.0)

    # Panel D: Battery State of Charge & Power Budget
    ax4 = axes[1, 1]
    dist_km = [t["distance_m"] / 1000.0 for t in telemetry]
    soc = [t["battery_pct"] for t in telemetry]
    solar = [t["solar_in_w"] for t in telemetry]
    drive = [t["drive_w"] for t in telemetry]

    ax4.plot(dist_km, soc, color="#10b981", linewidth=2.5, label="Battery SoC (%)")
    ax4.set_xlabel("Traverse Distance (km)", fontsize=10)
    ax4.set_ylabel("Battery State of Charge (%)", color="#10b981", fontsize=10)
    ax4.set_ylim(0, 105)
    ax4.grid(True, linestyle=":", alpha=0.6)

    ax4_twin = ax4.twinx()
    ax4_twin.plot(dist_km, solar, color="#f59e0b", linewidth=1.5, linestyle="--", label="Solar Gen (W)")
    ax4_twin.plot(dist_km, drive, color="#ef4444", linewidth=1.5, linestyle=":", label="Drive Draw (W)")
    ax4_twin.set_ylabel("Power (Watts)", color="#f59e0b", fontsize=10)
    ax4_twin.set_ylim(0, max(220, max(drive) + 30))

    ax4.set_title("Rover Energy Profile & Solar Budget Along Traverse", fontsize=12, fontweight="bold")

    # Combined legend
    lines1, labels1 = ax4.get_legend_handles_labels()
    lines2, labels2 = ax4_twin.get_legend_handles_labels()
    ax4.legend(lines1 + lines2, labels1 + labels2, loc="lower left", fontsize=8)

    plt.tight_layout()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_image)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"\n[Done] Analysis and plot successfully created: {out_path}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lunar Rover Path Planning CLI Demo")
    parser.add_argument("--start", nargs=2, type=int, help="Start row col")
    parser.add_argument("--goal", nargs=2, type=int, help="Goal row col")
    parser.add_argument("--out", type=str, default="traverse_plan_result.png", help="Output image filename")
    args = parser.parse_args()

    run_demo(start_coord=args.start, goal_coord=args.goal, output_image=args.out)
