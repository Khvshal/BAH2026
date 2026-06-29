import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import json
from scipy.ndimage import label
import numpy as np

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "Vedik@098")
DB_NAME = os.getenv("DB_NAME", "polaris")

def get_connection(db_name=DB_NAME):
    """Get a raw connection to the PostgreSQL server."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=db_name
    )

def check_postgis(conn):
    """Check if PostGIS extension is available and enabled."""
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            conn.commit()
            cur.execute("SELECT postgis_version();")
            version = cur.fetchone()
            print(f"[DB] PostGIS is available: {version[0]}")
            return True
        except Exception as e:
            conn.rollback()
            print(f"[DB] PostGIS is not available or failed to enable: {e}")
            return False

def init_db():
    """Verify/create the database and initialize the schema."""
    conn = get_connection("postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;", (DB_NAME,))
        exists = cur.fetchone()
        if not exists:
            print(f"[DB] Creating database '{DB_NAME}'...")
            cur.execute(f"CREATE DATABASE {DB_NAME};")
        else:
            print(f"[DB] Database '{DB_NAME}' already exists.")
            
    conn.close()

    conn = get_connection(DB_NAME)
    has_postgis = check_postgis(conn)
    
    with conn.cursor() as cur:
        geom_type = "GEOMETRY(Point, 4326)" if has_postgis else "VARCHAR(100)"
        poly_geom_type = "GEOMETRY(Polygon, 4326)" if has_postgis else "TEXT"
        line_geom_type = "GEOMETRY(LineString, 4326)" if has_postgis else "TEXT"
        
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS doubly_shadowed_craters (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE,
                center_geom {geom_type},
                area_km2 FLOAT,
                depth_m FLOAT,
                diameter_m FLOAT,
                min_illumination_pct FLOAT,
                estimated_temp_k FLOAT,
                aif FLOAT
            );
        """)
        
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS ice_detections (
                id SERIAL PRIMARY KEY,
                crater_id INT REFERENCES doubly_shadowed_craters(id) ON DELETE CASCADE,
                region_geom {poly_geom_type},
                mean_cpr FLOAT,
                mean_dop FLOAT,
                ice_probability FLOAT,
                uncertainty FLOAT,
                area_km2 FLOAT,
                detection_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS landing_sites (
                id SERIAL PRIMARY KEY,
                crater_id INT REFERENCES doubly_shadowed_craters(id) ON DELETE CASCADE,
                site_geom {geom_type},
                composite_score FLOAT,
                ice_proximity_score FLOAT,
                terrain_safety_score FLOAT,
                solar_illumination_score FLOAT,
                dsc_access_score FLOAT,
                comm_los_score FLOAT,
                rank INT,
                risk_level VARCHAR(20)
            );
        """)
        
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS rover_traversals (
                id SERIAL PRIMARY KEY,
                landing_site_id INT REFERENCES landing_sites(id) ON DELETE CASCADE,
                path_geom {line_geom_type},
                algorithm VARCHAR(50),
                total_distance_m FLOAT,
                estimated_time_hours FLOAT,
                max_slope_encountered_deg FLOAT,
                energy_profile JSONB,
                risk_score FLOAT
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ice_volume_estimates (
                id SERIAL PRIMARY KEY,
                crater_id INT REFERENCES doubly_shadowed_craters(id) ON DELETE CASCADE,
                volume_m3 FLOAT,
                uncertainty_m3 FLOAT,
                ice_area_km2 FLOAT,
                mean_ice_fraction_pct FLOAT,
                depth_m FLOAT,
                water_mass_kg FLOAT,
                astronaut_days FLOAT,
                method VARCHAR(100),
                estimated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        print("[DB] Database schema check/setup complete.")
        
    conn.close()
    return has_postgis


# ---------------------------------------------------------------------------
# Data Integration Helpers
# ---------------------------------------------------------------------------

def pixel_to_lonlat(cx, cy, dem_shape=(3200, 3200), ohrc_extent=None):
    """
    Map DEM pixel coordinates (cx, cy) to geographic (lon, lat) using the OHRC extent.
    Defaults to lunar south pole coordinates if no extent is provided.
    """
    if ohrc_extent:
        lon_min = ohrc_extent.get("lon_min", 22.8)
        lon_max = ohrc_extent.get("lon_max", 27.8)
        lat_min = ohrc_extent.get("lat_min", -85.3)
        lat_max = ohrc_extent.get("lat_max", -84.5)
    else:
        # Standard fallback bounding box for Site 1
        lon_min, lon_max = 22.802526, 27.751481
        lat_min, lat_max = -85.320925, -84.526014

    lon = lon_min + (cx / float(dem_shape[1])) * (lon_max - lon_min)
    # y-axis is inverted in DEM rows
    lat = lat_max - (cy / float(dem_shape[0])) * (lat_max - lat_min)
    return lon, lat


def save_craters_to_db(psr_mask, dsc_mask, dem, ohrc_extent=None):
    """
    Processes the masks to identify craters and saves them to the DB.
    Optimized for fast execution on large grids using single-pass unique counts.
    """
    has_postgis = init_db()
    conn = get_connection()
    
    # Check if there are components in dsc_mask, otherwise fall back to psr_mask
    mask_to_use = dsc_mask if np.sum(dsc_mask) > 0 else psr_mask
    labeled, n_components = label(mask_to_use)
    
    print(f"[DB] Found {n_components} craters/PSRs to save to DB...")
    
    saved_ids = []
    
    # Optimize: Get label counts in a single pass using unique
    unique, counts = np.unique(labeled, return_counts=True)
    # Ignore background label 0
    non_bg = unique != 0
    unique = unique[non_bg]
    counts = counts[non_bg]
    
    # Sort and take top 5 labels
    top_indices = np.argsort(counts)[::-1][:5]
    top_labels = unique[top_indices]
    top_counts = counts[top_indices]
    
    with conn.cursor() as cur:
        # Clear existing
        cur.execute("TRUNCATE doubly_shadowed_craters CASCADE;")
        
        for index, (label_id, pixel_count) in enumerate(zip(top_labels, top_counts)):
            name = f"Shackleton-DSC-0{index+1}" if np.sum(dsc_mask) > 0 else f"PSR-SouthPole-0{index+1}"
            
            ys, xs = np.where(labeled == label_id)
            # Center point
            cy, cx = int(np.mean(ys)), int(np.mean(xs))
            lon, lat = pixel_to_lonlat(cx, cy, dem.shape, ohrc_extent)
            
            # Physical metrics
            area_km2 = float(pixel_count * (5.0 * 5.0) / 1e6)  # assuming 5m resolution
            diameter_m = float(2.0 * np.sqrt(area_km2 * 1e6 / np.pi))
            
            crater_elevations = dem[ys, xs]
            min_elev = float(np.min(crater_elevations))
            max_elev = float(np.max(crater_elevations))
            depth_m = max(50.0, max_elev - min_elev)
            
            min_illum = 0.0
            temp_k = 40.0
            aif = 0.0
            
            if has_postgis:
                geom_val = f"ST_GeomFromText('POINT({lon} {lat})', 4326)"
                cur.execute(f"""
                    INSERT INTO doubly_shadowed_craters 
                    (name, center_geom, area_km2, depth_m, diameter_m, min_illumination_pct, estimated_temp_k, aif)
                    VALUES (%s, {geom_val}, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (name, area_km2, depth_m, diameter_m, min_illum, temp_k, aif))
            else:
                geom_val = f"POINT({lon} {lat})"
                cur.execute("""
                    INSERT INTO doubly_shadowed_craters 
                    (name, center_geom, area_km2, depth_m, diameter_m, min_illumination_pct, estimated_temp_k, aif)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (name, geom_val, area_km2, depth_m, diameter_m, min_illum, temp_k, aif))
                
            crater_id = cur.fetchone()[0]
            saved_ids.append(crater_id)
            
        conn.commit()
    conn.close()
    print(f"[DB] Successfully inserted {len(saved_ids)} craters into DB.")
    return saved_ids


def save_landing_sites_to_db(candidates, crater_ids, ohrc_extent=None):
    """Saves identified landing candidates to DB."""
    if not crater_ids:
        return
    
    has_postgis = init_db()
    conn = get_connection()
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE landing_sites CASCADE;")
        
        for c in candidates:
            # Match to first crater for demo reference
            crater_id = crater_ids[0]
            cx, cy = c["pixel_x"], c["pixel_y"]
            lon, lat = pixel_to_lonlat(cx, cy, (3200, 3200), ohrc_extent)
            
            # Scores & metrics
            comp_score = c.get("composite_score", 1.0 - c["mean_hazard"])
            ice_prox = c.get("ice_proximity_score", 0.8)
            safety = c.get("terrain_safety_score", 1.0 - (c["mean_slope_deg"] / 15.0))
            solar = c.get("solar_illumination_score", 0.75)
            access = c.get("dsc_access_score", 0.85)
            comm = c.get("comm_los_score", 0.9)
            rank = c["rank"]
            risk = "LOW" if c["mean_hazard"] < 0.2 else "MEDIUM"
            
            if has_postgis:
                geom_val = f"ST_GeomFromText('POINT({lon} {lat})', 4326)"
                cur.execute(f"""
                    INSERT INTO landing_sites 
                    (crater_id, site_geom, composite_score, ice_proximity_score, terrain_safety_score, 
                     solar_illumination_score, dsc_access_score, comm_los_score, rank, risk_level)
                    VALUES (%s, {geom_val}, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (crater_id, comp_score, ice_prox, safety, solar, access, comm, rank, risk))
            else:
                geom_val = f"POINT({lon} {lat})"
                cur.execute("""
                    INSERT INTO landing_sites 
                    (crater_id, site_geom, composite_score, ice_proximity_score, terrain_safety_score, 
                     solar_illumination_score, dsc_access_score, comm_los_score, rank, risk_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (crater_id, geom_val, comp_score, ice_prox, safety, solar, access, comm, rank, risk))
                
        conn.commit()
    conn.close()
    print("[DB] Landing candidates inserted successfully.")


def save_ice_detections_to_db(crater_ids, cpr, dop, ice_prob, ohrc_extent=None):
    """Saves ice detection statistics and bounds to DB."""
    if not crater_ids:
        return
    
    has_postgis = init_db()
    conn = get_connection()
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE ice_detections CASCADE;")
        
        # Calculate summary stats for the high probability ice area
        ice_mask = ice_prob > 0.5
        mean_cpr_val = float(np.mean(cpr[ice_mask])) if np.any(ice_mask) else 0.0
        mean_dop_val = float(np.mean(dop[ice_mask])) if np.any(ice_mask) else 0.0
        avg_prob = float(np.mean(ice_prob[ice_mask])) if np.any(ice_mask) else 0.0
        uncertainty = 0.15 # standard error model
        area_km2 = float(np.sum(ice_mask) * (5.0 * 5.0) / 1e6)
        
        # Create a bounding box polygon for the ice region
        # Get bounding box pixels
        if np.any(ice_mask):
            ys, xs = np.where(ice_mask)
            min_y, max_y = int(np.min(ys)), int(np.max(ys))
            min_x, max_x = int(np.min(xs)), int(np.max(xs))
            
            # Map corner pixels to lat/lon
            lon1, lat1 = pixel_to_lonlat(min_x, min_y, ice_prob.shape, ohrc_extent)
            lon2, lat2 = pixel_to_lonlat(max_x, min_y, ice_prob.shape, ohrc_extent)
            lon3, lat3 = pixel_to_lonlat(max_x, max_y, ice_prob.shape, ohrc_extent)
            lon4, lat4 = pixel_to_lonlat(min_x, max_y, ice_prob.shape, ohrc_extent)
            
            poly_wkt = f"POLYGON(({lon1} {lat1}, {lon2} {lat2}, {lon3} {lat3}, {lon4} {lat4}, {lon1} {lat1}))"
        else:
            poly_wkt = "POLYGON((0 0, 0 0, 0 0, 0 0, 0 0))"
            
        crater_id = crater_ids[0]
        
        if has_postgis:
            geom_val = f"ST_GeomFromText('{poly_wkt}', 4326)"
            cur.execute(f"""
                INSERT INTO ice_detections 
                (crater_id, region_geom, mean_cpr, mean_dop, ice_probability, uncertainty, area_km2)
                VALUES (%s, {geom_val}, %s, %s, %s, %s, %s);
            """, (crater_id, mean_cpr_val, mean_dop_val, avg_prob, uncertainty, area_km2))
        else:
            cur.execute("""
                INSERT INTO ice_detections 
                (crater_id, region_geom, mean_cpr, mean_dop, ice_probability, uncertainty, area_km2)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (crater_id, poly_wkt, mean_cpr_val, mean_dop_val, avg_prob, uncertainty, area_km2))
            
        conn.commit()
    conn.close()
    print("[DB] Ice detections inserted successfully.")


def save_rover_traversal_to_db(landing_site_rank, path, algorithm, total_distance_m, estimated_time_hours, max_slope, energy_profile, risk_score):
    """Saves a rover traverse path to DB matched to landing site by rank."""
    has_postgis = init_db()
    conn = get_connection()
    
    with conn.cursor() as cur:
        # Find landing site ID
        cur.execute("SELECT id FROM landing_sites WHERE rank = %s;", (landing_site_rank,))
        res = cur.fetchone()
        if not res:
            print(f"[DB] Error: No landing site with rank {landing_site_rank} found.")
            conn.close()
            return
        site_id = res[0]
        
        # Clear existing traversal for this site
        cur.execute("DELETE FROM rover_traversals WHERE landing_site_id = %s;", (site_id,))
        
        # Build path WKT
        path_points = []
        for r, c in path:
            lon, lat = pixel_to_lonlat(c, r) # column=x, row=y
            path_points.append(f"{lon} {lat}")
        
        path_wkt = f"LINESTRING({', '.join(path_points)})"
        
        if has_postgis:
            geom_val = f"ST_GeomFromText('{path_wkt}', 4326)"
            cur.execute(f"""
                INSERT INTO rover_traversals 
                (landing_site_id, path_geom, algorithm, total_distance_m, estimated_time_hours, 
                 max_slope_encountered_deg, energy_profile, risk_score)
                VALUES (%s, {geom_val}, %s, %s, %s, %s, %s, %s);
            """, (site_id, algorithm, total_distance_m, estimated_time_hours, max_slope, json.dumps(energy_profile), risk_score))
        else:
            cur.execute("""
                INSERT INTO rover_traversals 
                (landing_site_id, path_geom, algorithm, total_distance_m, estimated_time_hours, 
                 max_slope_encountered_deg, energy_profile, risk_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (site_id, path_wkt, algorithm, total_distance_m, estimated_time_hours, max_slope, json.dumps(energy_profile), risk_score))
            
        conn.commit()
    conn.close()
    print(f"[DB] Rover traversal saved for landing site rank {landing_site_rank}.")


def save_ice_volume_estimate_to_db(crater_id, volume_m3, uncertainty_m3, ice_area_km2, mean_ice_fraction, depth_m, method):
    """Saves ice volume estimates to DB."""
    conn = get_connection()
    
    with conn.cursor() as cur:
        # Clear existing
        cur.execute("DELETE FROM ice_volume_estimates WHERE crater_id = %s;", (crater_id,))
        
        # ISRU calculations
        water_mass = volume_m3 * 917.0 * mean_ice_fraction # 917 kg/m3 density of pure ice
        astronaut_days = water_mass / 3.0 # 3kg per astronaut per day
        
        cur.execute("""
            INSERT INTO ice_volume_estimates 
            (crater_id, volume_m3, uncertainty_m3, ice_area_km2, mean_ice_fraction_pct, 
             depth_m, water_mass_kg, astronaut_days, method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (crater_id, volume_m3, uncertainty_m3, ice_area_km2, mean_ice_fraction * 100, depth_m, water_mass, astronaut_days, method))
        
        conn.commit()
    conn.close()
    print("[DB] Ice volume estimate inserted successfully.")
