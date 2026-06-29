# POLARIS — Polar Ice Analytics & Rover Intelligence System
## Complete Implementation Blueprint | BAH 2026 | Problem Statement 8
### Chandrayaan-2 Subsurface Ice Detection & Exploration Intelligence Platform

---

## EXECUTIVE SUMMARY

**Solution Name:** POLARIS — Polar Ice Analytics & Rover Intelligence System
**Tagline:** *From Radar Shadows to Rover Roads — AI-Powered Lunar Ice Intelligence*
**Team:** Antariksh | BAH 2026

**Core Value Proposition:**
POLARIS transforms raw Chandrayaan-2 DFSAR radar and OHRC imagery data into a complete, scientifically rigorous, actionable exploration intelligence platform — covering ice detection, landing site selection, rover path planning, and ice volume quantification in a single production-grade interface that sets a new bar for hackathon planetary science applications.

**Why POLARIS Wins:**
- Deep domain alignment: Full polarimetric pipeline (CPR, DOP, m-chi decomposition) matching published lunar ice science
- Visual superiority: 3D CesiumJS terrain with real-time radar overlays and rover animation
- Operational realism: Energy-aware rover traversal with solar budget tracking
- Scientific rigor: Uncertainty quantification on every estimate, not just point values
- ISRO relevance: ISRU water/propellant potential scoring directly tied to mission planning

---

## SECTION 1: PROBLEM STATEMENT ANALYSIS

### 1.1 Objective Decomposition

| Objective | Priority | Complexity | POLARIS Module |
|-----------|----------|------------|---------------|
| Map PSRs and doubly shadowed craters | Critical | High | PSR Illumination Mapper |
| Compute CPR / DOP radar parameters | Critical | High | DFSAR Polarimetry Engine |
| Distinguish ice vs rocky terrain | Critical | Very High | AI Ice Classifier |
| Terrain morphology from OHRC | High | Medium | Terrain Morphology Analyzer |
| Propose optimal landing site | Critical | High | Landing Site Selector |
| Design optimal rover traverse | Critical | High | Rover Path Planner |
| Estimate ice volume (top 5m) | Critical | High | Ice Volume Estimator |

### 1.2 Stakeholder Map

| Stakeholder | Role | What They Need | POLARIS Response |
|-------------|------|---------------|-----------------|
| ISRO Scientists | End users | Scientific ice detection accuracy | m-chi + CPR + DOP fusion, published thresholds |
| Mission Planners | Decision makers | Safe landing, feasible traverse | Multi-criteria scoring, energy-aware A* |
| Hackathon Judges | Evaluators | Technical depth + visual excellence | Full pipeline + 3D visualization |
| Future Crew | Beneficiaries | ISRU water/O2/propellant potential | Volume → ISRU potential score |

### 1.3 Requirement Traceability Matrix

| PS8 Requirement | Source | POLARIS Module | Deliverable |
|-----------------|--------|---------------|-------------|
| Map PSRs + doubly shadowed craters | Obj 1 | PSR Mapper | PSR boundary map + DSC catalog |
| Radar polarimetric signatures for ice | Obj 2 | DFSAR Engine | CPR + DOP + m-chi maps |
| Distinguish ice from rough rock | Obj 2 | AI Classifier | Ice probability heatmap |
| Terrain safety for landing | Obj 3 | Terrain Analyzer | Hazard map (slope, boulders) |
| Scientifically viable landing site | Obj 3 | Site Selector | Top-3 ranked sites + MCDA breakdown |
| Optimal rover traverse | Obj 4 | Path Planner | Optimal path + energy profile |
| Ice volume estimation (0–5m) | Obj 5 | Volume Estimator | Volume m³ ± uncertainty |
| DFSAR data processing | Dataset | DFSAR Engine | Calibrated, terrain-corrected products |
| OHRC imagery analysis | Dataset | Terrain Analyzer | Morphology + boulder density maps |

### 1.4 Evaluation Criterion Mapping

| Evaluation Parameter | Judge Weight | POLARIS Strength |
|---------------------|-------------|-----------------|
| Scientific robustness of ice detection | Very High | Full m-chi decomposition + CPR+DOP dual criterion |
| Accuracy and clarity of data analysis | High | Uncertainty quantification + SHAP explainability |
| Feasibility of landing site | High | MCDA with 5 weighted safety/science criteria |
| Efficiency/safety of rover traverse | High | Energy-aware A* with solar budget constraints |
| Innovation in methodology | High | Bayesian uncertainty + multi-frequency depth model |
| Clarity of presentation | High | Production-grade 3D dark UI + animated demos |

### 1.5 Key Scientific Constraints

- PSR definition: Annual Illumination Fraction (AIF) < 0.1%
- Doubly shadowed crater: nested inside PSR, with crater rim creating secondary shadow even to scattered light
- Ice signature: CPR > 1.0 AND DOP < 0.13 (distinguishes from rough rocky terrain where CPR > 1 but DOP > 0.13)
- Radar penetration depth: ~5–30m at S-band through ice-bearing regolith
- Rover slope constraint: max 15° for safe traverse
- Solar power: minimum 30% illumination fraction at landing site

---

## SECTION 2: COMPLETE DELIVERABLES BREAKDOWN

---

### MODULE 1: PSR ILLUMINATION MAPPER

#### Purpose
Establish the spatial prior for ice detection by computing which regions are thermally cold enough to preserve volatiles over geological timescales. This is the scientific foundation layer — without accurate PSR mapping, the ice detection pipeline has no spatial context.

#### Inputs
- LOLA DEM (Lunar Orbiter Laser Altimeter) — 118m/pixel regional, 30m/pixel local
- Computed solar positions across full lunar year (12 lunations × 360° azimuth)
- OHRC imagery for crater rim identification (25 cm/pixel)

#### Processing
```
Step 1: Load DEM → compute surface normal vectors at each pixel
Step 2: For each solar position (az, el pair in annual ephemeris):
    → Cast ray from Sun to each pixel
    → If ray intersects terrain before reaching pixel: shadow = True
    → Accumulate illumination count map
Step 3: Annual Illumination Fraction (AIF) = illuminated_count / total_solar_positions
Step 4: PSR = pixels where AIF < 0.001 (< 0.1%)
Step 5: Doubly shadowed craters:
    → Find craters that lie entirely within PSR mask
    → Compute crater-local horizon elevation angles
    → DSC confirmed if even scattered/secondary illumination blocked by rim height
Step 6: Assign temperature proxy: T_PSR ~ 40–100K (from illumination model)
```

#### Algorithm Detail
```python
import numpy as np
from scipy.ndimage import label, binary_erosion

def horizon_shadow_cast(dem, sun_az_deg, sun_el_deg, pixel_size_m):
    """
    Efficient horizon-angle shadow casting on DEM grid.
    Returns binary shadow map for single solar position.
    """
    rows, cols = dem.shape
    shadow = np.zeros((rows, cols), dtype=bool)
    
    az_rad = np.radians(sun_az_deg)
    dx = np.cos(az_rad)
    dy = np.sin(az_rad)
    tan_el = np.tan(np.radians(sun_el_deg))
    
    # March rays across DEM in solar direction
    for start_r in range(rows):
        for start_c in range(cols):
            x, y = float(start_c), float(start_r)
            z0 = dem[start_r, start_c]
            
            while 0 <= int(y) < rows and 0 <= int(x) < cols:
                x += dx; y += dy
                if not (0 <= int(y) < rows and 0 <= int(x) < cols):
                    break
                dist = np.sqrt((x - start_c)**2 + (y - start_r)**2) * pixel_size_m
                required_height = z0 + dist * tan_el
                if dem[int(y), int(x)] > required_height:
                    shadow[start_r, start_c] = True
                    break
    
    return shadow

def identify_doubly_shadowed_craters(psr_mask, dem, crater_catalog):
    """
    Find craters nested inside PSRs where even reflected light is blocked.
    Doubly shadowed = zero direct AND zero secondary illumination.
    """
    doubly_shadowed = []
    for crater in crater_catalog:
        cy, cx = crater.center_pixel
        if not psr_mask[cy, cx]:
            continue
        # Check rim-to-floor line of sight at all azimuths
        rim_heights = []
        for az in range(0, 360, 5):
            rim_heights.append(sample_rim_height(dem, cx, cy, az, crater.radius_px))
        min_horizon_el = np.degrees(np.arctan(
            np.min(rim_heights) / (crater.radius_px * 30)  # pixel_size=30m
        ))
        if min_horizon_el < 0.5:  # Rim fully blocks scattered light
            crater.doubly_shadowed = True
            doubly_shadowed.append(crater)
    return doubly_shadowed
```

#### Outputs
- Annual Illumination Map (0–100%, GeoTIFF, exportable)
- PSR Mask (binary, GeoTIFF)
- Doubly Shadowed Crater (DSC) catalog: {id, lat, lon, area_km², depth_m, min_temp_K}
- Illumination confidence map

#### Tech Stack
- Python: NumPy, SciPy, GDAL, Rasterio
- GDAL for DEM warping and reprojection
- Matplotlib/Cartopy for 2D illumination outputs
- CesiumJS for 3D terrain with PSR overlay

---

### MODULE 2: DFSAR POLARIMETRY ENGINE

#### Purpose
The scientific core of POLARIS. Process Chandrayaan-2 DFSAR Single Look Complex (SLC) data to extract the polarimetric parameters that unambiguously distinguish subsurface ice from rough rocky terrain — the distinction that defines whether CPR > 1 is ice or surface roughness.

#### Inputs
- Chandrayaan-2 DFSAR SLC data: S-band (2.5 GHz, λ=12cm) and L-band (610 MHz, λ=49cm)
- Polarimetric calibration matrices from DFSAR metadata
- OHRC co-registered for validation

#### Processing Pipeline

