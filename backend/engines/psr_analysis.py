"""
PSR Analysis Engine - End-to-End on Real Chandrayaan-2 / LOLA Data.

Data sources consumed (all from ``dataset demo/``):
  1. LOLA DEM  - Site01_final_adj_5mpp_surf.tif  (GeoTIFF, float32, metres)
  2. LOLA Slope - Site01_final_adj_5mpp_slp.tif   (GeoTIFF, float32, degrees - used for cross-validation)
  3. OHRC Image - ch2_ohr_..._d_img_d18.img       (raw binary, uint8, 101075x12000)
  4. OHRC Geometry - ch2_ohr_..._g_grd_d18.csv    (lon,lat,pixel,scan)
  5. OHRC XML Metadata - ch2_ohr_..._d_img_d18.xml (sun_azimuth, sun_elevation)

Products written to ``output_dir``:
  slope.npy, roughness.npy, psr_mask.npy, dsc_mask.npy, hazard.npy,
  landing_candidates.json, ohrc_base.npy, dem_elevation.npy,
  lola_slope_validated.npy, metadata.json
"""

import numpy as np
from scipy.ndimage import sobel, uniform_filter, label, binary_dilation
import rasterio
import json
import os
import csv
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_solar_from_ohrc_xml(xml_path: str) -> dict | None:
    """
    Extract sun_azimuth and sun_elevation from the OHRC PDS4 XML label.
    These are the authoritative values from the ISRO pipeline.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # The ISDA namespace varies; search all elements
        sun_az = None
        sun_el = None
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "sun_azimuth" and elem.text:
                sun_az = float(elem.text)
            elif tag == "sun_elevation" and elem.text:
                sun_el = float(elem.text)
        if sun_az is not None and sun_el is not None:
            return {"solar_azimuth": sun_az, "solar_elevation": sun_el}
    except Exception as e:
        print(f"[XML] Warning: could not parse solar params from {xml_path}: {e}")
    return None


def _read_ohrc_geometry_csv(csv_path: str, sample_every: int = 100) -> np.ndarray:
    """
    Read OHRC geometry CSV (Longitude, Latitude, Pixel, Scan).
    Samples every ``sample_every`` rows to keep memory bounded.
    Returns structured ndarray with fields: lon, lat, pixel, scan
    """
    rows = []
    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header
        for i, row in enumerate(reader):
            if i % sample_every == 0:
                try:
                    rows.append((float(row[0]), float(row[1]), int(row[2]), int(row[3])))
                except (ValueError, IndexError):
                    continue
    dt = np.dtype([("lon", "f8"), ("lat", "f8"), ("pixel", "i4"), ("scan", "i4")])
    return np.array(rows, dtype=dt)


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class PSRAnalysisEngine:
    """
    End-to-end Terrain, PSR & Hazard Analysis using real LOLA DEM + OHRC data.
    """

    def __init__(
        self,
        dem_tif_path: str,
        lola_slope_tif_path: str | None = None,
        ohrc_img_path: str | None = None,
        ohrc_img_xml_path: str | None = None,
        ohrc_geo_csv_path: str | None = None,
        pixel_size_m: float | None = None,   # auto-detected from GeoTIFF if None
    ):
        self.dem_tif_path = dem_tif_path
        self.lola_slope_tif_path = lola_slope_tif_path
        self.ohrc_img_path = ohrc_img_path
        self.ohrc_img_xml_path = ohrc_img_xml_path
        self.ohrc_geo_csv_path = ohrc_geo_csv_path
        self.pixel_size_override = pixel_size_m

        # Loaded arrays
        self.dem = None             # 2-D float32, metres
        self.dem_transform = None   # rasterio Affine
        self.dem_crs = None
        self.lola_slope_ref = None  # Reference slope from LOLA (for validation)
        self.ohrc_image = None      # 2-D uint8
        self.ohrc_geometry = None   # structured array
        self.solar_params = None    # dict with solar_azimuth, solar_elevation
        self.pixel_size = 5.0       # metres (LOLA default at 5 m/px)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_data(self):
        """Load ALL real datasets."""

        # 1) LOLA DEM surface elevation
        print(f"[DEM] Loading {os.path.basename(self.dem_tif_path)} …")
        with rasterio.open(self.dem_tif_path) as src:
            self.dem = src.read(1).astype(np.float32)
            self.dem_transform = src.transform
            self.dem_crs = src.crs
            # Derive pixel size from transform if not overridden
            if self.pixel_size_override is not None:
                self.pixel_size = self.pixel_size_override
            else:
                self.pixel_size = abs(src.transform.a)  # metres per pixel
        print(f"[DEM] Shape: {self.dem.shape}, pixel size: {self.pixel_size:.2f} m, "
              f"range: [{np.nanmin(self.dem):.1f}, {np.nanmax(self.dem):.1f}] m")

        # Handle NaN / nodata
        nodata_mask = np.isnan(self.dem)
        if np.any(nodata_mask):
            self.dem[nodata_mask] = np.nanmedian(self.dem)
            print(f"[DEM] Filled {int(np.sum(nodata_mask))} NaN pixels with median.")

        # 2) LOLA Slope (cross-validation)
        if self.lola_slope_tif_path and os.path.exists(self.lola_slope_tif_path):
            print(f"[SLP] Loading reference slope from {os.path.basename(self.lola_slope_tif_path)} …")
            with rasterio.open(self.lola_slope_tif_path) as src:
                self.lola_slope_ref = src.read(1).astype(np.float32)
            print(f"[SLP] Shape: {self.lola_slope_ref.shape}, "
                  f"range: [{np.nanmin(self.lola_slope_ref):.2f}, {np.nanmax(self.lola_slope_ref):.2f}]°")

        # 3) OHRC image (1.2 GB raw binary – memory-map a sub-region)
        if self.ohrc_img_path and os.path.exists(self.ohrc_img_path):
            ohrc_lines = 101075
            ohrc_samples = 12000
            # Parse from XML if available
            if self.ohrc_img_xml_path and os.path.exists(self.ohrc_img_xml_path):
                import xml.etree.ElementTree as ET
                tree = ET.parse(self.ohrc_img_xml_path)
                ns = {"pds": "http://pds.nasa.gov/pds4/pds/v1"}
                for ax in tree.findall(".//{http://pds.nasa.gov/pds4/pds/v1}Axis_Array"):
                    name_el = ax.find("{http://pds.nasa.gov/pds4/pds/v1}axis_name")
                    elem_el = ax.find("{http://pds.nasa.gov/pds4/pds/v1}elements")
                    if name_el is not None and elem_el is not None:
                        if name_el.text == "Line":
                            ohrc_lines = int(elem_el.text)
                        elif name_el.text == "Sample":
                            ohrc_samples = int(elem_el.text)

            print(f"[OHRC] Memory-mapping {os.path.basename(self.ohrc_img_path)} "
                  f"({ohrc_lines}×{ohrc_samples}) …")
            # We downsample by 4× to keep things tractable (~25 Mpx → ~1.5 Mpx)
            ds = 4
            mmap = np.memmap(self.ohrc_img_path, dtype=np.uint8, mode='r',
                             shape=(ohrc_lines, ohrc_samples))
            self.ohrc_image = np.array(mmap[::ds, ::ds])  # copy into RAM (small)
            del mmap
            print(f"[OHRC] Downsampled image shape: {self.ohrc_image.shape}")

        # 4) OHRC geometry CSV
        if self.ohrc_geo_csv_path and os.path.exists(self.ohrc_geo_csv_path):
            print(f"[GEO] Loading OHRC ground-reference from {os.path.basename(self.ohrc_geo_csv_path)} …")
            self.ohrc_geometry = _read_ohrc_geometry_csv(self.ohrc_geo_csv_path, sample_every=50)
            print(f"[GEO] Loaded {len(self.ohrc_geometry)} sampled ground-reference points, "
                  f"lat range: [{self.ohrc_geometry['lat'].min():.4f}, {self.ohrc_geometry['lat'].max():.4f}]°")

        # 5) Solar parameters from OHRC XML metadata (authoritative source)
        if self.ohrc_img_xml_path and os.path.exists(self.ohrc_img_xml_path):
            print(f"[SOL] Extracting solar parameters from {os.path.basename(self.ohrc_img_xml_path)} ...")
            self.solar_params = _parse_solar_from_ohrc_xml(self.ohrc_img_xml_path)
            if self.solar_params:
                print(f"[SOL] Solar elevation={self.solar_params['solar_elevation']:.4f} deg, "
                      f"azimuth={self.solar_params['solar_azimuth']:.4f} deg")
            else:
                print("[SOL] Warning: could not extract solar params from XML.")

    # ------------------------------------------------------------------
    # Terrain computations
    # ------------------------------------------------------------------

    def compute_slope_aspect(self) -> tuple[np.ndarray, np.ndarray]:
        """Compute slope (degrees) and aspect (degrees) from the DEM using Sobel gradients."""
        dz_dx = sobel(self.dem, axis=1) / (8.0 * self.pixel_size)
        dz_dy = sobel(self.dem, axis=0) / (8.0 * self.pixel_size)
        slope_deg = np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)))
        aspect_deg = np.degrees(np.arctan2(-dz_dy, dz_dx)) % 360
        return slope_deg.astype(np.float32), aspect_deg.astype(np.float32)

    def compute_roughness(self, window_m: float = 100.0) -> np.ndarray:
        """RMS height deviation within a local window — standard terrain roughness metric."""
        window_px = max(3, int(window_m / self.pixel_size))
        if window_px % 2 == 0:
            window_px += 1
        mean_z = uniform_filter(self.dem.astype(np.float64), window_px)
        rms_height = np.sqrt(uniform_filter((self.dem - mean_z)**2, window_px))
        return rms_height.astype(np.float32)

    # ------------------------------------------------------------------
    # PSR / DSC detection — illumination model with real solar data
    # ------------------------------------------------------------------

    def detect_psr_dsc(self, slope: np.ndarray, aspect: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Identify Permanently Shadowed Regions (PSR) and Doubly Shadowed Craters (DSC).

        Uses a three-pronged approach on real data:
          a) Topographic depression detection from the DEM.
          b) Self-shadowing via slope + aspect vs actual solar elevation.
          c) Horizon / obstruction analysis (simplified ray model).
        """
        # ---- (a) Topographic depressions ----
        # Compare each pixel to its local neighbourhood mean to find depressions
        local_mean_200 = uniform_filter(self.dem.astype(np.float64), size=max(3, int(200 / self.pixel_size)))
        local_mean_500 = uniform_filter(self.dem.astype(np.float64), size=max(3, int(500 / self.pixel_size)))
        depression_200 = (local_mean_200 - self.dem).astype(np.float32)
        depression_500 = (local_mean_500 - self.dem).astype(np.float32)

        # ---- (b) Solar-illumination self-shadowing ----
        # Use real solar elevation from OHRC XML metadata
        if self.solar_params is not None:
            solar_elev_deg = self.solar_params["solar_elevation"]
            solar_az_deg = self.solar_params["solar_azimuth"]
            print(f"[PSR] Using real solar elevation={solar_elev_deg:.2f} deg, azimuth={solar_az_deg:.2f} deg")
        else:
            # At the lunar south pole, typical grazing angle ~ 1.5 deg
            solar_elev_deg = 1.5
            solar_az_deg = 0.0
            print(f"[PSR] No solar data -- defaulting to polar grazing angle {solar_elev_deg} deg")

        # A surface facet is self-shadowed when the local slope facing away from
        # the sun exceeds the solar elevation angle.
        solar_az_rad = np.radians(solar_az_deg)
        # Component of slope facing the sun
        slope_toward_sun = slope * np.cos(np.radians(aspect) - solar_az_rad)
        self_shadow = slope_toward_sun > solar_elev_deg

        # ---- (c) Horizon obstruction (simplified) ----
        # Pixels deep inside craters have their horizon blocked.
        # We approximate this: if the pixel is >20 m below its 200 m
        # neighbourhood AND slope >10°, it is obstructed.
        horizon_blocked = (depression_200 > 20) & (slope > 10)

        # ---- Combine for PSR ----
        psr_mask = (
            (depression_200 > 15) |          # moderate depression
            (self_shadow & (slope > 8)) |     # self-shadowed steep slopes
            horizon_blocked                   # deep inside crater walls
        ).astype(np.uint8)

        # Clean up noise with morphological operations
        from scipy.ndimage import binary_opening, binary_closing
        struct_elem = np.ones((5, 5))
        psr_mask = binary_closing(psr_mask, structure=struct_elem, iterations=2).astype(np.uint8)
        psr_mask = binary_opening(psr_mask, structure=struct_elem, iterations=1).astype(np.uint8)

        # ---- DSC: innermost permanently dark regions ----
        # These are deep, nested depressions within already-shadowed PSRs
        dsc_mask = (
            (psr_mask == 1) &
            (depression_500 > 40) &    # very deep relative to wide context
            (depression_200 > 30)      # also deep relative to local context
        ).astype(np.uint8)

        # Label connected components and keep only substantial ones
        labeled_psr, n_psr = label(psr_mask)
        labeled_dsc, n_dsc = label(dsc_mask)

        # Filter tiny PSR blobs (< 50 pixels ≈ 1250 m² at 5 m/px)
        min_psr_pixels = max(50, int(1250 / (self.pixel_size**2)))
        for i in range(1, n_psr + 1):
            if np.sum(labeled_psr == i) < min_psr_pixels:
                psr_mask[labeled_psr == i] = 0

        print(f"[PSR] Detected {n_psr} PSR regions, {n_dsc} DSC regions")
        return psr_mask, dsc_mask

    # ------------------------------------------------------------------
    # Hazard map for rover traversability
    # ------------------------------------------------------------------

    def compute_hazard_map(self, slope: np.ndarray, roughness: np.ndarray) -> np.ndarray:
        """
        Fused traversability hazard map (0 = safe, 1 = impassable).
        Thresholds from lunar rover engineering constraints:
          - Slope > 15° → impassable
          - Roughness > 2 m RMS → hazardous
        """
        norm_slope = np.clip(slope / 15.0, 0, 1)
        norm_rough = np.clip(roughness / 2.0, 0, 1)

        hazard = 0.6 * norm_slope + 0.4 * norm_rough
        hazard[slope > 15] = 1.0   # hard exclusion
        return np.clip(hazard, 0, 1).astype(np.float32)

    # ------------------------------------------------------------------
    # Landing-site candidate identification
    # ------------------------------------------------------------------

    def identify_landing_candidates(
        self,
        hazard: np.ndarray,
        slope: np.ndarray,
        psr_mask: np.ndarray,
        n_candidates: int = 5,
        min_flat_radius_m: float = 100.0,
    ) -> list[dict]:
        """
        Find candidate landing sites that are:
          • Flat (slope < 5°)
          • Low hazard (< 0.25)
          • Near a PSR (within 1 km) for scientific interest
          • Large enough contiguous flat area (> min_flat_radius_m)
        """
        flat_mask = (slope < 5.0) & (hazard < 0.25)

        # Dilate PSR to find "near PSR" zones
        proximity_px = max(1, int(1000.0 / self.pixel_size))
        psr_dilated = binary_dilation(psr_mask.astype(bool),
                                       iterations=proximity_px // 5,
                                       structure=np.ones((5, 5)))
        near_psr = psr_dilated & ~psr_mask.astype(bool)

        candidate_mask = flat_mask & near_psr

        # Label and rank connected regions by area
        labeled, n_regions = label(candidate_mask)
        regions = []
        for i in range(1, n_regions + 1):
            area_px = int(np.sum(labeled == i))
            area_m2 = area_px * self.pixel_size**2
            if area_m2 < np.pi * min_flat_radius_m**2:
                continue
            ys, xs = np.where(labeled == i)
            cy, cx = int(np.mean(ys)), int(np.mean(xs))
            mean_slope = float(np.mean(slope[labeled == i]))
            mean_hazard = float(np.mean(hazard[labeled == i]))

            # Georef if available
            if self.dem_transform is not None:
                geo_x, geo_y = rasterio.transform.xy(self.dem_transform, cy, cx)
            else:
                geo_x, geo_y = float(cx), float(cy)

            regions.append({
                "rank": 0,
                "pixel_y": cy, "pixel_x": cx,
                "geo_x": geo_x, "geo_y": geo_y,
                "area_m2": area_m2,
                "mean_slope_deg": round(mean_slope, 2),
                "mean_hazard": round(mean_hazard, 3),
            })

        # Sort by area (larger is better) and take top N
        regions.sort(key=lambda r: r["area_m2"], reverse=True)
        for idx, r in enumerate(regions[:n_candidates]):
            r["rank"] = idx + 1
        return regions[:n_candidates]

    # ------------------------------------------------------------------
    # Cross-validation with LOLA slope product
    # ------------------------------------------------------------------

    def validate_slope(self, computed_slope: np.ndarray) -> dict | None:
        """Compare our Sobel-derived slope against the LOLA reference slope product."""
        if self.lola_slope_ref is None:
            return None
        if computed_slope.shape != self.lola_slope_ref.shape:
            print(f"[VAL] Shape mismatch: computed {computed_slope.shape} vs LOLA {self.lola_slope_ref.shape}")
            return None

        ref = self.lola_slope_ref
        valid = ~(np.isnan(ref) | np.isnan(computed_slope))
        if np.sum(valid) == 0:
            return None

        diff = computed_slope[valid] - ref[valid]
        metrics = {
            "mean_abs_error_deg": round(float(np.mean(np.abs(diff))), 4),
            "rmse_deg": round(float(np.sqrt(np.mean(diff**2))), 4),
            "correlation": round(float(np.corrcoef(computed_slope[valid], ref[valid])[0, 1]), 4),
            "n_valid_pixels": int(np.sum(valid)),
        }
        print(f"[VAL] Slope validation: MAE={metrics['mean_abs_error_deg']}°, "
              f"RMSE={metrics['rmse_deg']}°, r={metrics['correlation']}")
        return metrics

    # ------------------------------------------------------------------
    # Master pipeline
    # ------------------------------------------------------------------

    def process_all(self, output_dir: str) -> dict:
        """Run the full end-to-end pipeline and persist all products."""

        self.load_data()

        print("\n— Computing slope and aspect …")
        slope, aspect = self.compute_slope_aspect()

        print("— Computing terrain roughness …")
        roughness = self.compute_roughness()

        print("— Detecting PSR / DSC …")
        psr_mask, dsc_mask = self.detect_psr_dsc(slope, aspect)

        print("— Generating hazard map …")
        hazard = self.compute_hazard_map(slope, roughness)

        print("— Identifying landing site candidates …")
        candidates = self.identify_landing_candidates(hazard, slope, psr_mask)

        print("— Cross-validating slope …")
        validation = self.validate_slope(slope)

        # ---- Persist outputs ----
        os.makedirs(output_dir, exist_ok=True)

        np.save(os.path.join(output_dir, "slope.npy"), slope)
        np.save(os.path.join(output_dir, "roughness.npy"), roughness)
        np.save(os.path.join(output_dir, "psr_mask.npy"), psr_mask)
        np.save(os.path.join(output_dir, "dsc_mask.npy"), dsc_mask)
        np.save(os.path.join(output_dir, "hazard.npy"), hazard)
        np.save(os.path.join(output_dir, "dem_elevation.npy"), self.dem)

        if self.lola_slope_ref is not None:
            np.save(os.path.join(output_dir, "lola_slope_validated.npy"), self.lola_slope_ref)

        if self.ohrc_image is not None:
            np.save(os.path.join(output_dir, "ohrc_base.npy"), self.ohrc_image)

        with open(os.path.join(output_dir, "landing_candidates.json"), "w") as f:
            json.dump(candidates, f, indent=2)

        # Assemble stats
        stats = {
            "dem_shape": list(self.dem.shape),
            "pixel_size_m": self.pixel_size,
            "elevation_range_m": [float(np.nanmin(self.dem)), float(np.nanmax(self.dem))],
            "max_slope_deg": float(np.nanmax(slope)),
            "mean_slope_deg": float(np.nanmean(slope)),
            "mean_roughness_m": float(np.nanmean(roughness)),
            "psr_area_pixels": int(np.sum(psr_mask)),
            "psr_area_km2": round(int(np.sum(psr_mask)) * self.pixel_size**2 / 1e6, 4),
            "dsc_area_pixels": int(np.sum(dsc_mask)),
            "dsc_area_km2": round(int(np.sum(dsc_mask)) * self.pixel_size**2 / 1e6, 4),
            "n_landing_candidates": len(candidates),
            "landing_candidates": candidates,
            "slope_validation": validation,
            "data_sources": {
                "dem": os.path.basename(self.dem_tif_path),
                "lola_slope": os.path.basename(self.lola_slope_tif_path) if self.lola_slope_tif_path else None,
                "ohrc_image": os.path.basename(self.ohrc_img_path) if self.ohrc_img_path else None,
                "ohrc_geometry": os.path.basename(self.ohrc_geo_csv_path) if self.ohrc_geo_csv_path else None,
                "solar_params": os.path.basename(self.ohrc_img_xml_path) if self.ohrc_img_xml_path else None,
            },
        }

        # Solar context
        if self.solar_params is not None:
            stats["solar_elevation_deg"] = round(
                float(self.solar_params["solar_elevation"]), 4)
            stats["solar_azimuth_deg"] = round(
                float(self.solar_params["solar_azimuth"]), 4)

        # Geo-extent from OHRC geometry
        if self.ohrc_geometry is not None and len(self.ohrc_geometry) > 0:
            stats["ohrc_extent"] = {
                "lat_min": round(float(self.ohrc_geometry["lat"].min()), 6),
                "lat_max": round(float(self.ohrc_geometry["lat"].max()), 6),
                "lon_min": round(float(self.ohrc_geometry["lon"].min()), 6),
                "lon_max": round(float(self.ohrc_geometry["lon"].max()), 6),
            }

        with open(os.path.join(output_dir, "metadata.json"), "w") as f:
            json.dump(stats, f, indent=2)

        print(f"\n[OK] All products written to {output_dir}")
        print(json.dumps(stats, indent=2))
        return stats


# ---------------------------------------------------------------------------
# Standalone entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset = os.path.join(base_dir, "dataset demo")

    engine = PSRAnalysisEngine(
        dem_tif_path=os.path.join(dataset, "Lola DEM", "SITE1", "Site01_final_adj_5mpp_surf.tif"),
        lola_slope_tif_path=os.path.join(dataset, "Lola DEM", "SITE1", "Site01_final_adj_5mpp_slp.tif"),
        ohrc_img_path=os.path.join(dataset, "ohrc", "data", "calibrated", "20260103",
                                    "ch2_ohr_ncp_20260103T1005176450_d_img_d18.img"),
        ohrc_img_xml_path=os.path.join(dataset, "ohrc", "data", "calibrated", "20260103",
                                        "ch2_ohr_ncp_20260103T1005176450_d_img_d18.xml"),
        ohrc_geo_csv_path=os.path.join(dataset, "ohrc", "geometry", "calibrated", "20260103",
                                        "ch2_ohr_ncp_20260103T1005176450_g_grd_d18.csv"),
    )

    stats = engine.process_all(os.path.join(base_dir, "engines", "output"))
