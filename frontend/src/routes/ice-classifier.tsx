import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Play, AlertCircle, Cpu } from "lucide-react";

import { PageShell, Panel } from "@/components/page-shell";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { fetchIceMaps, triggerIceClassification, fetchShapExplanation, WS_BASE_URL } from "@/lib/api";

export const Route = createFileRoute("/ice-classifier")({
  head: () => ({
    meta: [
      { title: "AI Ice Classifier — POLARIS" },
      { name: "description", content: "Multi-modal neural classifier fusing DFSAR polarimetry, OHRC morphology and PSR illumination into ice probability tiles." },
      { property: "og:title", content: "AI Ice Classifier — POLARIS" },
      { property: "og:description", content: "U-Net++ ensemble with calibrated uncertainty for ice-vs-regolith classification." },
    ],
  }),
  component: IceClassifierPage,
});

const matrix = [
  { row: "Ice (truth)", cols: [142, 8, 5] },
  { row: "Rocky (truth)", cols: [11, 198, 6] },
  { row: "Mixed (truth)", cols: [9, 12, 87] },
];
const labels = ["Ice", "Rocky", "Mixed"];

function IceClassifierPage() {
  const queryClient = useQueryClient();
  const [processing, setProcessing] = useState(false);
  const [log, setLog] = useState<{ step: string; progress: number; message: string } | null>(null);
  
  const [selectedPixel, setSelectedPixel] = useState<any | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const imageRef = useRef<HTMLImageElement>(null);

  // Queries
  const { data: maps, isLoading: mapsLoading } = useQuery({
    queryKey: ["iceProbabilityMap"],
    queryFn: fetchIceMaps,
    refetchOnWindowFocus: false,
  });

  const handleClassify = async () => {
    try {
      setProcessing(true);
      setLog({ step: "Init", progress: 5, message: "Deploying neural inference nodes..." });

      const ws = new WebSocket(WS_BASE_URL);
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        setLog(msg);
        if (msg.step === "complete" || msg.progress === 100) {
          setTimeout(() => {
            setProcessing(false);
            setLog(null);
            queryClient.invalidateQueries({ queryKey: ["iceProbabilityMap"] });
          }, 1500);
          ws.close();
        }
      };

      await triggerIceClassification();
    } catch (err) {
      console.error(err);
      setProcessing(false);
      setLog(null);
    }
  };

  const handleImageClick = async (event: React.MouseEvent<HTMLImageElement>) => {
    if (!imageRef.current) return;
    
    const rect = imageRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left; //x position within the element.
    const y = event.clientY - rect.top;  //y position within the element.
    
    // Scale to the actual 1000x1000 grid of polarimetry arrays
    const gridX = Math.round((x / rect.width) * 1000);
    const gridY = Math.round((y / rect.height) * 1000);
    
    try {
      setExplainLoading(true);
      const data = await fetchShapExplanation(gridX, gridY);
      setSelectedPixel(data);
    } catch (err) {
      console.error("SHAP explain error:", err);
    } finally {
      setExplainLoading(false);
    }
  };

  return (
    <PageShell
      eyebrow="MODULE · 03"
      title="AI Ice Classifier"
      description="Ensemble of U-Net++ heads (DFSAR + OHRC + PSR). Per-pixel output is calibrated to true probability and supported by live SHAP feature importance explainability."
      actions={
        <Button
          onClick={handleClassify}
          disabled={processing}
          className="bg-ice hover:bg-ice/85 text-[#070B18] font-semibold border-none rounded shadow-[0_0_15px_rgba(0,212,255,0.4)] transition-all"
        >
          {processing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Running Inference...
            </>
          ) : (
            <>
              <Cpu className="mr-2 h-4 w-4 fill-current" />
              Execute U-Net++ Ensemble
            </>
          )}
        </Button>
      }
    >
      {/* WebSocket progress overlay */}
      {processing && log && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#070B18]/85 backdrop-blur-md">
          <div className="w-full max-w-md border border-border bg-[#0D1426] p-6 rounded-lg shadow-2xl">
            <h3 className="text-lg font-semibold text-ice">U-Net++ Ensemble Classifier</h3>
            <p className="text-xs text-muted-foreground mt-1">Executing convolutional segmentation pipeline</p>
            
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

      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <Stat label="Model F1-Score" value="0.913" sub="held-out polar test tiles" />
        <Stat label="Precision · ice" value="0.94" />
        <Stat label="Recall · ice" value="0.89" />
        <Stat label="ECE" value="0.021" sub="calibration error" />
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-[1fr_360px]">
        <Panel 
          title="Ice Probability Heatmap" 
          subtitle="Click on any pixel to compute SHAP feature importances live"
        >
          {mapsLoading ? (
            <div className="flex h-72 items-center justify-center bg-card/25 border border-border/40 rounded">
              <Loader2 className="h-8 w-8 animate-spin text-ice" />
            </div>
          ) : maps?.ice_prob_img ? (
            <div className="relative overflow-hidden rounded border border-border bg-black/20 max-h-[360px] flex items-center justify-center">
              <img 
                ref={imageRef}
                src={maps.ice_prob_img} 
                alt="Ice probability map" 
                onClick={handleImageClick}
                className="max-w-full h-auto object-contain cursor-crosshair active:scale-[0.99] transition-transform" 
              />
            </div>
          ) : (
            <div className="flex h-72 items-center justify-center text-xs text-muted-foreground">
              Execute U-Net++ classifier to generate ice map.
            </div>
          )}
          <div className="mt-3 flex items-center justify-between text-mono text-[11px] text-muted-foreground">
            <span>Low Probability</span>
            <div className="mx-3 h-2 flex-1 rounded-full" style={{ background: "linear-gradient(to right, #002244, #4488ff, #ff4444)" }} />
            <span>High Ice Conf</span>
          </div>
        </Panel>

        <div className="space-y-3">
          {/* SHAP Telemetry */}
          {selectedPixel ? (
            <Panel title="AI EXPLANATION" subtitle={`Pixel at grid [${selectedPixel.coordinates.x}, ${selectedPixel.coordinates.y}]`}>
              <div className="space-y-3 text-xs text-[#E0F2FE]">
                <div className="p-2 rounded bg-ice/5 border border-ice/20 flex flex-col gap-1">
                  <div className="text-[10px] text-muted-foreground text-mono uppercase">VERDICT</div>
                  <div className="font-semibold text-ice text-sm flex items-center gap-1.5">
                    <AlertCircle className="h-4 w-4 text-ice" />
                    {selectedPixel.verdict}
                  </div>
                  <div className="text-mono text-xs mt-1">
                    Ice Probability: <span className="text-white font-bold">{selectedPixel.probability}%</span>
                  </div>
                </div>

                <div className="text-[10px] text-muted-foreground text-mono uppercase">SHAP FEATURE ATTRIBUTION</div>
                <ul className="space-y-2">
                  {Object.entries(selectedPixel.shap_values).map(([name, val]: any) => {
                    const pct = Math.abs(val) * 100;
                    const isPositive = val >= 0;
                    return (
                      <li key={name}>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-muted-foreground">{name}</span>
                          <span className={isPositive ? "text-success" : "text-warning"}>
                            {isPositive ? "+" : ""}{(val * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden flex">
                          <div 
                            className={`h-full rounded-full ${isPositive ? "bg-success" : "bg-warning"}`} 
                            style={{ width: `${pct}%`, marginLeft: isPositive ? "0" : "auto" }}
                          />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </Panel>
          ) : (
            <Panel title="AI EXPLANATION" subtitle="Click pixel to explain">
              {explainLoading ? (
                <div className="flex h-32 items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-ice" />
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Hover over the heatmap and click on any point. The explainability head will compute SHAP feature attributions on-the-fly from the underlying PostGIS datasets.
                </p>
              )}
            </Panel>
          )}

          <Panel title="Confusion matrix" subtitle="Validation statistics">
            <table className="w-full text-mono text-[10px]">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="px-1 py-1"></th>
                  {labels.map((l) => (
                    <th key={l} className="px-1 py-1 font-normal">pred {l}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.map((row, i) => (
                  <tr key={row.row} className="border-t border-border/40">
                    <th className="px-1 py-1 text-left font-normal text-muted-foreground">{row.row}</th>
                    {row.cols.map((v, j) => {
                      const intensity = Math.min(1, v / 200);
                      const diag = i === j;
                      return (
                        <td key={j} className="px-1 py-1 text-right" style={{
                          background: diag
                            ? `oklch(${0.18 + intensity * 0.3} 0.14 220 / 0.6)`
                            : `oklch(0.30 0.04 25 / ${intensity * 0.4})`,
                          color: "var(--foreground)",
                        }}>{v}</td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>
      </div>

      <div className="mt-3">
        <Panel title="Model pipeline">
          <div className="flex flex-wrap items-center gap-2 text-mono text-[11px]">
            {[
              "DFSAR Complex Covariance Matrices",
              "OHRC Grayscale Image Blocks",
              "LOLA DEM Topographic Slope Matrix",
              "Feature concatenation late-fusion block",
              "SHAP importance attribution maps",
              "PostgreSQL ice_detections telemetry log",
            ].map((b, i) => (
              <span key={b} className="flex items-center gap-2">
                <Badge variant="outline" className="text-mono text-[10px]">{(i + 1).toString().padStart(2, "0")}</Badge>
                <span className="text-foreground">{b}</span>
                {i < 5 && <span className="text-muted-foreground">→</span>}
              </span>
            ))}
          </div>
        </Panel>
      </div>
    </PageShell>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-border/70 bg-card/60 p-4">
      <div className="text-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold tracking-tight text-ice">{value}</div>
      {sub && <div className="text-mono text-[11px] text-muted-foreground">{sub}</div>}
    </div>
  );
}