**Stage 1 — Radiometric Calibration**
- Convert raw digital numbers to β⁰ (beta-naught) using calibration constant K
- Apply noise floor correction
- σ⁰ = β⁰ × sin(θ_incidence)

**Stage 2 — Geometric Correction**
- Terrain-corrected product using LOLA DEM
- Range-Doppler terrain correction (RD-TC)
- Register to geographic coordinates (WGS84 / MOON_ME)

**Stage 3 — Speckle Reduction**
- Multi-look processing: 3×3 to 7×7 boxcar filter
- Refined Lee filter for edge preservation

**Stage 4 — Polarimetric Parameter Extraction**

```python
import numpy as np
from scipy.ndimage import uniform_filter

class DFSARPolarimetryEngine:
    """
    Complete Chandrayaan-2 DFSAR Polarimetric Processor.
    Computes CPR, DOP, and m-chi decomposition for lunar ice detection.
    """
    
    def __init__(self, slc_data: dict, wavelength_m: float, window_size: int = 5):
        self.slc = slc_data  # Keys: 'HH', 'HV', 'VH', 'VV' as complex arrays
        self.lam = wavelength_m
        self.w = window_size
    
    def _boxcar(self, arr):
        """Boxcar speckle filter."""
        return uniform_filter(arr.real, self.w) + 1j * uniform_filter(arr.imag, self.w)
    
    def compute_covariance_matrix(self):
        """
        3x3 Coherency matrix [T] from Pauli decomposition.
        k_P = [SHH+SVV, SHH-SVV, 2SHV]^T / sqrt(2)
        """
        SHH = self.slc['HH']
        SHV = self.slc['HV']
        SVV = self.slc['VV']
        
        k1 = (SHH + SVV) / np.sqrt(2)
        k2 = (SHH - SVV) / np.sqrt(2)
        k3 = np.sqrt(2) * SHV
        
        k = np.stack([k1, k2, k3], axis=0)
        T = np.zeros((*SHH.shape, 3, 3), dtype=complex)
        
        for i in range(3):
            for j in range(3):
                product = k[i] * np.conj(k[j])
                T[..., i, j] = uniform_filter(product.real, self.w) + \
                               1j * uniform_filter(product.imag, self.w)
        return T
    
    def compute_cpr(self):
        """
        Circular Polarization Ratio.
        CPR = P_SC / P_OC
        For lunar ice: CPR > 1.0 (coherent backscatter enhancement).
        For rough terrain: CPR > 1.0 but DOP > 0.13.
        """
        # Convert from linear to circular basis
        SRR = (self.slc['HH'] - self.slc['VV'] + 2j * self.slc['HV']) / 2
        SRL = (self.slc['HH'] + self.slc['VV']) / 2
        
        P_sc = uniform_filter(np.abs(SRR)**2, self.w)  # Same-sense circular
        P_oc = uniform_filter(np.abs(SRL)**2, self.w)  # Opposite-sense circular
        
        return P_sc / (P_oc + 1e-12)
    
    def compute_dop(self, T):
        """
        Degree of Polarization.
        DOP = sqrt(1 - 27*det([T]) / trace([T])^3)
        
        Ice-rich: DOP < 0.13 (high volume scattering → depolarization)
        Rocky:    DOP > 0.40 (surface scattering → polarization preserved)
        """
        det_T = (T[...,0,0]*T[...,1,1]*T[...,2,2]
                 - T[...,0,0]*T[...,1,2]*T[...,2,1]
                 - T[...,0,1]*T[...,1,0]*T[...,2,2]
                 + T[...,0,1]*T[...,1,2]*T[...,2,0]
                 + T[...,0,2]*T[...,1,0]*T[...,2,1]
                 - T[...,0,2]*T[...,1,1]*T[...,2,0])
        
        trace_T = T[...,0,0] + T[...,1,1] + T[...,2,2]
        
        return np.real(np.sqrt(np.clip(
            1.0 - 27.0 * np.abs(det_T) / (np.abs(trace_T)**3 + 1e-12), 0, 1
        )))
    
    def mchi_decomposition(self, T):
        """
        Raney m-chi (m-χ) decomposition for lunar applications.
        
        Returns:
            - volume: Ice-like volume scattering component (blue)
            - double_bounce: Dihedral / double-bounce (red)
            - surface: Bragg surface scattering (green)
        
        Reference: Raney et al. 2012, Stacy & Campbell 2018
        """
        T11 = T[...,0,0].real
        
        # Degree of polarization m (from Stokes parameters)
        S0 = T[...,0,0].real + T[...,1,1].real
        S1 = T[...,0,0].real - T[...,1,1].real
        S2 = 2 * T[...,0,1].real
        S3 = -2 * T[...,0,1].imag  # Stokes V
        
        m = np.sqrt(S1**2 + S2**2 + S3**2) / (S0 + 1e-12)
        chi = 0.5 * np.arcsin(np.clip(S3 / (m * S0 + 1e-12), -1, 1))  # Ellipticity
        
        volume    = m * (1 - np.abs(np.sin(chi))) * T11 / 2  # Ice → high volume
        double_bn = m * (1 + np.sin(chi)) * T11 / 4           # Rock dihedral
        surface   = m * (1 - np.sin(chi)) * T11 / 4           # Bragg surface
        
        return {'volume': volume, 'double_bounce': double_bn, 'surface': surface}
    
    def ice_probability_score(self, cpr, dop, mchi):
        """
        Fused ice probability: combines all polarimetric evidence.
        
        Criteria (from published lunar ice literature):
        - CPR > 1.0: necessary condition
        - DOP < 0.13: removes rough-terrain false positives
        - High volume / total in m-chi: confirms ice-like scattering
        """
        cpr_score  = np.clip((cpr - 1.0) / 1.5, 0, 1)           # normalized CPR excess
        dop_score  = np.clip((0.13 - dop) / 0.13, 0, 1)          # low DOP = ice
        vol_frac   = mchi['volume'] / (
            mchi['volume'] + mchi['double_bounce'] + mchi['surface'] + 1e-12)
        
        # Weighted fusion
        ice_score = 0.40 * cpr_score + 0.35 * dop_score + 0.25 * vol_frac
        
        # Apply hard constraints
        ice_prob = np.where((cpr > 1.0) & (dop < 0.13), ice_score, ice_score * 0.15)
        
        return np.clip(ice_prob, 0, 1)
```

**Stage 5 — Multi-Frequency Depth Profiling (S + L band)**
- S-band (12cm): higher resolution, shallower penetration (~5–10m in regolith)
- L-band (49cm): coarser resolution, deeper penetration (~15–30m)
- Frequency ratio (CPR_Sband / CPR_Lband) indicates ice depth distribution
- If both bands show CPR > 1: ice distributed from surface to deep
- If only L-band: ice is deep (>5m), below S-band sensitivity

#### Outputs
- CPR Map (GeoTIFF, 0–3+ scale, color-coded)
- DOP Map (GeoTIFF, 0–1 scale)
- m-chi RGB Composite (Volume=Blue, Double=Red, Surface=Green)
- Ice Probability Map (0–1, exported as GeoTIFF + PNG)
- Processing statistics JSON (mean CPR, max CPR, DOP thresholds, ice_area_km²)

#### Tech Stack
- Python: NumPy, SciPy, GDAL, h5py (DFSAR HDF5)
- MIDAS (DFSAR-specific processing tool per PS8 recommendation)
- SNAP (ESA Sentinel Application Platform — SAR calibration workflows)
- Rasterio for GeoTIFF I/O

---

### MODULE 3: TERRAIN MORPHOLOGY ANALYZER

#### Purpose
Characterize the crater and surrounding terrain from OHRC imagery and DEM to: (a) confirm doubly shadowed status via morphology, (b) assess traversability for path planning, (c) detect boulders that are landing hazards.

#### Inputs
- OHRC imagery (25 cm/pixel optical)
- LOLA DEM or OHRC-derived DEM
- Doubly shadowed crater centroids from Module 1

#### Processing

**3a — Slope and Aspect (from DEM)**
```python
from scipy.ndimage import sobel

def compute_slope_aspect(dem, pixel_size_m):
    """
    Compute slope (degrees) and aspect from DEM using gradient method.
    """
    dz_dx = sobel(dem, axis=1) / (8 * pixel_size_m)
    dz_dy = sobel(dem, axis=0) / (8 * pixel_size_m)
    
    slope_deg = np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)))
    aspect_deg = np.degrees(np.arctan2(-dz_dy, dz_dx)) % 360
    
    return slope_deg, aspect_deg
```

**3b — Surface Roughness (RMS Height + Hurst Exponent)**
```python
def compute_roughness(dem, window_m=100, pixel_size_m=30):
    window_px = int(window_m / pixel_size_m)
    
    # RMS height deviation
    mean_z = uniform_filter(dem.astype(float), window_px)
    rms_height = np.sqrt(uniform_filter((dem - mean_z)**2, window_px))
    
    return rms_height  # Units: meters
```

**3c — Boulder Detection (CNN on OHRC)**
- Architecture: Modified ResNet-50 pretrained on LRO NAC boulder datasets
- Input: 512×512 OHRC tiles at 25cm/pixel
- Output: Boulder centroids + estimated diameter
- Post-processing: Morphological closing + NMS suppression
- Boulder density map: boulders per km² (smoothed with Gaussian kernel)

