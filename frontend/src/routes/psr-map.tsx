import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageShell, Panel } from "@/components/page-shell";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { fetchCraters, fetchMetadata } from "@/lib/api";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/psr-map")({
  head: () => ({
    meta: [
      { title: "PSR Illumination Map — POLARIS" },
      { name: "description", content: "Permanently Shadowed Regions and doubly shadowed crater mapping over the lunar south pole." },
      { property: "og:title", content: "PSR Illumination Map — POLARIS" },
      { property: "og:description", content: "Stereographic projection of PSRs derived from solar geometry simulation." },
    ],
  }),
  component: PsrMapPage,
});

function PsrMapPage() {
  const [showPsr, setShowPsr] = useState(true);
  const [showDoubly, setShowDoubly] = useState(true);
  const [minDiameter, setMinDiameter] = useState(1000); // meters
  const [hoveredCrater, setHoveredCrater] = useState<any | null>(null);

  // Queries
  const { data: craters = [], isLoading: cratersLoading } = useQuery({
    queryKey: ["craters"],
    queryFn: fetchCraters,
  });

  const { data: meta } = useQuery({
    queryKey: ["metadata"],
    queryFn: fetchMetadata,
  });

  // Project lat/lon (lat ~ -80 to -90) to stereographic XY in [0,1]
  const project = (lat: number, lon: number) => {
    // Map south pole: pole (-90) is center (0.5, 0.5)
    // Distance from pole: r proportional to (90 + lat)
    const r = (90.0 + lat) / 10.0; // scale factor
    const theta = (lon * Math.PI) / 180.0;
    return { 
      x: 0.5 + r * 0.4 * Math.sin(theta), 
      y: 0.5 - r * 0.4 * Math.cos(theta) 
    };
  };

  const filteredCraters = craters.filter((c) => {
    // Filter out if not meeting diameter threshold
    if (c.diameter_m < minDiameter) return false;
    
    // Filter based on type
    const isDsc = c.name.includes("DSC");
    if (isDsc && !showDoubly) return false;
    if (!isDsc && !showPsr) return false;
    
    return true;
  });

  return (
    <PageShell
      eyebrow="MODULE · 01"
      title="PSR Illumination Map"
      description="Stereographic projection (80°–90°S). Permanently Shadowed Regions (PSRs) and Doubly Shadowed Craters (DSCs) are registered in PostgreSQL + PostGIS."
    >
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_320px]">
        <Panel 
          title="South Pole stereographic projection" 
          subtitle={cratersLoading ? "Loading database records..." : "Hover a crater element to inspect detailed geometry."}
        >
          {cratersLoading ? (
            <div className="flex aspect-square w-full items-center justify-center rounded-md border border-border/60 bg-background">
              <Loader2 className="h-8 w-8 animate-spin text-ice" />
            </div>
          ) : (
            <div className="relative aspect-square w-full overflow-hidden rounded-md border border-border/60 bg-background">
              <svg viewBox="0 0 600 600" className="absolute inset-0 h-full w-full">
                <defs>
                  <radialGradient id="moon" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="oklch(0.22 0.012 250)" />
                    <stop offset="100%" stopColor="oklch(0.10 0.008 250)" />
                  </radialGradient>
                </defs>
                <circle cx="300" cy="300" r="280" fill="url(#moon)" stroke="oklch(0.28 0.012 250)" />
                {[1, 2, 3].map((i) => (
                  <circle key={i} cx="300" cy="300" r={(280 / 3) * i} fill="none" stroke="oklch(0.22 0.012 250)" strokeDasharray="2 4" />
                ))}
                <line x1="20" y1="300" x2="580" y2="300" stroke="oklch(0.22 0.012 250)" strokeDasharray="2 4" />
                <line x1="300" y1="20" x2="300" y2="580" stroke="oklch(0.22 0.012 250)" strokeDasharray="2 4" />
                <text x="300" y="14" textAnchor="middle" className="fill-muted-foreground text-mono" fontSize="9">0°</text>
                <text x="586" y="304" className="fill-muted-foreground text-mono" fontSize="9">90°E</text>
                <text x="300" y="594" textAnchor="middle" className="fill-muted-foreground text-mono" fontSize="9">180°</text>
                <text x="6" y="304" className="fill-muted-foreground text-mono" fontSize="9">90°W</text>

                {filteredCraters.map((c) => {
                  const { x, y } = project(c.latitude, c.longitude);
                  const cx = x * 600;
                  const cy = y * 600;
                  const isDsc = c.name.includes("DSC");
                  const fill = isDsc ? "oklch(0.55 0.18 290)" : "oklch(0.82 0.14 220)";
                  // Scale circle radius based on diameter
                  const visualRadius = Math.max(8, Math.min(30, c.diameter_m / 400.0));
                  
                  return (
                    <g 
                      key={c.id}
                      onMouseEnter={() => setHoveredCrater(c)}
                      onMouseLeave={() => setHoveredCrater(null)}
                      className="cursor-pointer"
                    >
                      <circle 
                        cx={cx} 
                        cy={cy} 
                        r={visualRadius} 
                        fill={fill} 
                        fillOpacity={isDsc ? 0.65 : 0.45} 
                        stroke={fill} 
                        strokeWidth={hoveredCrater?.id === c.id ? "2" : "1"}
                        strokeOpacity="0.9" 
                      />
                      {isDsc && (
                        <circle cx={cx} cy={cy} r={visualRadius + 4} fill="none" stroke="oklch(0.82 0.14 220)" strokeOpacity="0.5">
                          <animate attributeName="r" from={visualRadius + 2} to={visualRadius + 8} dur="2.4s" repeatCount="indefinite" />
                          <animate attributeName="stroke-opacity" from="0.5" to="0" dur="2.4s" repeatCount="indefinite" />
                        </circle>
                      )}
                    </g>
                  );
                })}
                <circle cx="300" cy="300" r="3" fill="oklch(0.93 0.012 230)" />
                <text x="306" y="296" className="fill-foreground text-mono" fontSize="10">90°S</text>
              </svg>
            </div>
          )}
        </Panel>

        <div className="space-y-3">
          {hoveredCrater ? (
            <Panel title="Crater telemetry" subtitle={hoveredCrater.name}>
              <div className="space-y-2 text-xs text-[#E0F2FE]">
                <div className="flex justify-between border-b border-border/30 pb-1">
                  <span className="text-muted-foreground">Coordinates</span>
                  <span className="text-mono">{hoveredCrater.latitude.toFixed(4)}°S, {hoveredCrater.longitude.toFixed(4)}°E</span>
                </div>
                <div className="flex justify-between border-b border-border/30 pb-1">
                  <span className="text-muted-foreground">Area</span>
                  <span className="text-mono text-ice">{hoveredCrater.area_km2.toFixed(3)} km²</span>
                </div>
                <div className="flex justify-between border-b border-border/30 pb-1">
                  <span className="text-muted-foreground">Diameter</span>
                  <span className="text-mono">{hoveredCrater.diameter_m.toFixed(1)} m</span>
                </div>
                <div className="flex justify-between border-b border-border/30 pb-1">
                  <span className="text-muted-foreground">Est. Depth</span>
                  <span className="text-mono">{hoveredCrater.depth_m.toFixed(1)} m</span>
                </div>
                <div className="flex justify-between border-b border-border/30 pb-1">
                  <span className="text-muted-foreground">Est. Temp</span>
                  <span className="text-mono text-purple-400">{hoveredCrater.estimated_temp_k} K (-233°C)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Illumination</span>
                  <span className="text-mono text-success">0.00%</span>
                </div>
              </div>
            </Panel>
          ) : (
            <Panel title="Crater telemetry" subtitle="No crater selected">
              <p className="text-xs text-muted-foreground">Hover over any mapping element on the projection to read real-time dimensions.</p>
            </Panel>
          )}

          <Panel title="Layers">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="psr" className="text-sm">PSR (Permanently Shadowed)</Label>
                <Switch id="psr" checked={showPsr} onCheckedChange={setShowPsr} />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="dbl" className="text-sm">DSC (Doubly Shadowed)</Label>
                <Switch id="dbl" checked={showDoubly} onCheckedChange={setShowDoubly} />
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <Label className="text-sm">Min Diameter</Label>
                  <span className="text-mono text-[11px] text-ice">{minDiameter} m</span>
                </div>
                <Slider value={[minDiameter]} min={200} max={5000} step={100} onValueChange={(v) => setMinDiameter(v[0])} />
              </div>
            </div>
          </Panel>
          <Panel title="Legend">
            <ul className="space-y-2 text-sm">
              <Swatch color="oklch(0.55 0.18 290)" label="Doubly shadowed (DSC)" />
              <Swatch color="oklch(0.82 0.14 220)" label="Permanently shadowed (PSR)" />
              <Swatch color="oklch(0.18 0.012 250)" label="Illuminated surface" />
            </ul>
          </Panel>
          <Panel title="Database context">
            <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-mono text-[11px]">
              <dt className="text-muted-foreground">Engine source</dt><dd>FastAPI / PostgreSQL</dd>
              <dt className="text-muted-foreground">DB Schema</dt><dd>PostGIS Spatials</dd>
              <dt className="text-muted-foreground">Total Craters</dt><dd>{craters.length}</dd>
              <dt className="text-muted-foreground">Solar elevation</dt><dd>{meta ? `${meta.solar_elevation_deg.toFixed(2)}°` : "5.52°"}</dd>
            </dl>
          </Panel>
        </div>
      </div>
    </PageShell>
  );
}

function Swatch({ color, label }: { color: string; label: string }) {
  return (
    <li className="flex items-center gap-2">
      <span className="inline-block h-3 w-3 rounded-sm" style={{ background: color }} />
      <span className="text-foreground">{label}</span>
    </li>
  );
}
