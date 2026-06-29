import { MISSION } from "@/lib/mock-data";
import { SidebarTrigger } from "@/components/ui/sidebar";

export function StatusBar() {
  return (
    <header className="sticky top-0 z-30 flex h-12 items-center gap-3 border-b border-border bg-background/80 px-3 backdrop-blur">
      <SidebarTrigger />
      <div className="flex items-center gap-2">
        <span className="relative inline-flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success/70" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
        </span>
        <span className="text-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          LINK · NOMINAL
        </span>
      </div>
      <div className="hidden items-center gap-4 md:flex">
        <Pill label="Mission" value={MISSION.name} />
        <Pill label="Target" value={MISSION.target} />
        <Pill label="Cycle" value={MISSION.cycle} />
      </div>
      <div className="ml-auto text-mono text-[11px] text-muted-foreground">
        UTC {MISSION.utc}
      </div>
    </header>
  );
}

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border/70 bg-card/40 px-2 py-1">
      <span className="text-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
      <span className="text-mono text-[11px] text-foreground">{value}</span>
    </div>
  );
}
