import { createFileRoute } from "@tanstack/react-router";
import { PageShell, Panel } from "@/components/page-shell";
import { Badge } from "@/components/ui/badge";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchPsrMaps, fetchMetadata, triggerPsrProcessing, WS_BASE_URL } from "@/lib/api";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Loader2, Play } from "lucide-react";

export const Route = createFileRoute("/terrain")({
  head: () => ({
    meta: [
      { title: "Terrain Morphology — POLARIS" },
      { name: "description", content: "OHRC-derived slope, roughness and boulder density maps for traversability assessment." },
      { property: "og:title", content: "Terrain Morphology — POLARIS" },
      { property: "og:description", content: "Photogrammetric DEM with slope and roughness layers from OHRC stereo pairs." },
    ],
  }),
  component: Terrain,
});

function Terrain() {
  const queryClient = useQueryClient();
  const [processing, setProcessing] = useState(false);
  const [log, setLog] = useState<{ step: string; progress: number; message: string } | null>(null);

  // Queries
  const { data: maps, isLoading: mapsLoading, error: mapsError } = useQuery({
    queryKey: ["psrMaps"],
    queryFn: fetchPsrMaps,
    refetchOnWindowFocus: false,
  });

  const { data: meta, isLoading: metaLoading } = useQuery({
    queryKey: ["metadata"],
    queryFn: fetchMetadata,
    refetchOnWindowFocus: false,
  });

  // Handle processing trigger and WebSocket tracking
  const handleProcess = async () => {
    try {
      setProcessing(true);
      setLog({ step: "Init", progress: 5, message: "Establishing WebSocket link..." });

      // Open WebSocket
      const ws = new WebSocket(WS_BASE_URL);
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        setLog(msg);
        if (msg.step === "complete" || msg.progress === 100) {
          setTimeout(() => {
            setProcessing(false);
            setLog(null);
            queryClient.invalidateQueries({ queryKey: ["psrMaps"] });
            queryClient.invalidateQueries({ queryKey: ["metadata"] });
          }, 1500);
          ws.close();
        }
      };

      ws.onerror = (err) => {
        console.error("WS error:", err);
      };

      ws.onclose = () => {
        console.log("WS closed");
      };

      // Trigger request
      await triggerPsrProcessing();
    } catch (err) {
      console.error(err);
      setProcessing(false);
      setLog(null);
    }
  };

  const hasData = maps && meta;

  return (
    <PageShell
      eyebrow="MODULE · 04"
      title="Terrain Morphology Analyzer"
      description="OHRC stereo photogrammetry → 1 m/px DEM. Slope, aspect, roughness and boulder density fused into a traversability index."
      actions={
        <Button
          onClick={handleProcess}
          disabled={processing}
          className="bg-ice hover:bg-ice/85 text-[#070B18] font-semibold border-none rounded shadow-[0_0_15px_rgba(0,212,255,0.4)] transition-all"
        >
          {processing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4 fill-current" />
              Compute Terrain Products
            </>
          )}
        </Button>
      }
    >
      {/* Processing Modal Overlay */}
      {processing && log && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#070B18]/85 backdrop-blur-md">
          <div className="w-full max-w-md border border-border bg-[#0D1426] p-6 rounded-lg shadow-2xl">
            <h3 className="text-lg font-semibold text-ice">Analyzing Terrain Datasets</h3>
            <p className="text-xs text-muted-foreground mt-1">Real-time telemetry link with ISRO pipeline</p>
            
            <div className="mt-4 flex items-center justify-between text-mono text-xs">
              <span className="text-ice">{log.step}</span>
              <span className="text-muted-foreground">{log.progress}%</span>
            </div>
            
            <div className="mt-2 h-2 w-full bg-surface/30 rounded overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-ice to-purple-500 transition-all duration-300"
                style={{ width: `${log.progress}%` }}
              />
            </div>
            
            <div className="mt-4 p-3 bg-black/40 rounded border border-border/30 text-mono text-[11px] text-[#A0AEC0]">
              <span className="text-[#00E676] mr-1">$</span>
              {log.message}
            </div>
          </div>
        </div>
      )}

      {/* KPI Stats */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <Stat 
          label="Mean slope" 
          value={meta ? `${meta.mean_slope_deg.toFixed(2)}°` : "---"} 
        />
        <Stat 
          label="Max slope" 
          value={meta ? `${meta.max_slope_deg.toFixed(2)}°` : "---"} 
          sub="hazard limit: >15°" 
          tone={meta && meta.max_slope_deg > 15 ? "warn" : "ice"} 
        />
        <Stat 
          label="Mean roughness" 
          value={meta ? `${meta.mean_roughness_m.toFixed(3)} m` : "---"} 
          sub="RMS height deviation" 
        />
        <Stat 
          label="PSR coverage" 
          value={meta ? `${meta.psr_area_km2.toFixed(3)} km²` : "---"} 
          tone="ok" 
        />
      </div>

      {/* Map views */}
      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Panel title="Elevation Model (DEM)" subtitle="Derived from Lola DEM 5m/px">
          {mapsLoading ? (
            <div className="flex h-64 items-center justify-center rounded bg-card/25 border border-border/40">
              <Loader2 className="h-8 w-8 animate-spin text-ice" />
            </div>
          ) : mapsError ? (
            <div className="flex h-64 items-center justify-center rounded bg-red-900/10 text-red-500 border border-red-500/20 text-xs">
              Error fetching DEM map. Run processing first.
            </div>
          ) : maps?.dem_img ? (
            <div className="overflow-hidden rounded border border-border bg-black/20">
              <img src={maps.dem_img} alt="DEM Elevation" className="w-full h-auto object-cover" />
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded bg-card/25 border border-border/40 text-muted-foreground text-xs">
              No Elevation Map loaded
            </div>
          )}
        </Panel>

        <Panel title="Slope Profile" subtitle="Calculated via Sobel Gradients">
          {mapsLoading ? (
            <div className="flex h-64 items-center justify-center rounded bg-card/25 border border-border/40">
              <Loader2 className="h-8 w-8 animate-spin text-ice" />
            </div>
          ) : mapsError ? (
            <div className="flex h-64 items-center justify-center rounded bg-red-900/10 text-red-500 border border-red-500/20 text-xs">
              Error fetching Slope map.
            </div>
          ) : maps?.slope_img ? (
            <div className="overflow-hidden rounded border border-border bg-black/20">
              <img src={maps.slope_img} alt="Slope map" className="w-full h-auto object-cover" />
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded bg-card/25 border border-border/40 text-muted-foreground text-xs">
              No Slope Map loaded
            </div>
          )}
        </Panel>

        <Panel title="Traversability Hazard Map" subtitle="Fused risk index (Slope + Roughness)">
          {mapsLoading ? (
            <div className="flex h-64 items-center justify-center rounded bg-card/25 border border-border/40">
              <Loader2 className="h-8 w-8 animate-spin text-ice" />
            </div>
          ) : maps?.hazard_img ? (
            <div className="overflow-hidden rounded border border-border bg-black/20">
              <img src={maps.hazard_img} alt="Hazard map" className="w-full h-auto object-cover" />
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded bg-card/25 border border-border/40 text-muted-foreground text-xs">
              No Hazard Map loaded
            </div>
          )}
        </Panel>

        <Panel title="Base OHRC Image" subtitle="Sub-sampled Chandrayaan-2 base image">
          {mapsLoading ? (
            <div className="flex h-64 items-center justify-center rounded bg-card/25 border border-border/40">
              <Loader2 className="h-8 w-8 animate-spin text-ice" />
            </div>
          ) : maps?.ohrc_img ? (
            <div className="overflow-hidden rounded border border-border bg-black/20">
              <img src={maps.ohrc_img} alt="OHRC base image" className="w-full h-auto object-cover" />
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded bg-card/25 border border-border/40 text-muted-foreground text-xs">
              OHRC base image pre-processing required
            </div>
          )}
        </Panel>
      </div>

      <div className="mt-3">
        <Panel title="OHRC processing chain">
          <div className="flex flex-wrap items-center gap-2 text-mono text-[11px]">
            {[
              "OHRC L1 stereo pair",
              "Bundle adjustment",
              "Dense matching · NCC",
              "DEM @ 5 m/px",
              "Slope/aspect/roughness",
              "Hazard Fusion index",
              "PostgreSQL + PostGIS Sync",
            ].map((s, i) => (
              <span key={s} className="flex items-center gap-2">
                <Badge variant="outline" className="text-mono text-[10px]">{(i + 1).toString().padStart(2, "0")}</Badge>
                <span>{s}</span>
                {i < 6 && <span className="text-muted-foreground">→</span>}
              </span>
            ))}
          </div>
        </Panel>
      </div>
    </PageShell>
  );
}

function Stat({ label, value, sub, tone = "ice" }: { label: string; value: string; sub?: string; tone?: "ice" | "ok" | "warn" }) {
  const c = tone === "ok" ? "text-success" : tone === "warn" ? "text-warning" : "text-ice";
  return (
    <div className="rounded-lg border border-border/70 bg-card/60 p-4">
      <div className="text-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tracking-tight ${c}`}>{value}</div>
      {sub && <div className="text-mono text-[11px] text-muted-foreground">{sub}</div>}
    </div>
  );
}
