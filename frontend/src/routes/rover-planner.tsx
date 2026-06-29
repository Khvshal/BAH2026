import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Pause, Play, RotateCcw, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { PageShell, Panel } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { planRoverPath, fetchLandingCandidates, fetchCraters } from "@/lib/api";

export const Route = createFileRoute("/rover-planner")({
  head: () => ({
    meta: [
      { title: "Rover Path Planner — POLARIS" },
      { name: "description", content: "Energy-aware A* traverse planning over polar terrain with solar budget tracking." },
      { property: "og:title", content: "Rover Path Planner — POLARIS" },
      { property: "og:description", content: "Plan and animate a multi-sol rover route between landing site and ice cache." },
    ],
  }),
  component: RoverPlanner,
});

function RoverPlanner() {
  const [selectedSiteRank, setSelectedSiteRank] = useState(1);
  const [selectedCraterId, setSelectedCraterId] = useState(1);
  
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);

  // Queries
  const { data: sites = [] } = useQuery({
    queryKey: ["landingCandidates"],
    queryFn: fetchLandingCandidates,
  });

  const { data: craters = [] } = useQuery({
    queryKey: ["craters"],
    queryFn: fetchCraters,
  });

  const { data: plan, isLoading: planLoading } = useQuery({
    queryKey: ["traversePlan", selectedSiteRank, selectedCraterId],
    queryFn: () => planRoverPath(selectedSiteRank, selectedCraterId),
    refetchOnWindowFocus: false,
  });

  const waypoints = plan?.energy_profile || [];
  const totalDistance = plan?.distance_m || 0;
  const totalTime = plan?.estimated_time_hours || 0;
  const maxSlope = plan?.max_slope_deg || 0;

  useEffect(() => {
    if (!playing || waypoints.length === 0) return;
    const id = setInterval(() => {
      setStep((s) => {
        if (s >= waypoints.length - 1) {
          setPlaying(false);
          return s;
        }
        return s + 1;
      });
    }, 150); // fast animation ticks
    return () => clearInterval(id);
  }, [playing, waypoints.length]);

  const cur = waypoints[step] || { grid_x: 0, grid_y: 0, battery_pct: 100, solar_in_w: 150, drive_w: 100, status: "STANDBY" };

  // Scale grid coords (0-3200) to SVG viewport (800x500)
  const mapX = (gx: number) => (gx / 3200.0) * 800;
  const mapY = (gy: number) => (gy / 3200.0) * 500;

  return (
    <PageShell
      eyebrow="MODULE · 06"
      title="Rover Path Planner"
      description="Energy-aware A* over slope + roughness + illumination cost surface. Solar recharge is modeled along traverse; battery is maintained above 20% limit."
      actions={
        <>
          <Button size="sm" variant="outline" onClick={() => setStep(0)} className="text-mono text-[11px]">
            <RotateCcw className="mr-2 h-3.5 w-3.5" /> Reset
          </Button>
          <Button 
            size="sm" 
            onClick={() => setPlaying((p) => !p)} 
            disabled={waypoints.length === 0}
            className="text-[#070B18] font-semibold bg-ice hover:bg-ice/85 text-mono text-[11px]"
          >
            {playing ? <Pause className="mr-2 h-3.5 w-3.5 fill-[#070B18]" /> : <Play className="mr-2 h-3.5 w-3.5 fill-[#070B18]" />}
            {playing ? "Pause" : "Animate"}
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_320px]">
        <Panel 
          title="Weighted A* Traverse path" 
          subtitle={planLoading ? "Computing pathfinding weights..." : "Optimal route plotted on terrain cost grid"}
        >
          {planLoading ? (
            <div className="flex aspect-[16/10] w-full items-center justify-center rounded-md border border-border/60 bg-background">
              <Loader2 className="h-8 w-8 animate-spin text-ice" />
            </div>
          ) : (
            <div className="overflow-hidden rounded-md border border-border/60 bg-black/40">
              <svg viewBox="0 0 800 500" className="h-auto w-full">
                {/* background noise grid representing cost surface */}
                {Array.from({ length: 50 * 32 }, (_, idx) => {
                  const x = idx % 50, y = Math.floor(idx / 50);
                  const v = (Math.sin(x / 4) + Math.cos(y / 3) + Math.sin((x + y) / 6)) / 3 + 0.5;
                  const c = v > 0.7 ? "oklch(0.30 0.06 25 / 0.55)" : v > 0.45 ? "oklch(0.32 0.04 80 / 0.45)" : "oklch(0.20 0.015 250 / 0.6)";
                  return <rect key={idx} x={x * 16} y={y * 16} width={16} height={16} fill={c} />;
                })}
                
                {/* Full planned path */}
                {waypoints.length > 0 && (
                  <path
                    d={`M ${waypoints.map((w) => `${mapX(w.grid_x)} ${mapY(w.grid_y)}`).join(" L ")}`}
                    fill="none"
                    stroke="oklch(0.82 0.14 220)"
                    strokeOpacity="0.4"
                    strokeWidth="2"
                    strokeDasharray="4 4"
                  />
                )}
                
                {/* Traveled path */}
                {waypoints.length > 0 && (
                  <path
                    d={`M ${waypoints.slice(0, step + 1).map((w) => `${mapX(w.grid_x)} ${mapY(w.grid_y)}`).join(" L ")}`}
                    fill="none"
                    stroke="oklch(0.82 0.14 220)"
                    strokeWidth="3"
                  />
                )}

                {/* Start and Goal pins */}
                {waypoints.length > 0 && (
                  <>
                    {/* Start (Landing Site) */}
                    <g transform={`translate(${mapX(waypoints[0].grid_x)} ${mapY(waypoints[0].grid_y)})`}>
                      <circle r="6" fill="#00E676" />
                      <text x="10" y="4" className="fill-foreground text-mono" fontSize="9">START</text>
                    </g>
                    {/* Goal (Crater Target) */}
                    <g transform={`translate(${mapX(waypoints[waypoints.length-1].grid_x)} ${mapY(waypoints[waypoints.length-1].grid_y)})`}>
                      <circle r="6" fill="#FF5722" />
                      <text x="10" y="4" className="fill-foreground text-mono" fontSize="9">TARGET</text>
                    </g>
                  </>
                )}

                {/* Animated Rover marker */}
                {waypoints.length > 0 && (
                  <g transform={`translate(${mapX(cur.grid_x)} ${mapY(cur.grid_y)})`}>
                    <circle r="12" fill="oklch(0.82 0.14 220)" fillOpacity="0.3" className="animate-ping" />
                    <circle r="5" fill="#00D4FF" stroke="white" strokeWidth="1.5" />
                  </g>
                )}
              </svg>
            </div>
          )}
        </Panel>

        <div className="space-y-3">
          {/* Site and Target selection */}
          <Panel title="Plan parameters">
            <div className="space-y-2 text-xs">
              <div>
                <Label className="text-[10px] text-muted-foreground text-mono uppercase">Select Landing Site</Label>
                <select 
                  value={selectedSiteRank}
                  onChange={(e) => { setSelectedSiteRank(Number(e.target.value)); setStep(0); }}
                  className="w-full mt-1 bg-surface border border-border/50 text-foreground p-1 rounded font-mono"
                >
                  {sites.map(s => (
                    <option key={s.id} value={s.rank}>Ellipse #{s.rank} (Score: {s.composite_score})</option>
                  ))}
                  {sites.length === 0 && <option value={1}>Ellipse #1</option>}
                </select>
              </div>

              <div>
                <Label className="text-[10px] text-muted-foreground text-mono uppercase">Select Target PSR</Label>
                <select 
                  value={selectedCraterId}
                  onChange={(e) => { setSelectedCraterId(Number(e.target.value)); setStep(0); }}
                  className="w-full mt-1 bg-surface border border-border/50 text-foreground p-1 rounded font-mono"
                >
                  {craters.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                  {craters.length === 0 && <option value={1}>PSR-SouthPole-01</option>}
                </select>
              </div>
            </div>
          </Panel>

          <Panel title="Telemetry" subtitle={`Telemetry waypoint ${step + 1} of ${waypoints.length || 1}`}>
            <dl className="space-y-2 text-mono text-[11px]">
              <Row label="Distance mapped" value={`${((step / Math.max(1, waypoints.length - 1)) * (totalDistance / 1000.0)).toFixed(2)} km`} />
              <Row label="Battery state" value={`${cur.battery_pct.toFixed(1)}%` } tone={cur.battery_pct < 30 ? "warn" : "ok"} />
              <Row label="Solar charge rate" value={`${cur.solar_in_w.toFixed(0)} W`} />
              <Row label="Rover draw rate" value={`${cur.drive_w.toFixed(0)} W`} tone={cur.drive_w > 120 ? "warn" : "ok"} />
              <Row label="Motor state" value={cur.status} />
            </dl>
            <div className="mt-3">
              <div className="mb-1 flex items-center justify-between"><span className="text-mono text-[10px] text-muted-foreground">BATTERY CHARGE LEVEL</span></div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${cur.battery_pct}%`, background: cur.battery_pct < 20 ? "#FF5722" : (cur.battery_pct < 50 ? "#FFC107" : "#00D4FF") }}
                />
              </div>
            </div>
          </Panel>

          <Panel title="Path summary metrics">
            <ul className="space-y-2 text-sm">
              <li className="flex items-center justify-between"><span>Total distance</span><span className="text-mono text-[11px] text-ice">{(totalDistance / 1000.0).toFixed(2)} km</span></li>
              <li className="flex items-center justify-between"><span>Est. travel time</span><span className="text-mono text-[11px] text-ice">{totalTime.toFixed(1)} hrs</span></li>
              <li className="flex items-center justify-between"><span>Maximum slope</span><span className="text-mono text-[11px] text-ice">{maxSlope.toFixed(2)}°</span></li>
            </ul>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <Badge variant="outline" className="text-mono text-[10px]">A* pathfinder</Badge>
              <Badge variant="outline" className="text-mono text-[10px]">energy-aware</Badge>
              <Badge variant="outline" className="text-mono text-[10px]">sol-charging</Badge>
            </div>
          </Panel>
        </div>
      </div>
    </PageShell>
  );
}

function Row({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" }) {
  return (
    <div className="flex items-center justify-between border-b border-border/30 pb-2 last:border-0 last:pb-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={tone === "warn" ? "text-warning" : tone === "ok" ? "text-success" : "text-foreground"}>{value}</dd>
    </div>
  );
}
