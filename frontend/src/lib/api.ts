export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws") + "/ws/processing";

export interface Crater {
  id: number;
  name: string;
  longitude: number;
  latitude: number;
  area_km2: number;
  depth_m: number;
  diameter_m: number;
  min_illumination_pct: number;
  estimated_temp_k: number;
  aif: number;
}

export interface LandingSite {
  id: number;
  rank: number;
  name: string;
  longitude: number;
  latitude: number;
  composite_score: number;
  ice_proximity_score: number;
  terrain_safety_score: number;
  solar_illumination_score: number;
  dsc_access_score: number;
  comm_los_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface Waypoint {
  longitude: number;
  latitude: number;
}

export interface EnergySegment {
  waypoint: number;
  grid_y: number;
  grid_x: number;
  status: string;
  battery_pct: number;
  solar_in_w: number;
  drive_w: number;
}

export interface TraversePlan {
  distance_m: number;
  estimated_time_hours: number;
  max_slope_deg: number;
  path: Waypoint[];
  energy_profile: EnergySegment[];
}

export interface VolumeReport {
  volume_m3: number;
  volume_km3: number;
  uncertainty_m3: number;
  ice_area_km2: number;
  mean_ice_fraction_pct: number;
  depth_m: number;
  water_mass_kg: number;
  astronaut_days: number;
  rocket_propellant_kg: number;
  method: string;
  estimated_at: string;
}

export interface ShapExplanation {
  coordinates: { x: number; y: number };
  features: {
    cpr: number;
    dop: number;
    slope_deg: number;
    roughness_m: number;
  };
  shap_values: Record<string, number>;
  verdict: string;
  probability: number;
}

export interface ScoreWeights {
  ice_proximity_weight: number;
  terrain_safety_weight: number;
  solar_illumination_weight: number;
  dsc_access_weight: number;
  comm_los_weight: number;
}

export async function fetchCraters(): Promise<Crater[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/psr/craters`);
  if (!res.ok) throw new Error("Failed to fetch craters");
  return res.json();
}

export async function fetchLandingCandidates(): Promise<LandingSite[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/landing/top3`);
  if (!res.ok) throw new Error("Failed to fetch landing candidates");
  return res.json();
}

export async function scoreLandingSites(weights: ScoreWeights): Promise<LandingSite[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/landing/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(weights),
  });
  if (!res.ok) throw new Error("Failed to score landing sites");
  return res.json();
}

export async function planRoverPath(landingSiteRank: number, craterId: number): Promise<TraversePlan> {
  const res = await fetch(`${API_BASE_URL}/api/v1/traverse/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ landing_site_rank: landingSiteRank, crater_id: craterId }),
  });
  if (!res.ok) throw new Error("Failed to plan rover path");
  return res.json();
}

export async function estimateIceVolume(craterId: number, depthM: number, baselineCpr: number): Promise<VolumeReport> {
  const res = await fetch(`${API_BASE_URL}/api/v1/volume/estimate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ crater_id: craterId, depth_m: depthM, baseline_cpr: baselineCpr }),
  });
  if (!res.ok) throw new Error("Failed to estimate ice volume");
  return res.json();
}

export async function fetchVolumeReport(): Promise<VolumeReport> {
  const res = await fetch(`${API_BASE_URL}/api/v1/volume/report`);
  if (!res.ok) throw new Error("Failed to fetch volume report");
  return res.json();
}

export async function fetchPsrMaps(): Promise<{
  slope_img: string;
  psr_img: string;
  hazard_img: string;
  dsc_img?: string;
  dem_img?: string;
  roughness_img?: string;
  ohrc_img?: string;
}> {
  const res = await fetch(`${API_BASE_URL}/api/v1/psr/craters`).then(() => 
    fetch(`${API_BASE_URL}/api/maps/psr`) // Fallback matching backend structure
  );
  if (!res.ok) {
    // Try directly /api/maps/psr
    const directRes = await fetch(`${API_BASE_URL}/api/maps/psr`);
    if (!directRes.ok) throw new Error("Failed to fetch PSR maps");
    return directRes.json();
  }
  return res.json();
}

export async function fetchIceMaps(): Promise<{
  cpr_img: string;
  dop_img: string;
  ice_prob_img: string;
}> {
  const res = await fetch(`${API_BASE_URL}/api/maps/ice`);
  if (!res.ok) throw new Error("Failed to fetch polarimetry maps");
  return res.json();
}

export async function triggerPsrProcessing(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/psr/compute`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger PSR compute");
  return res.json();
}

export async function triggerRadarProcessing(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/radar/process`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger radar processing");
  return res.json();
}

export async function triggerIceClassification(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ice/classify`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger ice classification");
  return res.json();
}

export async function fetchShapExplanation(x: number, y: number): Promise<ShapExplanation> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ice/explain/${x},${y}`);
  if (!res.ok) throw new Error("Failed to fetch SHAP explanation");
  return res.json();
}

export async function fetchMissionReport(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/report/export`);
  if (!res.ok) throw new Error("Failed to fetch mission report");
  return res.json();
}

export async function fetchMetadata(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/data/metadata`);
  if (!res.ok) throw new Error("Failed to fetch metadata");
  return res.json();
}