**3d — Crater Morphometry**
```python
def analyze_crater_morphology(dem, crater):
    """
    Key metrics: depth, diameter, D/d ratio, rim height profile, floor flatness.
    """
    cx, cy = crater.center_pixel
    r = crater.radius_px
    
    # Extract cross-sections at 8 azimuths
    floor_z = dem[cy-r//3:cy+r//3, cx-r//3:cx+r//3].mean()
    
    rim_z_values = []
    for az in range(0, 360, 45):
        rim_x = int(cx + r * np.cos(np.radians(az)))
        rim_y = int(cy + r * np.sin(np.radians(az)))
        rim_z_values.append(dem[rim_y, rim_x])
    
    rim_z = np.mean(rim_z_values)
    depth_m = rim_z - floor_z
    diameter_m = 2 * r * 30  # assuming 30m/pixel
    
    return {
        'depth_m': depth_m,
        'diameter_m': diameter_m,
        'depth_diameter_ratio': depth_m / diameter_m,  # ~0.2 fresh, ~0.1 degraded
        'rim_height_m': rim_z,
        'floor_slope_deg': compute_slope_aspect(
            dem[cy-r//3:cy+r//3, cx-r//3:cx+r//3], 30)[0].mean()
    }
```

**3e — Combined Terrain Hazard Map**
```
Hazard Score = 0.40 × normalize(slope) +
               0.35 × normalize(boulder_density) +
               0.25 × normalize(roughness_rms)

Hard exclusions: slope > 15° → hazard = 1.0 (no traverse/landing)
                 boulder > 1m within 50m → landing_hazard += 0.5
```

#### Outputs
- Slope map (degrees), Aspect map — GeoTIFF
- Roughness map (RMS height in cm) — GeoTIFF
- Boulder density map (count/km²) — GeoTIFF
- Terrain hazard composite map (0–1) — GeoTIFF
- Crater morphology report JSON

---

### MODULE 4: AI ICE DETECTION ENGINE

#### Purpose
Fuse all evidence layers — radar polarimetry, terrain morphology, spatial priors (PSR), thermal context — into a unified, explainable ice probability map with confidence intervals. This is the flagship AI module of POLARIS.

#### Model Architecture

**Primary Model: Gradient Boosting Ensemble (demo-reliable, fast)**
```python
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
import shap

# Feature vector per pixel (10 features)
FEATURE_NAMES = [
    'cpr',                    # Circular Polarization Ratio
    'dop',                    # Degree of Polarization
    'mchi_volume_frac',       # m-chi volume fraction (ice scattering)
    'mchi_doublebounce_frac', # m-chi double-bounce fraction
    'slope_deg',              # Terrain slope
    'roughness_rms_cm',       # Surface roughness
    'in_psr',                 # Binary: within PSR
    'in_dsc',                 # Binary: within doubly shadowed crater
    'crater_depth_m',         # Local crater depth (0 outside craters)
    'thermal_stability'       # Proxy: 1/AIF (higher = more thermally stable)
]

# Training strategy: use published CPR/DOP signatures from
# Cabeus, Haworth, Shackleton PSRs as positive class,
# non-PSR S-band bright surfaces as negative class
base_model = GradientBoostingClassifier(
    n_estimators=300, max_depth=5, learning_rate=0.04,
    subsample=0.8, random_state=42
)
# Calibrate probabilities (Platt scaling)
ice_classifier = CalibratedClassifierCV(base_model, method='sigmoid', cv=5)

# SHAP explainability
explainer = shap.TreeExplainer(ice_classifier.base_estimator)
```

**Secondary Model: CNN Patch Classifier (production quality)**
```
Architecture: EfficientNet-B0 modified for 8-channel input
Input:  64×64 patches × 8 channels (CPR, DOP, m-chi×3, slope, roughness, PSR)
Output: [ice_prob, roughness_prob, smooth_prob] + MC Dropout uncertainty

Training data strategy:
- Positive class: Published CPR > 1, DOP < 0.13 patches from Cabeus
- Negative class: Non-PSR surface patches, rough terrain patches
- Augmentation: rotational (lunar surface is rotation-invariant), noise injection

MC Dropout (20 forward passes) → σ_pred = uncertainty heatmap
```

**Bayesian Posterior Ice Map (for final output)**
```
P(ice | features) = P(features | ice) × P(ice in PSR) / P(features)

Prior P(ice in PSR) = 0.30  (literature: ~30% of PSR area has ice signatures)
Prior P(ice outside PSR) = 0.01

Posterior = weighted ensemble of GB + CNN + Bayesian prior
```

#### Explainability Layer (SHAP)
```python
def generate_ice_explanation(pixel_features):
    """
    For each classified pixel, explain WHY it was classified as ice.
    Output sentence for UI: "Ice detected because CPR=1.45 (↑89%), DOP=0.09 (↑72%),
    within doubly shadowed crater (↑65%). Slope=3.2° (safe)."
    """
    shap_vals = explainer.shap_values(pixel_features)
    
    feature_contributions = sorted(
        zip(FEATURE_NAMES, shap_vals[1]),
        key=lambda x: abs(x[1]), reverse=True
    )
    
    explanation_lines = []
    for feat, contribution in feature_contributions[:4]:
        direction = "↑" if contribution > 0 else "↓"
        explanation_lines.append(
            f"{feat.upper()}={pixel_features[feat]:.2f} "
            f"({direction}{abs(contribution)*100:.0f}%)"
        )
    
    return " | ".join(explanation_lines)
```

#### Outputs
- Ice Probability Map (0–1, GeoTIFF + interactive overlay)
- Uncertainty Map (σ from MC Dropout, same resolution)
- High-Confidence Ice Region Polygons (shapefile/GeoJSON)
- SHAP Feature Importance Chart (per-pixel explainability)
- Summary statistics: total ice area km², mean confidence, top-3 hotspot coords

---

### MODULE 5: LANDING SITE SELECTOR

#### Purpose
Identify the optimal 100m×100m landing ellipse near the doubly shadowed crater — balancing scientific access (proximity to ice) with operational safety (terrain, power, communications).

#### Multi-Criteria Decision Analysis (MCDA) Framework

```python
import numpy as np
from scipy.ndimage import gaussian_filter

CRITERIA = {
    'ice_proximity':      {'weight': 0.25, 'type': 'benefit'},  # Mean ice score in 2km radius
    'terrain_safety':     {'weight': 0.30, 'type': 'benefit'},  # Slope/roughness/boulder inverse hazard
    'solar_illumination': {'weight': 0.20, 'type': 'benefit'},  # % time illuminated
    'dsc_access':         {'weight': 0.15, 'type': 'benefit'},  # 1 / distance_to_DSC
    'comm_los':           {'weight': 0.10, 'type': 'benefit'},  # Earth visibility fraction
}

def score_candidate_sites(candidate_grid, maps):
    """
    Score each candidate 100m×100m site on 5 criteria.
    Normalize to [0,1] and compute weighted sum.
    """
    scores = {}
    
    for site_id, (row, col) in enumerate(candidate_grid):
        r_km = 2000 // 30  # 2km radius in pixels (30m/pixel)
        
        # 1. Ice Proximity (mean ice probability in 2km radius)
        local_ice = maps['ice_prob'][
            max(0,row-r_km):row+r_km, max(0,col-r_km):col+r_km
        ]
        ice_prox = local_ice.mean()
        
        # 2. Terrain Safety (1 - hazard score at site, 5×5 pixel window)
        local_hazard = maps['hazard'][row-2:row+2, col-2:col+2].mean()
        terrain_safety = 1.0 - local_hazard
        
        # 3. Solar Illumination (from illumination model)
        solar = maps['illumination'][row, col]  # fraction 0-1
        
        # 4. DSC Access (inverse distance to nearest DSC)
        dist_pixels = np.min([
            np.sqrt((row - dsc.cy)**2 + (col - dsc.cx)**2)
            for dsc in maps['dsc_catalog']
        ])
        dsc_access = 1.0 / (1.0 + dist_pixels * 0.03)  # km normalization
        
        # 5. Communications LoS (Earth visibility, simplified)
        lat = maps['lat_grid'][row, col]
        # Earth visible from lunar south pole when |lat| > 85° and elevation > 0
        comm_los = 0.5 + 0.5 * np.clip((abs(lat) - 85) / 5, 0, 1)
        
        # TOPSIS-style composite scoring
        weighted_score = (
            CRITERIA['ice_proximity']['weight']      * ice_prox +
            CRITERIA['terrain_safety']['weight']     * terrain_safety +
            CRITERIA['solar_illumination']['weight'] * solar +
            CRITERIA['dsc_access']['weight']         * dsc_access +
            CRITERIA['comm_los']['weight']           * comm_los
        )
        
        scores[site_id] = {
            'composite': weighted_score,
            'breakdown': {
                'ice_proximity': ice_prox,
                'terrain_safety': terrain_safety,
                'solar_illumination': solar,
                'dsc_access': dsc_access,
                'comm_los': comm_los
            },
            'lat': maps['lat_grid'][row, col],
            'lon': maps['lon_grid'][row, col],
            'row': row, 'col': col
        }
    
    # Return top-3 ranked sites
    return sorted(scores.values(), key=lambda x: x['composite'], reverse=True)[:3]
```

#### Landing Site Risk Matrix
Each candidate site also gets a 2×2 risk matrix (likelihood × impact) for:
- Soft landing failure risk (terrain roughness / slope)
- Power failure risk (illumination loss events)
- Scientific access risk (DSC blocked by boulder)
- Communication blackout risk (Earth horizon loss)

#### Outputs
- Top-3 ranked landing sites (lat/lon + composite score)
- Per-criterion score breakdown (radar chart visualization)
- Risk matrix per site
- "Exclusion zones" overlay (slope > 15°, boulder field, deep shadow)
- Recommended primary + backup landing sites with narrative justification

---

### MODULE 6: ROVER TRAVERSE PATH PLANNER

#### Purpose
Generate the safest, most energy-efficient path from the landing site to the doubly shadowed crater, accounting for terrain hazards, power constraints, and time of traverse.

#### Algorithm Stack (3 levels)

