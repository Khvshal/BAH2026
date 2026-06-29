import numpy as np
import heapq

def build_cost_map(slope_map, roughness_map, psr_mask, pixel_size_m=5.0):
    """
    Per-pixel traversal cost for rover.
    Combines energy, safety, and solar power into unified cost surface.
    """
    # Energy cost: power proportional to slope
    energy = 1.0 + 8.0 * np.sin(np.radians(slope_map))
    
    # Safety penalty: hard barriers + soft penalties
    safety_penalty = np.zeros_like(slope_map)
    safety_penalty[slope_map > 15.0] = 1e6       # Absolute exclusion
    safety_penalty[slope_map > 10.0] += 50.0      # Steep slope penalty
    safety_penalty += roughness_map * 10.0       # Roughness friction
    
    # Solar bonus: prefer outside of PSR (negative is reward)
    solar_bonus = np.where(psr_mask == 1, 5.0, -1.0)
    
    cost_map = energy + safety_penalty + solar_bonus
    cost_map = np.clip(cost_map, 1.0, 1e6)
    return cost_map

def weighted_astar(cost_map, start, goal, w=1.5):
    """
    Weighted A* (w=1.5 for speed, closer to optimal than Dijkstra).
    Heuristic: Euclidean distance * w * min_cost
    """
    rows, cols = cost_map.shape
    min_cost = float(cost_map[cost_map < 1e5].min()) if np.any(cost_map < 1e5) else 1.0
    
    def h(pos):
        return w * min_cost * np.sqrt((pos[0]-goal[0])**2 + (pos[1]-goal[1])**2)
    
    open_heap = [(h(start), 0, start)]
    came_from = {start: None}
    g_score = {start: 0}
    closed = set()
    
    neighbors = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    diag_factor = [1, 1, 1, 1, np.sqrt(2), np.sqrt(2), np.sqrt(2), np.sqrt(2)]
    
    while open_heap:
        f, g, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        
        if current == goal:
            path = []
            while current:
                path.append(current)
                current = came_from[current]
            return path[::-1]
        
        for (dr, dc), diag in zip(neighbors, diag_factor):
            nr, nc = current[0]+dr, current[1]+dc
            if not (0 <= nr < rows and 0 <= nc < cols) or (nr,nc) in closed:
                continue
            if cost_map[nr, nc] >= 1e5:  # Hard obstacle
                continue
            tentative_g = g + cost_map[nr, nc] * diag
            if (nr,nc) not in g_score or tentative_g < g_score[(nr,nc)]:
                g_score[(nr,nc)] = tentative_g
                came_from[(nr,nc)] = current
                f_new = tentative_g + h((nr,nc))
                heapq.heappush(open_heap, (f_new, tentative_g, (nr,nc)))
                
    return None  # No path found

def smooth_path_rdp(path, epsilon=1.5):
    """Ramer-Douglas-Peucker path simplification."""
    if len(path) < 3:
        return path
    
    start, end = np.array(path[0]), np.array(path[-1])
    line_vec = end - start
    line_len = np.linalg.norm(line_vec)
    if line_len == 0:
        return [path[0], path[-1]]
    
    distances = []
    for point in path[1:-1]:
        p = np.array(point)
        proj = np.dot(p - start, line_vec) / line_len
        nearest = start + proj * line_vec / line_len
        distances.append(np.linalg.norm(p - nearest))
        
    max_dist = max(distances)
    max_idx = distances.index(max_dist) + 1
    
    if max_dist > epsilon:
        left = smooth_path_rdp(path[:max_idx+1], epsilon)
        right = smooth_path_rdp(path[max_idx:], epsilon)
        return left[:-1] + right
    else:
        return [path[0], path[-1]]

def compute_energy_profile(path, slope_map, psr_mask, rover_spec=None):
    """
    Track cumulative energy consumption and solar charging along path.
    """
    if rover_spec is None:
        rover_spec = {
            'battery_wh': 500.0,
            'solar_panel_w': 150.0,
            'drive_power_w': 100.0,
            'speed_m_per_s': 0.1
        }
        
    battery = rover_spec['battery_wh']
    max_battery = rover_spec['battery_wh']
    solar_power_w = rover_spec['solar_panel_w']
    consumption_w = rover_spec['drive_power_w']
    
    profile = []
    for i, (r, c) in enumerate(path):
        # Bound coordinates
        r = min(max(0, int(r)), slope_map.shape[0]-1)
        c = min(max(0, int(c)), slope_map.shape[1]-1)
        
        slope = slope_map[r, c]
        drive_watts = consumption_w + consumption_w * 2.0 * np.sin(np.radians(slope))
        
        # Illuminated area = 1 - psr_mask (psr_mask=1 is shadow)
        is_illuminated = 1.0 - float(psr_mask[r, c])
        solar_in = solar_power_w * is_illuminated
        
        net_power = solar_in - drive_watts
        time_seg = 1.0 / rover_spec['speed_m_per_s'] * 5.0  # 5m pixel resolution
        
        battery += net_power * (time_seg / 3600.0)  # Wh
        battery = np.clip(battery, 0.0, max_battery)
        
        battery_pct = (battery / max_battery) * 100.0
        
        status = 'DRIVING'
        if battery_pct < 20.0:
            status = 'RECHARGE_STOP'
            # Let it charge back up slightly during the stop
            battery = min(max_battery, battery + solar_power_w * 0.5) # charge for 30 min
            
        profile.append({
            'waypoint': i,
            'grid_y': int(r),
            'grid_x': int(c),
            'status': status,
            'battery_pct': round(float(battery_pct), 2),
            'solar_in_w': round(float(solar_in), 2),
            'drive_w': round(float(drive_watts), 2)
        })
        
    return profile
