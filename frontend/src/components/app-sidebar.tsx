import { Link, useRouterState } from "@tanstack/react-router";
import {
  Activity,
  Compass,
  Crosshair,
  Gauge,
  Globe2,
  Layers,
  Mountain,
  Route as RouteIcon,
  Snowflake,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const nav = [
  { title: "Mission Overview", url: "/", icon: Gauge },
  { title: "PSR Illumination Map", url: "/psr-map", icon: Globe2 },
  { title: "DFSAR Polarimetry", url: "/polarimetry", icon: Activity },
  { title: "AI Ice Classifier", url: "/ice-classifier", icon: Snowflake },
  { title: "Terrain Morphology", url: "/terrain", icon: Mountain },
  { title: "Landing Site Selector", url: "/landing-sites", icon: Crosshair },
  { title: "Rover Path Planner", url: "/rover-planner", icon: RouteIcon },
  { title: "Ice Volume Estimator", url: "/ice-volume", icon: Layers },
];

export function AppSidebar() {
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="relative grid h-8 w-8 place-items-center rounded-md bg-gradient-to-br from-primary/80 to-primary/30">
            <Compass className="h-4 w-4 text-primary-foreground" />
            <span className="absolute -inset-px rounded-md ring-1 ring-primary/40" />
          </div>
          <div className="leading-tight">
            <div className="text-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Antariksh</div>
            <div className="text-sm font-semibold text-foreground">POLARIS</div>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-mono text-[10px] uppercase tracking-[0.2em]">
            Pipeline
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {nav.map((item) => {
                const active = pathname === item.url;
                return (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton asChild isActive={active}>
                      <Link to={item.url} className="flex items-center gap-2">
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border">
        <div className="px-3 py-2 text-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          BAH 2026 · PS-08
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