**Level 1 — Global Path: Weighted A* on Cost Grid**
```python
import heapq
import numpy as np

def build_cost_map(slope_map, roughness_map, boulder_map, illumination_map, pixel_size_m=30):
    """
    Per-pixel traversal cost for rover.
    Combines energy, safety, and solar power into unified cost surface.
    """
    # Energy cost: power ∝ slope (rover motor model)
    energy = 1.0 + 8.0 * np.sin(np.radians(slope_map))
    
    # Safety penalty: hard barriers + soft penalties
    safety_penalty = np.zeros_like(slope_map)
    safety_penalty[slope_map > 15] = 1e6       # Absolute exclusion
    safety_penalty[slope_map > 10] += 50        # Steep slope penalty
    safety_penalty += boulder_map * 30          # Boulder avoidance
    safety_penalty += roughness_map * 0.1       # Roughness friction

    # Solar bonus: prefer illuminated regions (recharging potential)
    solar_bonus = -0.5 * illumination_map       # Negative = reward

    cost_map = energy + safety_penalty + solar_bonus
    cost_map = np.clip(cost_map, 1.0, 1e6)
    return cost_map

def weighted_astar(cost_map, start, goal, w=1.5):
    """
    Weighted A* (w=1.5 for speed, closer to optimal than Dijkstra's).
    Heuristic: Euclidean distance × w × min_cost
    """
    rows, cols = cost_map.shape
    min_cost = cost_map[cost_map < 1e5].min()
    
    def h(pos):
        return w * min_cost * np.sqrt((pos[0]-goal[0])**2 + (pos[1]-goal[1])**2)
    
    open_heap = [(h(start), 0, start)]
    came_from = {start: None}
    g_score = {start: 0}
    closed = set()
    
    neighbors = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    diag_factor = [1,1,1,1,np.sqrt(2)]*4
    
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

def smooth_path_rdp(path, epsilon=2.0):
    """Ramer-Douglas-Peucker path simplification."""
    if len(path) < 3:
        return path
    # Find point with max perpendicular distance from line start-end
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
```

**Level 2 — Path Smoothing**
- RDP simplification: reduce waypoints while preserving key turns
- Bezier spline interpolation for realistic rover kinematics

**Level 3 — Energy & Solar Budget Analysis**
```python
def compute_energy_profile(path, cost_map, illumination_map, rover_spec):
    """
    Track cumulative energy consumption and solar charging along path.
    Ensures battery never drops below 20% reserve capacity.
    """
    battery = rover_spec['battery_wh']  # e.g., 500 Wh
    max_battery = rover_spec['battery_wh']
    solar_power_w = rover_spec['solar_panel_w']  # e.g., 150W
    consumption_w = rover_spec['drive_power_w']  # e.g., 100W base + slope penalty
    
    profile = []
    for i, (r, c) in enumerate(path):
        slope = slope_map[r, c]
        drive_watts = consumption_w + consumption_w * 2 * np.sin(np.radians(slope))
        solar_in = solar_power_w * illumination_map[r, c]
        
        net_power = solar_in - drive_watts  # Positive = charging
        time_seg = 1.0 / rover_spec['speed_m_per_s'] * 30  # 30m pixel
        
        battery += net_power * (time_seg / 3600)  # Wh
        battery = np.clip(battery, 0, max_battery)
        
        if battery < 0.20 * max_battery:
            # Flag: forced stop for recharge
            profile.append({'waypoint': i, 'status': 'RECHARGE_STOP', 'battery_pct': 20})
        else:
            profile.append({'waypoint': i, 'battery_pct': battery/max_battery*100,
                          'solar_in_w': solar_in, 'drive_w': drive_watts})
    
    return profile
```

**Alternative Paths**
- Path 1 (Optimal): A* with full cost function
- Path 2 (Safest): A* with slope constraint tightened to 10°
- Path 3 (Fastest): Dijkstra's with energy-only cost (straight-line bias)
- All three visualized simultaneously for comparison

#### Outputs
- Optimal path (waypoint list with lat/lon/elevation)
- Total distance (m), estimated traverse time (hours/sols)
- Energy consumption profile (chart: battery % vs. waypoint)
- Risk heatmap along path
- 3 alternative paths for comparison
- Animated CesiumJS rover traverse simulation

---

### MODULE 7: ICE VOLUME ESTIMATOR

#### Purpose
Convert the 2D ice probability map into a 3D volumetric estimate of subsurface ice within the top 5 meters of regolith in the doubly shadowed crater — the key quantitative deliverable that matters for ISRU planning.

#### Physical Model

**Radar Penetration Depth (Skin Depth)**
```
δ_skin = λ / (4π × Im[√ε_complex])

S-band (λ=0.12m), ice: ε_ice = 3.15 + 0.0003j → δ ≈ 35m
S-band (λ=0.12m), dry regolith: ε_reg = 2.7 + 0.003j → δ ≈ 9m
L-band (λ=0.49m), ice: → δ ≈ 140m (deep sounding capability)

→ S-band sensitive to top ~5–10m of ice-bearing regolith
→ L-band samples 10–30m depth
```

**Dielectric Mixing Model (Tiuri–Looyenga)**
```
ε_mix = [(1 - V_ice) × ε_reg^(1/3) + V_ice × ε_ice^(1/3)]^3

Solving for V_ice from measured ε_mix (derived from backscatter model):
V_ice = (ε_mix^(1/3) - ε_reg^(1/3)) / (ε_ice^(1/3) - ε_reg^(1/3))
```

**CPR-to-Ice-Fraction Empirical Calibration**
```python
def cpr_to_ice_fraction(cpr_values, baseline_cpr=0.35):
    """
    Empirical CPR → volumetric ice fraction.
    Calibrated against Cabeus crater ground truth (LCROSS impact results).
    
    Cabeus: V_ice ~ 5.6% by mass (Colaprete et al. 2010)
    → CPR_Cabeus ~ 1.1–1.3 in CPR maps
    → Linear fit: V_ice ≈ 0.20 × (CPR - baseline_cpr) for CPR ∈ [1.0, 2.0]
    
    Returns volumetric ice fraction (0–0.5 capped)
    """
    excess_cpr = np.maximum(cpr_values - baseline_cpr, 0)
    v_ice = np.clip(excess_cpr * 0.20, 0, 0.50)
    return v_ice

def estimate_total_ice_volume(ice_prob_map, cpr_map, pixel_size_m=30, depth_m=5.0):
    """
    Integrate ice fraction across crater floor area and depth.
    Returns volume estimate with uncertainty.
    """
    # Threshold: high-confidence ice pixels (prob > 0.5)
    ice_mask = ice_prob_map > 0.50
    
    # Per-pixel ice fraction
    v_ice_map = cpr_to_ice_fraction(cpr_map)
    
    # Depth weighting: assume exponential decline with depth
    # V_total = ∫₀^5m A(z) × f_ice(z) dz
    # f_ice(z) = f_surface × exp(-z / δ_s) where δ_s ≈ 3m (S-band regime)
    delta_s = 3.0  # m, S-band effective depth scale
    depth_integrated_fraction = v_ice_map * delta_s * (1 - np.exp(-depth_m / delta_s))
    
    # Total volume
    pixel_area = pixel_size_m ** 2  # m²
    ice_volumes_per_pixel = depth_integrated_fraction * ice_mask * pixel_area
    
    total_volume_m3 = ice_volumes_per_pixel.sum()
    total_area_m2 = ice_mask.sum() * pixel_area
    mean_fraction = v_ice_map[ice_mask].mean() if ice_mask.any() else 0
    
    # Uncertainty: ±35% from dielectric model uncertainty + CPR calibration
    uncertainty_m3 = 0.35 * total_volume_m3
    
    return {
        'volume_m3': total_volume_m3,
        'volume_km3': total_volume_m3 / 1e9,
        'uncertainty_m3': uncertainty_m3,
        'ice_area_m2': total_area_m2,
        'ice_area_km2': total_area_m2 / 1e6,
        'mean_ice_fraction_pct': mean_fraction * 100,
        'depth_m': depth_m,
        # ISRU conversion
        'water_mass_kg': total_volume_m3 * 917 * mean_fraction,
        'water_liters': total_volume_m3 * 917 * mean_fraction,
        'astronaut_days': (total_volume_m3 * 917 * mean_fraction) / 3,  # 3kg/day/person
        'rocket_propellant_kg': total_volume_m3 * 917 * mean_fraction * 0.88 * 8  # LOX/LH2 ratio
    }
```

#### Synthetic Depth Profile Visualization
- Generate synthetic cross-section plot showing ice concentration gradient
- X-axis: depth 0–5m
- Y-axis: ice fraction (%) — peaks near surface for shallow ice, deeper for PSR-preserved
- Uncertainty band around mean estimate
- Multi-frequency depth model: S-band shows shallow zone, L-band shows deep zone

#### Outputs
- Ice volume (m³ ± 35% uncertainty) within DSC floor (top 5m)
- Water-equivalent mass (kg)
- ISRU potential metrics (astronaut-days water support, propellant potential kg)
- 3D volumetric visualization (cross-section)
- Spatial ice concentration map within crater
- Comparison with Cabeus/Shackleton reference estimates

---

## SECTION 3: SYSTEM ARCHITECTURE

