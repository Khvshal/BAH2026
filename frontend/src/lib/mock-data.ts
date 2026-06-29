// Deterministic mock data for POLARIS modules.

function mulberry32(seed: number) {
  return () => {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const MISSION = {
  name: "Chandrayaan-2 / DFSAR",
  target: "Lunar South Pole (75°–90°S)",
  campaign: "POLARIS-S01",
  cycle: "Orbit 1,842",
  utc: "2026-03-14T08:42:11Z",
};

export const KPIS = [
  { label: "PSRs Mapped", value: "1,284", delta: "+47", unit: "craters", tone: "ice" as const },
  { label: "Ice-Probable Area", value: "2,917", delta: "+112", unit: "km²", tone: "success" as const },
  { label: "Mean CPR (PSR)", value: "1.42", delta: "+0.04", unit: "σ", tone: "ice" as const },
  { label: "Est. Ice Volume (5 m)", value: "0.83", delta: "±0.21", unit: "km³ WEQ", tone: "warning" as const },
];

export type Crater = {
  id: string;
  name: string;
  lat: number;
  lon: number;
  radius: number; // px
  psr: boolean;
  doubly: boolean;
  cpr: number;
  dop: number;
  iceProb: number;
  volume: number; // m^3 WEQ
};

export function generateCraters(): Crater[] {
  const rnd = mulberry32(42);
  const names = ["Shackleton", "Cabeus", "Haworth", "Faustini", "de Gerlache", "Sverdrup", "Shoemaker", "Slater", "Nobile", "Amundsen", "Idel'son", "Wiechert"];
  const out: Crater[] = [];
  for (let i = 0; i < 64; i++) {
    const lat = -75 - rnd() * 15;
    const lon = -180 + rnd() * 360;
    const psr = rnd() > 0.45;
    const doubly = psr && rnd() > 0.7;
    const cpr = psr ? 0.9 + rnd() * 0.9 : 0.3 + rnd() * 0.5;
    const dop = 0.4 + rnd() * 0.5;
    const iceProb = psr ? Math.min(1, 0.4 + rnd() * 0.6) : rnd() * 0.35;
    out.push({
      id: `C-${(1000 + i).toString()}`,
      name: i < names.length ? names[i] : `Unnamed ${i}`,
      lat, lon,
      radius: 6 + rnd() * 28,
      psr, doubly, cpr, dop, iceProb,
      volume: iceProb * (1e6 + rnd() * 8e6),
    });
  }
  return out.sort((a, b) => b.iceProb - a.iceProb);
}

export type LandingSite = {
  id: string;
  name: string;
  lat: number;
  lon: number;
  iceScore: number;
  safetyScore: number;
  illumination: number; // %
  commsWindow: number; // hrs/day
  slope: number; // deg
  composite: number;
};

export function generateLandingSites(): LandingSite[] {
  const rnd = mulberry32(7);
  const names = ["Aristarchus Rim", "Shackleton Plateau", "Cabeus Apron", "Haworth Edge", "Faustini North", "de Gerlache Saddle"];
  return names.map((n, i) => {
    const ice = 0.55 + rnd() * 0.4;
    const safety = 0.5 + rnd() * 0.45;
    const illum = 30 + rnd() * 55;
    const comms = 8 + rnd() * 12;
    const slope = 2 + rnd() * 12;
    const composite = +(ice * 0.4 + safety * 0.3 + (illum / 100) * 0.2 + (comms / 24) * 0.1).toFixed(3);
    return {
      id: `LS-${i + 1}`,
      name: n,
      lat: -80 - rnd() * 8,
      lon: -180 + rnd() * 360,
      iceScore: +ice.toFixed(2),
      safetyScore: +safety.toFixed(2),
      illumination: +illum.toFixed(1),
      commsWindow: +comms.toFixed(1),
      slope: +slope.toFixed(1),
      composite,
    };
  }).sort((a, b) => b.composite - a.composite);
}

export type Waypoint = { x: number; y: number; energy: number; sol: number; note?: string };

export function generateTraverse(): { waypoints: Waypoint[]; totalDistance: number; totalEnergy: number; sols: number } {
  const rnd = mulberry32(13);
  const pts: Waypoint[] = [];
  let x = 80, y = 380;
  let energy = 100;
  for (let i = 0; i < 14; i++) {
    pts.push({
      x, y,
      energy: +energy.toFixed(1),
      sol: i,
      note: i === 0 ? "Landing" : i === 13 ? "Ice cache" : undefined,
    });
    x += 30 + rnd() * 50;
    y += (rnd() - 0.5) * 60;
    energy -= 4 + rnd() * 3;
    if (i % 4 === 3) energy = Math.min(100, energy + 22); // solar recharge
  }
  return {
    waypoints: pts,
    totalDistance: 1.84,
    totalEnergy: 412,
    sols: pts.length - 1,
  };
}

export function generateRadarTimeseries(n = 64) {
  const rnd = mulberry32(99);
  return Array.from({ length: n }, (_, i) => ({
    t: i,
    cpr: 0.6 + Math.sin(i / 6) * 0.3 + rnd() * 0.25,
    dop: 0.5 + Math.cos(i / 9) * 0.2 + rnd() * 0.18,
    mchi: 0.4 + Math.sin(i / 4 + 1) * 0.35 + rnd() * 0.12,
  }));
}

export function generateVolumeBins() {
  return [
    { depth: "0–1 m", volume: 0.18, conf: 0.86 },
    { depth: "1–2 m", volume: 0.22, conf: 0.78 },
    { depth: "2–3 m", volume: 0.19, conf: 0.64 },
    { depth: "3–4 m", volume: 0.14, conf: 0.48 },
    { depth: "4–5 m", volume: 0.10, conf: 0.32 },
  ];
}
