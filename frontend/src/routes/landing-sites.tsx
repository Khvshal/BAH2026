import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Crosshair, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { PageShell, Panel } from "@/components/page-shell";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { scoreLandingSites, fetchLandingCandidates } from "@/lib/api";

export const Route = createFileRoute("/landing-sites")({
  head: () => ({
    meta: [
      { title: "Landing Site Selector — POLARIS" },
      { name: "description", content: "Multi-criteria scoring of candidate lunar polar landing sites: ice, safety, illumination, comms." },
      { property: "og:title", content: "Landing Site Selector — POLARIS" },
      { property: "og:description", content: "Tune mission weights to rank candidate landing sites by composite score." },
    ],
  }),
  component: LandingSites,
});

function LandingSites() {
  const [wIce, setIce] = useState(40);
  const [wSafety, setSafety] = useState(30);
  const [wIllum, setIllum] = useState(20);
  const [wComms, setComms] = useState(10);
  
  const total = wIce + wSafety + wIllum + wComms + 10; // including fixed access weight of 10

  const { data: ranked = [], isLoading } = useQuery({
    queryKey: ["landingSites", wIce, wSafety, wIllum, wComms],
    queryFn: () => scoreLandingSites({
      ice_proximity_weight: wIce / total,
      terrain_safety_weight: wSafety / total,
      solar_illumination_weight: wIllum / total,
      dsc_access_weight: 10 / total,
      comm_los_weight: wComms / total
    }),
    refetchOnWindowFocus: false,
  });

  return (
    <PageShell
      eyebrow="MODULE · 05"
      title="Landing Site Selector"
      description="Composite scoring across ice potential, terrain safety, solar illumination duration and Earth comms window. Tune weights to update PostgreSQL database records live."
      actions={<Button size="sm" className="bg-ice text-[#070B18] font-semibold border-none hover:bg-ice/85">Export to mission planner</Button>}
    >
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[320px_1fr]">
        <Panel title="Mission weights" subtitle={`Σ = ${total}`}>
          <div className="space-y-4">
            <WeightSlider label="Ice proximity weight" value={wIce} onChange={setIce} color="oklch(0.82 0.14 220)" />
            <WeightSlider label="Terrain safety weight" value={wSafety} onChange={setSafety} color="oklch(0.72 0.16 160)" />
            <WeightSlider label="Illumination weight" value={wIllum} onChange={setIllum} color="oklch(0.78 0.16 80)" />
            <WeightSlider label="Comms window weight" value={wComms} onChange={setComms} color="oklch(0.55 0.18 290)" />
            <div className="text-[10px] text-muted-foreground text-mono uppercase border-t border-border/30 pt-3">
              * Access capability: fixed at 10 (10%)
            </div>
          </div>
        </Panel>

        <Panel title="Ranked candidates" subtitle={isLoading ? "Recomputing rankings..." : "PostgreSQL query completed"}>
          {isLoading && ranked.length === 0 ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-ice" />
            </div>
          ) : (
            <div className="space-y-3">
              {ranked.map((s, i) => (
                <div key={s.id} className={`rounded-md border p-3 ${i === 0 ? "ice-glow border-ice/40 bg-ice/5" : "border-border/60 bg-background/40"}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-mono text-[11px] w-6 text-muted-foreground">#{i + 1}</span>
                      <Crosshair className={`h-4 w-4 ${i === 0 ? "text-ice" : "text-muted-foreground"}`} />
                      <span className="text-sm font-medium text-foreground">{s.name}</span>
                      <span className="text-mono text-[11px] text-muted-foreground">
                        {s.latitude.toFixed(4)}°S, {s.longitude.toFixed(4)}°E
                      </span>
                      {i === 0 && <Badge className="bg-ice/20 text-ice hover:bg-ice/20">Recommended</Badge>}
                      <Badge variant="outline" className="text-mono text-[10px] capitalize">Risk: {s.risk_level}</Badge>
                    </div>
                    <div className="text-mono text-sm text-ice">{(s.composite_score * 100).toFixed(1)}</div>
                  </div>
                  <div className="mt-3 grid grid-cols-5 gap-2 text-mono text-[11px]">
                    <MiniBar label="Ice" v={s.ice_proximity_score} color="oklch(0.82 0.14 220)" />
                    <MiniBar label="Safety" v={s.terrain_safety_score} color="oklch(0.72 0.16 160)" />
                    <MiniBar label="Illum" v={s.solar_illumination_score} color="oklch(0.78 0.16 80)" />
                    <MiniBar label="Access" v={s.dsc_access_score} color="oklch(0.62 0.22 25)" />
                    <MiniBar label="Comms" v={s.comm_los_score} color="oklch(0.55 0.18 290)" />
                  </div>
                  <div className="mt-2 text-mono text-[11px] text-muted-foreground">
                    <span>MCDA Score: {s.composite_score.toFixed(3)} | DB Reference ID: {s.id}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </PageShell>
  );
}

function WeightSlider({ label, value, onChange, color }: { label: string; value: number; onChange: (v: number) => void; color: string }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <Label className="flex items-center gap-2 text-sm">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
          {label}
        </Label>
        <span className="text-mono text-[11px] text-foreground">{value}</span>
      </div>
      <Slider value={[value]} max={100} step={5} onValueChange={(v) => onChange(v[0])} />
    </div>
  );
}

function MiniBar({ label, v, color }: { label: string; v: number; color: string }) {
  return (
    <div>
      <div className="flex items-center justify-between"><span className="text-muted-foreground">{label}</span><span>{(v * 100).toFixed(0)}</span></div>
      <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full" style={{ width: `${v * 100}%`, background: color }} />
      </div>
    </div>
  );
}