### 3.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           POLARIS PLATFORM                                   │
│                                                                              │
│  DATA INGESTION LAYER                                                        │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────┐            │
│  │  DFSAR HDF5 │ │ OHRC TIF   │ │  LOLA DEM  │ │  Diviner   │            │
│  │  S+L bands  │ │ 25cm/pixel │ │ 30–118m/px │ │  Temps     │            │
│  └──────┬──────┘ └──────┬──────┘ └─────┬──────┘ └─────┬──────┘            │
│         └───────────────┴──────────────┴───────────────┘                   │
│                                  │                                           │
│  PROCESSING LAYER                ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend (Python 3.11)                                        │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │  │
│  │  │ PSR Mapper   │ │ DFSAR Engine │ │ AI Classifier│ │ Terrain    │  │  │
│  │  │ (illumin.)   │ │ CPR/DOP/mchi │ │ GB+CNN+Bayes │ │ Analyzer   │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │  │
│  │  │ Site Selector│ │ Path Planner │ │ Vol Estimator│                  │  │
│  │  │ MCDA/TOPSIS  │ │ A* + Solar   │ │ Dielectric   │                  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                  │                                           │
│  DATA STORAGE LAYER              ▼                                           │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────────┐                    │
│  │ PostgreSQL  │ │   Redis     │ │  File Storage       │                    │
│  │ + PostGIS   │ │  Job Queue  │ │  (GeoTIFF, HDF5)   │                    │
│  └─────────────┘ └─────────────┘ └────────────────────┘                    │
│                                  │                                           │
│  PRESENTATION LAYER              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  React 18 + Tailwind CSS                                             │  │
│  │  CesiumJS (3D Terrain) + Recharts (Analytics) + Three.js (Volume)   │  │
│  │  7 Screens: Dashboard | Radar Studio | Ice Map | Landing |           │  │
│  │             Traverse | Volume | Mission Report                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Complete Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18 + Vite | SPA framework |
| 3D Terrain | CesiumJS / Resium | 3D lunar terrain viewer |
| Charts | Recharts + D3.js | Analytics visualizations |
| 3D Cross-Section | Three.js | Ice volume subsurface view |
| Maps/GIS | Leaflet.js | 2D map fallback |
| UI | Tailwind CSS + shadcn/ui | Component library |
| State | Zustand | Global state management |
| Backend | FastAPI (Python 3.11) | REST API + WebSocket |
| Task Queue | Celery + Redis | Async processing jobs |
| ML | Scikit-learn + PyTorch | Ice classification |
| Explainability | SHAP | Feature importance |
| SAR Processing | GDAL + h5py + NumPy | DFSAR pipeline |
| GIS | Rasterio + GeoPandas + GDAL | Raster + vector ops |
| Spatial DB | PostgreSQL + PostGIS | Spatial queries |
| Cache | Redis | Map tile caching |
| Containers | Docker + docker-compose | Deployment |

### 3.3 API Design

```
POST /api/v1/psr/compute          → Compute PSR mask from DEM
GET  /api/v1/psr/craters          → List doubly shadowed craters
POST /api/v1/radar/process        → Run DFSAR polarimetric pipeline
GET  /api/v1/radar/cpr            → Get CPR map (tile server)
GET  /api/v1/radar/dop            → Get DOP map (tile server)
GET  /api/v1/radar/mchi           → Get m-chi RGB composite
POST /api/v1/ice/classify         → Run AI ice classifier
GET  /api/v1/ice/probability      → Get ice probability map
GET  /api/v1/ice/explain/{pixel}  → Get SHAP explanation for pixel
POST /api/v1/terrain/analyze      → Run terrain morphology analysis
GET  /api/v1/terrain/hazard       → Get hazard composite map
POST /api/v1/landing/score        → Score candidate landing sites
GET  /api/v1/landing/top3         → Get top 3 ranked sites
POST /api/v1/traverse/plan        → Plan rover path (A*)
GET  /api/v1/traverse/energy      → Get energy profile for path
POST /api/v1/volume/estimate      → Compute ice volume
GET  /api/v1/volume/report        → Get full volume report JSON
GET  /api/v1/report/export        → Download PDF mission report
WS   /ws/processing               → Real-time job progress
```

### 3.4 Database Schema

```sql
-- Doubly Shadowed Craters
CREATE TABLE doubly_shadowed_craters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    center_geom GEOMETRY(Point, 4326),
    area_km2 FLOAT,
    depth_m FLOAT,
    diameter_m FLOAT,
    min_illumination_pct FLOAT,
    estimated_temp_k FLOAT,
    aif FLOAT  -- Annual Illumination Fraction
);

-- Ice Detection Results
CREATE TABLE ice_detections (
    id SERIAL PRIMARY KEY,
    crater_id INT REFERENCES doubly_shadowed_craters(id),
    region_geom GEOMETRY(Polygon, 4326),
    mean_cpr FLOAT,
    mean_dop FLOAT,
    ice_probability FLOAT,
    uncertainty FLOAT,
    area_km2 FLOAT,
    detection_timestamp TIMESTAMPTZ
);

-- Landing Site Candidates
CREATE TABLE landing_sites (
    id SERIAL PRIMARY KEY,
    crater_id INT REFERENCES doubly_shadowed_craters(id),
    site_geom GEOMETRY(Point, 4326),
    composite_score FLOAT,
    ice_proximity_score FLOAT,
    terrain_safety_score FLOAT,
    solar_illumination_score FLOAT,
    dsc_access_score FLOAT,
    comm_los_score FLOAT,
    rank INT,
    risk_level VARCHAR(20)
);

-- Rover Traversals
CREATE TABLE rover_traversals (
    id SERIAL PRIMARY KEY,
    landing_site_id INT REFERENCES landing_sites(id),
    path_geom GEOMETRY(LineString, 4326),
    algorithm VARCHAR(50),
    total_distance_m FLOAT,
    estimated_time_hours FLOAT,
    max_slope_encountered_deg FLOAT,
    energy_profile JSONB,
    risk_score FLOAT
);

-- Ice Volume Estimates
CREATE TABLE ice_volume_estimates (
    id SERIAL PRIMARY KEY,
    crater_id INT REFERENCES doubly_shadowed_craters(id),
    volume_m3 FLOAT,
    uncertainty_m3 FLOAT,
    ice_area_km2 FLOAT,
    mean_ice_fraction_pct FLOAT,
    depth_m FLOAT,
    water_mass_kg FLOAT,
    astronaut_days FLOAT,
    method VARCHAR(100),
    estimated_at TIMESTAMPTZ
);
```

---

## SECTION 4: DEMO STRATEGY

### 4.1 Demo Flow (5-Minute Script)

| Timestamp | Action | What's Real | What's Precomputed |
|-----------|--------|-------------|-------------------|
| 00:00–00:20 | POLARIS splash screen with animated lunar orbit | Live animation | — |
| 00:20–01:00 | Load DFSAR data → watch CPR/DOP maps render on 3D terrain | Data load animation | CPR/DOP maps precomputed |
| 01:00–01:40 | Slide CPR threshold slider → ice mask highlights live | Threshold computation | Ice probability map precomputed |
| 01:40–02:10 | AI classifier result: ice probability map glows in 3D | SHAP explanation live | Model inference precomputed |
| 02:10–02:40 | Landing site: show radar chart of 3 candidates | MCDA scoring live | Site candidates precomputed |
| 02:40–03:30 | Path planner: watch A* animate finding route to DSC | A* runs live in demo | Cost maps precomputed |
| 03:30–04:00 | Ice volume: 3D cross-section + "47,000 m³ of ice" | Volume calc live | Dielectric params precomputed |
| 04:00–04:30 | Mission report card + "Export PDF" click | PDF render | Report content precomputed |

### 4.2 Simulation Strategy

**REAL (implemented, runs live):**
- CPR/DOP threshold slider → real-time ice mask update
- MCDA scoring with live weight adjustment sliders
- A* pathfinding with live animation on 2D grid
- SHAP feature importance computation per pixel click
- Ice volume calculation from ice_fraction input

**SIMULATED (mocked with realistic data):**
- Full DFSAR SLC calibration pipeline (show progress bar, output maps precomputed)
- Boulder detection CNN inference (show confidence scores, bounding boxes precomputed)
- PSR illumination sweep (show keyframe animation, full AIF map precomputed)

**PRECOMPUTED:**
- CPR map, DOP map, m-chi RGB (from provided DFSAR or synthetic data)
- Ice probability map (from model on precomputed features)
- Hazard map, slope map, roughness map
- A* cost map (terrain-derived)
- Landing site composite scores

**VISUALIZED:**
- 3D CesiumJS terrain: DEM + PSR overlay + CPR heatmap + ice probability overlay
- Radar studio: 4-panel side-by-side
- Animated rover path with glowing trail
- 3D subsurface cross-section (Three.js)
- All charts: recharts with glassmorphism cards

---

## SECTION 5: UI/UX DESIGN SPECIFICATIONS

### 5.1 Design System

```
POLARIS Design Language — "Deep Space Instrument Panel"

Colors:
  Background:       #070B18  (deep space black)
  Surface-1:        #0D1426  (dark navy panel)
  Surface-2:        #131C35  (slightly lighter panel)
  Surface-3:        #1A2340  (card background)
  Accent-Ice:       #00D4FF  (primary — ice/cryogenic blue)
  Accent-AI:        #7C3AED  (AI insights — nebula purple)
  Accent-Alert:     #FF5722  (hazard orange)
  Accent-Safe:      #00E676  (safe/success green)
  Accent-Warning:   #FFC107  (moderate risk yellow)
  Text-Primary:     #E0F2FE
  Text-Secondary:   #7B91B0
  Text-Muted:       #4A5568
  Border:           rgba(0, 212, 255, 0.15)
  Glow-Ice:         0 0 24px rgba(0, 212, 255, 0.25)

Typography:
  UI Font:          Inter Variable (400, 500, 600, 700)
  Mono Font:        JetBrains Mono (coordinates, values)
  Display Font:     Exo 2 (screen titles)

Spacing: 4px base unit, 8/12/16/24/32/48px scale
Border-radius: 4px (tight), 8px (cards), 16px (panels), 24px (large)
Glassmorphism: background: rgba(13, 20, 38, 0.85); backdrop-filter: blur(12px)
```

### 5.2 Screen Designs

#### Screen 1: Mission Command Dashboard
```
┌──────────────────────────────────────────────────────────────────────┐
│ ◎ POLARIS    [Search coordinates...]     ⚡ Mission Active   Team ▾  │
├───────┬──────────────────────────────────────────────────────────────┤
│       │  [Ice Conf: 87%] [CPR Max: 2.14] [Sites: 3] [Vol: 47k m³]   │
│  NAV  │──────────────────────────────────────────────────────────────│
│       │                    ┌──────────┐                              │
│ ◉ CMD │                    │  LAYER   │     3D LUNAR TERRAIN         │
│ ○ ICE │   CesiumJS 3D     │  CONTROL │   (CesiumJS with DEM)        │
│ ○ RDR │   Terrain View    │  PANEL   │   PSR overlay in blue        │
│ ○ LND │   with ice map    │          │   Ice probability in teal    │
│ ○ TRV │   and rover path  │ ☑ PSR    │   Rover path in orange       │
│ ○ VOL │                   │ ☑ CPR    │                              │
│ ○ RPT │                   │ ☑ ICE    │                              │
│       │                   │ ☐ SLOPE  │                              │
│       │                   │ ☐ BOULDER│                              │
│       │──────────────────────────────────────────────────────────────│
│  HELP │  [CPR Histogram] [DOP Dist.] [Ice Area Timeline] [AI Status] │
└───────┴──────────────────────────────────────────────────────────────┘
KPI Cards (top):
  - ICE CONFIDENCE:  87.3% ↑2.1%    (ice blue glow)
  - CPR MAXIMUM:     2.14           (gradient bar)
  - LANDING SITES:   3 Identified   (pulsing dot)
  - ICE VOLUME:      47,200 ± 16,500 m³ (sparkline)
```

#### Screen 2: Radar Analysis Studio
```
┌──────────────────────────────────────────────────────────────────────┐
│ ← RADAR ANALYSIS STUDIO          Processing: Complete ✓  Export ↓   │
├──────────────┬───────────────┬───────────────┬───────────────────────┤
│ S-BAND SIGMA │    CPR MAP    │    DOP MAP    │   m-chi RGB COMPOSITE │
│   (σ⁰)       │  [0 ─────3+] │  [0 ──── 1]  │  R=dbl G=surf B=vol   │
│  grayscale   │  teal heatmap │ purple-orange │  full color           │
│  amplitude   │               │               │                       │
├──────────────┴───────────────┴───────────────┴───────────────────────┤
│  THRESHOLD CONTROLS                                                   │
│  CPR Minimum: [════════○══] 1.0      DOP Maximum: [○════════════] 0.13│
│  ▶ Ice pixels highlighted in real-time below                          │
├────────────────────────────────────────────────────────────────────┤
│  FEATURE SPACE                           AI FEATURE IMPORTANCE       │
│  CPR vs DOP scatter plot                 SHAP bar chart              │
│  □ Ice regions (teal)                    CPR     ████████████ 0.41   │
│  □ Rocky regions (orange)               DOP     ███████████  0.35   │
│  □ Ambiguous (grey)                     In DSC  ████████     0.12   │
│  □ Smooth floor (purple)               Slope   ████         0.07   │
│                                          m-chi   ███          0.05   │
└──────────────────────────────────────────────────────────────────────┘
```

#### Screen 3: Ice Detection Intelligence
```
┌──────────────────────────────────────────────────────────────────────┐
│ ← ICE DETECTION                   [Confidence: 87%] [Area: 3.7 km²] │
├──────────────────────────────────────────────────────────────────────┤
│                      ICE PROBABILITY MAP (3D terrain overlay)         │
│     [Interactive CesiumJS: green→yellow→red ice probability]         │
│     [Click any pixel → see SHAP explanation in right panel]          │
├──────────────────────────────────┬───────────────────────────────────┤
│  DETECTION SUMMARY               │  AI EXPLANATION (click-to-reveal) │
│  High Conf (>0.8):  1.2 km²      │  Pixel at (-89.61°, 45.23°):      │
│  Medium (0.5–0.8):  2.5 km²      │                                   │
│  Low (<0.5):        8.1 km²      │  ● CPR=1.45 → Ice scattering ↑   │
│                                   │  ● DOP=0.09 → Depolarized ↑     │
│  DSC REGIONS:                    │  ● In doubly shadowed crater ↑   │
│  ◉ DSC-01 (Faustini-A):          │  ● Slope=3.2° (safe) ↑          │
│    Ice Prob: 91% ± 8%            │  ● m-chi Volume: 67% ↑           │
│  ◉ DSC-02 (Haworth-B):           │                                   │
│    Ice Prob: 73% ± 12%           │  VERDICT: HIGH PROBABILITY ICE    │
│                                   │  Confidence: 91% ± 8%            │
└──────────────────────────────────┴───────────────────────────────────┘
```

#### Screen 4: Landing Site Evaluator
```
┌──────────────────────────────────────────────────────────────────────┐
│ ← LANDING SITE EVALUATOR          [MCDA Weights] [Export Report]     │
├───────────────────────────────────────────────────┬──────────────────┤
│           TERRAIN SAFETY MAP (3D)                  │ SITE COMPARISON  │
│  Red: excluded, Yellow: caution, Green: viable     │                  │
│  Landing ellipses marked as 1, 2, 3               │ [Radar Chart]    │
│                                                     │  showing 5      │
│  ╔══════════════════════════════════════════╗      │  criteria per   │
│  ║  SITE 1  Score: 0.87 ★★★★★              ║      │  site           │
│  ║  Lat: -89.6121, Lon: 45.2341            ║      │                  │
│  ║  Slope: 4.3°  |  Ice nearby: 91%        ║      │ [1] [2] [3]     │
│  ║  Solar: 82%   |  Dist to DSC: 1.2km    ║      │ selector tabs   │
│  ╚══════════════════════════════════════════╝      │                  │
│  SITE 2  Score: 0.79  ●●●●○                        │ RISK MATRIX     │
│  SITE 3  Score: 0.71  ●●●○○                        │ 2x2 chart       │
└───────────────────────────────────────────────────┴──────────────────┘
```

#### Screen 5: Rover Traverse Planner
```
┌──────────────────────────────────────────────────────────────────────┐
│ ← TRAVERSE PLANNER     Algorithm: Weighted A*  ▾   [▶ Animate]       │
├───────────────────────────────────────────────┬──────────────────────┤
│      3D TERRAIN + ROVER PATH                  │ PATH METRICS         │
│   Landing Site (🏠) → DSC (🎯)               │ Distance: 4,320m     │
│   Orange trail = optimal path                 │ Time:     36.2 hrs   │
│   Faded = alternative paths                   │ Energy:   82% used   │
│   Hazard overlay = red zones                  │ Max slope: 11.2°     │
│                                               │ Risk: LOW (0.18)     │
│   [▶ ANIMATE ROVER]                          │──────────────────────│
│   Animated rover moves along path             │ ENERGY PROFILE       │
│   Energy meter pulses in sync                 │ [Area chart]         │
│                                               │ Battery % vs. km     │
│                                               │ Solar recharge zones │
│                                               │ highlighted          │
├───────────────────────────────────────────────┴──────────────────────┤
│  PATH COMPARISON: [Optimal ─────] [Safest - - - -] [Fastest ·····]   │
│  Optimal: 4.32km  36h  | Safest: 5.71km  48h  | Fastest: 3.98km 31h │
└──────────────────────────────────────────────────────────────────────┘
```

#### Screen 6: Ice Volume & ISRU Dashboard
```
┌──────────────────────────────────────────────────────────────────────┐
│ ← ICE VOLUME & ISRU POTENTIAL          Confidence: ±35%  Export ↓   │
├──────────────────────────┬───────────────────────────────────────────┤
│  VOLUME ESTIMATE         │  3D SUBSURFACE CROSS-SECTION              │
│  ┌────────────────────┐  │  [Three.js 3D cross-section of crater]    │
│  │   47,200 m³        │  │  showing ice concentration gradient       │
│  │   ± 16,500 m³      │  │  by depth (0→5m), rotatable              │
│  │   Ice Volume       │  │                                           │
│  └────────────────────┘  │                                           │
│  Ice Area:  3.7 km²      │                                           │
│  Depth:     0–5 m        │───────────────────────────────────────────│
│  Avg Conc.: 24.3%        │  DEPTH PROFILE                            │
│                          │  [Line chart: ice fraction vs depth]      │
│  ISRU POTENTIAL          │  Peak near 1–2m depth                     │
│  💧 43M liters water     │  Uncertainty band shown                   │
│  🧑 39,400 astronaut-days│                                           │
│  🚀 370,000 kg propellant│  COMPARE TO KNOWN PSRS                   │
│                          │  Cabeus: 70k m³ | Haworth: 90k m³        │
└──────────────────────────┴───────────────────────────────────────────┘
```

#### Screen 7: Mission Intelligence Report
- Auto-generated report card with all findings
- Section headers: Ice Detection | Landing Site | Traverse | Volume | ISRU
- Confidence level chips per finding (HIGH/MEDIUM/LOW)
- "Export PDF" → downloads professional mission report
- "ISRO Format Export" → structured JSON for mission planning integration

---

## SECTION 6: ADVANCED FEATURES

### Feature 1: Multi-Frequency Radar Depth Model
**Why it wins:** L-band vs S-band CPR ratio reveals whether ice is shallow (<5m) or deep (5–30m), transforming a 2D map into a 3D depth-sensitive model. No basic team will think of this.
**Implementation:** CPR_ratio = CPR_S / CPR_L → Ratio > 1.5 = deep ice dominant; Ratio < 0.8 = shallow ice dominant
**Demo:** Side-by-side S vs L band, animated depth profile slider

### Feature 2: Bayesian Uncertainty Propagation
**Why it wins:** Shows scientific maturity — judges are often researchers who know that point estimates without uncertainty are meaningless in planetary science.
**Implementation:** MC Dropout (20 passes) on CNN ice classifier → σ_pred map shown as "confidence halo"
**Demo:** Toggle "show uncertainty" → colored bands appear around ice regions

### Feature 3: ISRU Potential Calculator
**Why it wins:** Directly answers "what does this ice mean for human presence?" — the ultimate mission relevance argument.
**Implementation:** Volume × purity estimate × extraction efficiency → liters water / kg propellant / astronaut-days
**Demo:** Animated counter showing real-time ISRU potential as user adjusts ice threshold

### Feature 4: Solar Illumination Simulator
**Why it wins:** Operational realism — judges care about whether a rover can actually be powered during traverse.
**Implementation:** Pre-animated 28-day lunar illumination sweep on terrain (keyframe interpolation)
**Demo:** Click "Play Solar Day" → watch shadows sweep across terrain in 10-second timelapse

### Feature 5: Mission Risk Monte Carlo
**Why it wins:** Quantifies operational risks that static maps miss — slope distribution along path, probability of safe landing in 3σ ellipse.
**Implementation:** 1000 Monte Carlo samples of terrain + path uncertainty → risk percentile distributions
**Demo:** "Risk Envelope" around rover path shown as semi-transparent corridor

### Feature 6: Historical PSR Comparison Table
**Why it wins:** Contextualizes findings against known ice deposits (Cabeus, Haworth, Shackleton). Shows you know the literature.
**Implementation:** Static table from published papers + our estimates in same format
**Demo:** Inline comparison card in volume screen: "Our DSC has 67% of Cabeus ice volume"

### Feature 7: Terrain Profile Viewer
**Why it wins:** Interactive elevation cross-section along the rover path shows exactly what the rover navigates.
**Implementation:** Extract DEM values along A* path → Recharts AreaChart with slope color coding
**Demo:** Hover on path in 3D view → matching point highlighted in profile chart

---

## SECTION 7: VISUALIZATION STRATEGY

| Visualization | Data Source | Framework | Interaction |
|---------------|-------------|-----------|-------------|
| 3D Lunar Terrain | LOLA DEM | CesiumJS | Pan, zoom, tilt, fly-to |
| PSR Overlay | Illumination model | CesiumJS heatmap | Toggle + opacity slider |
| CPR Heatmap | DFSAR engine | CesiumJS ImageryLayer | Threshold slider |
| DOP Map | DFSAR engine | CesiumJS ImageryLayer | Toggle |
| m-chi RGB | DFSAR engine | CesiumJS ImageryLayer | Channel selector |
| Ice Probability | AI classifier | CesiumJS heatmap | Confidence filter |
| Uncertainty Halo | MC Dropout | CesiumJS heatmap | Toggle |
| CPR/DOP Feature Space | Radar engine | D3 scatter plot | Brush select, click |
| SHAP Bar Chart | SHAP | Custom SVG bars | Hover, click |
| Terrain Hazard | Terrain analyzer | CesiumJS heatmap | Opacity |
| Landing Sites | Site selector | CesiumJS entity | Click to fly-to |
| Landing Radar Chart | MCDA | Recharts RadarChart | Site switcher |
| Rover Path | A* planner | CesiumJS PathEntity | Animate, hover |
| Energy Profile | Path planner | Recharts AreaChart | Hover |
| Solar Timeline | Illumination | Recharts LineChart | Scrub |
| Ice Cross-Section | Volume est. | Three.js 3D | Rotate, slice |
| Depth Profile | Volume est. | Recharts LineChart | Hover |
| ISRU Metrics | Volume est. | Animated counters | Slider |
| Mission Report | All modules | HTML/PDF | Export |

---

## SECTION 8: AI AGENT IMPLEMENTATION CONTEXT

### 8.1 Project Folder Structure

```
polaris/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   ├── TopBar.jsx
│   │   │   │   └── KPICards.jsx
│   │   │   ├── terrain/
│   │   │   │   ├── CesiumViewer.jsx          # 3D CesiumJS terrain
│   │   │   │   ├── LayerControls.jsx          # Toggle PSR/CPR/ice layers
│   │   │   │   └── TerrainOverlays.jsx        # Heatmap + vector overlays
│   │   │   ├── radar/
│   │   │   │   ├── RadarPanel.jsx             # 4-panel radar studio
│   │   │   │   ├── ThresholdSlider.jsx        # CPR/DOP live threshold
│   │   │   │   ├── FeatureScatter.jsx         # D3 CPR vs DOP scatter
│   │   │   │   └── ShapChart.jsx              # SHAP importance bars
│   │   │   ├── ice/
│   │   │   │   ├── IceProbMap.jsx             # Ice probability overlay
│   │   │   │   ├── DetectionSummary.jsx       # Stats + DSC list
│   │   │   │   └── ExplanationPanel.jsx       # Per-pixel SHAP explain
│   │   │   ├── landing/
│   │   │   │   ├── LandingMap.jsx             # Terrain safety + sites
│   │   │   │   ├── SiteCard.jsx               # Score breakdown card
│   │   │   │   ├── RadarChart.jsx             # Recharts radar per site
│   │   │   │   └── RiskMatrix.jsx             # 2x2 risk viz
│   │   │   ├── traverse/
│   │   │   │   ├── PathViewer.jsx             # Animated rover path
│   │   │   │   ├── EnergyProfile.jsx          # Battery % chart
│   │   │   │   ├── TerrainProfile.jsx         # Elevation cross-section
│   │   │   │   └── PathComparison.jsx         # 3 paths overlay
│   │   │   └── volume/
│   │   │       ├── IceVolumeDashboard.jsx     # Hero metric + breakdown
│   │   │       ├── CrossSectionViewer.jsx     # Three.js subsurface
│   │   │       ├── DepthProfile.jsx           # Ice fraction vs depth
│   │   │       └── ISRUCalculator.jsx         # Water/propellant metrics
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── RadarStudio.jsx
│   │   │   ├── IceDetection.jsx
│   │   │   ├── LandingSite.jsx
│   │   │   ├── TraversePlanner.jsx
│   │   │   ├── VolumeReport.jsx
│   │   │   └── MissionReport.jsx
│   │   ├── store/
│   │   │   ├── useMapStore.js                  # Layer visibility, map state
│   │   │   ├── useIceStore.js                  # Ice detection results
│   │   │   ├── useMissionStore.js              # Landing site, traverse
│   │   │   └── useVolumeStore.js               # Volume estimates
│   │   ├── api/
│   │   │   └── polarisAPI.js                   # Axios API client
│   │   └── utils/
│   │       ├── colorScales.js                  # D3 color functions
│   │       ├── cesiumHelpers.js                # CesiumJS utilities
│   │       └── formatters.js                   # Number/coord formatting
│   ├── public/
│   │   └── tiles/                              # Precomputed map tiles
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── psr.py
│   │   │   │   ├── radar.py
│   │   │   │   ├── ice.py
│   │   │   │   ├── terrain.py
│   │   │   │   ├── landing.py
│   │   │   │   ├── traverse.py
│   │   │   │   ├── volume.py
│   │   │   │   └── report.py
│   │   │   └── websocket.py                    # Real-time progress
│   │   ├── services/
│   │   │   ├── psr_mapper.py                   # Illumination + PSR
│   │   │   ├── dfsar_processor.py              # CPR/DOP/m-chi pipeline
│   │   │   ├── terrain_analyzer.py             # Slope/roughness/boulders
│   │   │   ├── ice_classifier.py               # AI + Bayesian fusion
│   │   │   ├── landing_selector.py             # MCDA scoring
│   │   │   ├── path_planner.py                 # A* + energy model
│   │   │   ├── volume_estimator.py             # Dielectric + integration
│   │   │   └── report_generator.py             # PDF report
│   │   ├── models/
│   │   │   ├── schemas.py                      # Pydantic models
│   │   │   └── db_models.py                    # SQLAlchemy + PostGIS
│   │   ├── ml/
│   │   │   ├── ice_classifier.pkl              # Trained GB model
│   │   │   ├── cnn_ice.pt                      # PyTorch CNN
│   │   │   └── shap_explainer.pkl
│   │   ├── config.py
│   │   └── main.py                             # FastAPI app
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── data/
│   ├── raw/
│   │   ├── dfsar/                              # DFSAR HDF5 files
│   │   └── ohrc/                               # OHRC GeoTIFF
│   ├── dem/
│   │   └── lola_spole_30m.tif                 # LOLA DEM (south pole)
│   ├── processed/
│   │   ├── cpr_map.tif
│   │   ├── dop_map.tif
│   │   ├── mchi_rgb.tif
│   │   ├── ice_probability.tif
│   │   ├── psr_mask.tif
│   │   └── hazard_map.tif
│   └── reference/                             # Known PSR CPR values
│
├── notebooks/
│   ├── 01_psr_analysis.ipynb
│   ├── 02_dfsar_processing.ipynb
│   ├── 03_ice_classification.ipynb
│   ├── 04_path_planning.ipynb
│   └── 05_volume_estimation.ipynb
│
├── docker-compose.yml
└── README.md
```

### 8.2 State Management Schema (Zustand)

```javascript
// useMapStore.js
{
  layers: {
    psr: { visible: true, opacity: 0.7 },
    cpr: { visible: true, opacity: 0.85, threshold: 1.0 },
    dop: { visible: false, opacity: 0.8, threshold: 0.13 },
    ice_probability: { visible: true, opacity: 0.9 },
    hazard: { visible: false, opacity: 0.7 },
    traverse: { visible: true }
  },
  viewState: { lat: -89.5, lon: 0, altitude: 50000 },
  selectedCrater: null,
  selectedLandingSite: null
}

// useIceStore.js
{
  cprStats: { mean: 0.82, max: 2.14, ice_pixel_count: 12453 },
  dopStats: { mean: 0.31, min: 0.04 },
  iceDetections: [{id, lat, lon, probability, area_km2, confidence}],
  hoveredPixel: { lat, lon, cpr, dop, ice_prob, shap_explanation },
  totalIceAreaKm2: 3.7
}

// useMissionStore.js
{
  landingSites: [
    {rank:1, lat, lon, composite_score:0.87, breakdown:{...}},
    {rank:2, lat, lon, composite_score:0.79, breakdown:{...}},
    {rank:3, lat, lon, composite_score:0.71, breakdown:{...}}
  ],
  selectedSite: 1,
  traversePath: { waypoints: [...], distance_m, time_hours, energy_profile },
  pathAnimation: { playing: false, progress: 0 }
}
```

### 8.3 API Contract Examples

```javascript
// POST /api/v1/radar/process
REQUEST: {
  "dfsar_path": "data/raw/dfsar/dsc_faustini_A.h5",
  "band": "S",
  "window_size": 5,
  "products": ["cpr", "dop", "mchi", "ice_probability"]
}
RESPONSE: {
  "job_id": "job_abc123",
  "status": "processing",
  "estimated_time_s": 45
}
// WS /ws/processing → streams progress 0-100%, then "complete"
// GET /api/v1/radar/cpr?job_id=job_abc123 → returns tile URL

// POST /api/v1/traverse/plan
REQUEST: {
  "start": {"lat": -89.6121, "lon": 45.2341},
  "goal_crater_id": 1,
  "algorithm": "weighted_astar",
  "w": 1.5,
  "constraints": {
    "max_slope_deg": 15,
    "min_battery_reserve_pct": 20,
    "rover_spec": {
      "battery_wh": 500,
      "solar_panel_w": 150,
      "drive_power_w": 100,
      "speed_m_per_s": 0.03
    }
  }
}
RESPONSE: {
  "path": [{"lat": ..., "lon": ..., "elevation": ..., "slope": ...}],
  "total_distance_m": 4320,
  "estimated_time_hours": 36.2,
  "energy_profile": [{"waypoint": 0, "battery_pct": 100, ...}],
  "max_slope_deg": 11.2,
  "risk_score": 0.18,
  "recharge_stops": [],
  "alternatives": [{"type": "safest", ...}, {"type": "fastest", ...}]
}

// POST /api/v1/volume/estimate
REQUEST: {
  "crater_id": 1,
  "depth_m": 5.0,
  "band": "S",
  "method": "dielectric_mixing"
}
RESPONSE: {
  "volume_m3": 47200,
  "uncertainty_m3": 16500,
  "ice_area_km2": 3.7,
  "mean_ice_fraction_pct": 24.3,
  "isru": {
    "water_mass_kg": 10400000,
    "water_liters": 10400000,
    "astronaut_days": 3466667,
    "rocket_propellant_kg": 73280000
  },
  "depth_profile": [
    {"depth_m": 0.5, "ice_fraction_pct": 31.2},
    {"depth_m": 1.0, "ice_fraction_pct": 27.8},
    ...
  ],
  "comparison": {
    "cabeus_volume_m3": 70000,
    "ratio_to_cabeus": 0.67
  }
}
```

---

## SECTION 9: PRIORITIZATION

### Phase 1 — Demo Core (Must-Have, Days 1–2)

| Priority | Feature | Demo Impact | Complexity |
|----------|---------|-------------|------------|
| 1 | Professional dark UI with sidebar + KPI cards | Critical | Low |
| 2 | CesiumJS 3D terrain with PSR overlay | Critical | Medium |
| 3 | Precomputed CPR/DOP maps loaded as heatmap layers | Critical | Low |
| 4 | CPR threshold slider → live ice mask update | High | Low |
| 5 | Ice probability map overlay | Critical | Low |
| 6 | MCDA landing site scorer (live) + radar chart | Critical | Medium |
| 7 | A* path planner with animated visualization | Critical | Medium |
| 8 | Ice volume calculator + ISRU metrics | High | Low |
| 9 | SHAP feature importance chart | High | Medium |

### Phase 2 — Enhanced Features (Days 3–4)

| Priority | Feature | Demo Impact | Complexity |
|----------|---------|-------------|------------|
| 1 | Animated rover traverse with energy meter | Very High | Medium |
| 2 | Per-pixel SHAP explanation on click | High | Low |
| 3 | Multi-frequency S+L band comparison panel | High | Medium |
| 4 | Three.js ice cross-section 3D viewer | Very High | High |
| 5 | Solar illumination timeline chart | High | Low |
| 6 | Path energy profile chart | High | Low |
| 7 | Risk matrix per landing site | Medium | Low |
| 8 | Downloadable PDF mission report | Medium | Medium |

### Phase 3 — Production Extensions

| Feature | Why |
|---------|-----|
| Full DFSAR SLC calibration pipeline | Real-time processing from raw data |
| Bayesian uncertainty maps (MC Dropout) | Scientific publication quality |
| Boulder detection CNN | Complete terrain assessment |
| RL-based rover path optimizer | Beyond A*, learns from hazard distributions |
| PSR illumination timelapse animator | 28-day solar cycle simulation |
| PDS (NASA) dataset integration | Real data validation from external sources |
| Export to ISRO mission data format | Direct operational utility |
| Collaborative multi-user annotation | Team science workflow |

---

## SECTION 10: COMPETITIVE ANALYSIS

### What Average Teams Will Build
- A Python notebook with matplotlib CPR heatmap
- Simple threshold: "if CPR > 1: ice = True"
- Static image of a crater with PSR colored
- Basic text report

### What Good Teams Will Build
- Proper CPR + DOP dual-criterion mask
- Leaflet.js or Folium interactive 2D map
- Simple A* or Dijkstra path shown statically
- Basic landing site suggestion with slope analysis
- Clean but generic dashboard UI

### What Top Teams Will Build (Our Competition)
- CPR/DOP processing pipeline in Python
- Interactive Streamlit/Dash app with map
- Basic path planning with A*
- Some form of volume estimation
- Decent UI matching the HeatWatch reference

### Where POLARIS Creates Separation

| Differentiator | Why It Matters to Judges | Estimated % of Teams Doing This |
|----------------|--------------------------|--------------------------------|
| m-chi polarimetric decomposition | Shows radar science depth beyond CPR/DOP | < 5% |
| 3D CesiumJS terrain viewer | Visual WOW — looks like ISRO mission control | < 3% |
| Bayesian uncertainty quantification | Scientific rigor in estimates | < 2% |
| Energy-aware path planning (solar budget) | Operational realism | < 5% |
| ISRU potential scoring | Mission relevance narrative | < 10% |
| Multi-frequency S+L depth model | Novel scientific contribution | < 1% |
| Three.js 3D ice cross-section | Unique visualization | < 2% |
| SHAP explainability per pixel | AI transparency | < 5% |
| Per-site risk matrix | Engineering depth | < 10% |

### The "Wow Moments" That Win

1. **[VISUAL]** 3D lunar terrain with ice glowing in teal beneath PSR shadows — instant emotional impact
2. **[SCIENCE]** "Unlike approaches that only use CPR, we apply m-chi decomposition to separate volume scattering from double-bounce, which is the critical distinction between ice and rough rocky terrain in permanently shadowed craters"
3. **[INNOVATION]** Click any pixel → "Ice detected here because CPR=1.45 (↑89%), DOP=0.09 (↑72%), within doubly shadowed crater"
4. **[OPERATIONAL]** Animated rover navigating terrain with real-time energy meter showing battery level
5. **[MISSION]** "We estimate 47,200 m³ of ice — equivalent to 43 million liters of water, enough to support 39,000 astronaut-days of life support or produce 370,000 kg of rocket propellant"
6. **[RIGOR]** Every estimate shows uncertainty bounds — "47,200 ± 16,500 m³ at 68% confidence" — ISRO scientists will respect this
7. **[DEPTH]** Multi-frequency comparison: "S-band shows shallow ice (<5m), L-band penetrates deeper confirming ice to 15m depth"

---

## APPENDIX: KEY FORMULAS REFERENCE

### Circular Polarization Ratio (CPR)
```
CPR = P_SC / P_OC
Ice signature: CPR > 1.0
Distinguishing criterion: CPR > 1.0 AND DOP < 0.13
```

### Degree of Polarization (DOP)
```
DOP = √(1 - 27·det[T] / trace[T]³)
Ice: DOP < 0.13 (volume scattering dominates → depolarization)
Rock: DOP > 0.40 (specular surface scattering → polarization preserved)
```

### m-chi Decomposition (Raney et al.)
```
Volume    = m · (1 - |sin χ|) · T₁₁ / 2   ← ice-like scattering
Dbl-bounce = m · (1 + sin χ) · T₁₁ / 4   ← rocky surface
Surface    = m · (1 - sin χ) · T₁₁ / 4   ← smooth specular
Where m = DOP, χ = ellipticity angle
```

### Radar Skin Depth
```
δ = λ / (4π · Im[√ε_complex])
S-band + ice:     δ ≈ 35m
S-band + regolith: δ ≈ 9m
L-band + ice:     δ ≈ 140m
```

### Ice Volume Integration
```
V_ice = ∫∫_A ∫₀^5m f(x,y,z) dz dA
      ≈ Σ_pixels [f_surface(x,y) · δ · (1 - e^{-5/δ}) · Δx·Δy]
Where f_surface = CPR-derived volumetric ice fraction
```

### Terrain Traversal Energy Cost
```
E(pixel) = P_base + P_base · k · sin(θ_slope) + boulder_penalty + solar_credit
k = slope steepness factor (~2.0 for lunar rover)
solar_credit = P_solar · AIF(pixel) (negative cost = recharging)
```

---

*POLARIS — Built for BAH 2026. Powered by Chandrayaan-2. Designed for the Lunar South Pole.*
*Every crater explored. Every ice deposit counted. Every path planned.*
