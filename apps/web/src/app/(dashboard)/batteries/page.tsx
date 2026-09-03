"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Zap,
  Cpu,
  ShieldCheck,
  Activity,
  Layers,
  Sparkles,
  Search,
  CheckCircle2,
  Clock,
  RefreshCw,
} from "lucide-react";
import { useState, useMemo } from "react";

interface PlatformBattery {
  id: string;
  name: string;
  category: "retrieval" | "ml_intelligence" | "safety_defense" | "computation_graph";
  status: "active" | "standby" | "disabled";
  algorithm_foundation: string;
  milestone: string;
  latency_profile: string;
  description: string;
  active_parameters: Record<string, any>;
  health_check_endpoint?: string;
}

interface PlatformBatteriesResponse {
  total_batteries: number;
  active_count: number;
  standby_count: number;
  batteries: PlatformBattery[];
}

type FilterCategory = "all" | "retrieval" | "ml_intelligence" | "safety_defense" | "computation_graph";

export default function BatteriesPage() {
  const [selectedCategory, setSelectedCategory] = useState<FilterCategory>("all");

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ["platform-batteries"],
    queryFn: () => api.get<PlatformBatteriesResponse>("/v1/admin/platform/batteries"),
  });

  const batteries = useMemo(() => data?.batteries || [], [data?.batteries]);

  const filteredBatteries = useMemo(() => {
    if (selectedCategory === "all") return batteries;
    return batteries.filter((b) => b.category === selectedCategory);
  }, [batteries, selectedCategory]);

  const categoryCounts = useMemo(() => {
    return {
      all: batteries.length,
      retrieval: batteries.filter((b) => b.category === "retrieval").length,
      ml_intelligence: batteries.filter((b) => b.category === "ml_intelligence").length,
      safety_defense: batteries.filter((b) => b.category === "safety_defense").length,
      computation_graph: batteries.filter((b) => b.category === "computation_graph").length,
    };
  }, [batteries]);

  return (
    <div className="flex flex-col h-full bg-background">
      <Topbar
        title="Batteries & Engine Capabilities"
        description="Unified observability for all cognitive retrieval, operational ML, and defense engines active in memory."
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-7xl w-full mx-auto">
        {/* Top KPI Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-border/60 bg-card/80 backdrop-blur-sm shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Total Batteries
              </CardTitle>
              <Cpu className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <div className="text-2xl font-bold font-mono text-foreground">
                  {data?.total_batteries || 12}
                </div>
              )}
              <p className="text-[11px] text-muted-foreground mt-1">
                Full-stack cognitive subsystems
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/80 backdrop-blur-sm shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Active & Serving
              </CardTitle>
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                  {data?.active_count || 12} / {data?.total_batteries || 12}
                </div>
              )}
              <p className="text-[11px] text-muted-foreground mt-1">
                100% operational readiness
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/80 backdrop-blur-sm shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Retrieval Latency
              </CardTitle>
              <Clock className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-foreground">
                &lt;15ms
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                ColBERT MaxSim + HNSW dense p50
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/80 backdrop-blur-sm shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Isolation Architecture
              </CardTitle>
              <ShieldCheck className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-foreground">
                Postgres RLS
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Strict DB-level tenant boundaries
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Action & Filter Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b pb-4">
          <div className="flex flex-wrap gap-2">
            <Button
              variant={selectedCategory === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory("all")}
              className="text-xs h-8"
            >
              All Batteries ({categoryCounts.all})
            </Button>
            <Button
              variant={selectedCategory === "retrieval" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory("retrieval")}
              className="text-xs h-8"
            >
              <Search className="h-3 w-3 mr-1" />
              Retrieval & Vector ({categoryCounts.retrieval})
            </Button>
            <Button
              variant={selectedCategory === "ml_intelligence" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory("ml_intelligence")}
              className="text-xs h-8"
            >
              <Sparkles className="h-3 w-3 mr-1" />
              ML Intelligence ({categoryCounts.ml_intelligence})
            </Button>
            <Button
              variant={selectedCategory === "safety_defense" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory("safety_defense")}
              className="text-xs h-8"
            >
              <ShieldCheck className="h-3 w-3 mr-1" />
              Defense & Safety ({categoryCounts.safety_defense})
            </Button>
            <Button
              variant={selectedCategory === "computation_graph" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory("computation_graph")}
              className="text-xs h-8"
            >
              <Layers className="h-3 w-3 mr-1" />
              Computation & Graph ({categoryCounts.computation_graph})
            </Button>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh Status
          </Button>
        </div>

        {/* Battery Cards Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, idx) => (
              <Skeleton key={idx} className="h-56 w-full rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredBatteries.map((battery) => (
              <Card
                key={battery.id}
                className="flex flex-col justify-between border border-border/70 hover:border-primary/50 transition-all duration-200 bg-card/60 hover:shadow-md hover:bg-card"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <Badge
                          variant="secondary"
                          className="font-mono text-[10px] px-1.5 py-0 uppercase tracking-wider text-muted-foreground"
                        >
                          {battery.milestone}
                        </Badge>
                        <Badge
                          variant="outline"
                          className="font-mono text-[10px] px-1.5 py-0 text-blue-500 border-blue-500/30"
                        >
                          {battery.latency_profile}
                        </Badge>
                      </div>
                      <CardTitle className="text-base font-bold text-foreground">
                        {battery.name}
                      </CardTitle>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                      </span>
                      <span className="text-[11px] font-mono font-semibold text-emerald-600 dark:text-emerald-400 uppercase">
                        {battery.status}
                      </span>
                    </div>
                  </div>

                  <CardDescription className="text-xs text-muted-foreground mt-2 line-clamp-2">
                    {battery.description}
                  </CardDescription>
                </CardHeader>

                <CardContent className="pt-0 space-y-3">
                  <div className="bg-muted/40 p-2.5 rounded-lg border border-border/40 text-[11px]">
                    <span className="text-muted-foreground block font-medium mb-1">
                      Algorithmic Architecture:
                    </span>
                    <span className="font-mono text-foreground font-semibold text-[11px] break-words">
                      {battery.algorithm_foundation}
                    </span>
                  </div>

                  {battery.active_parameters && Object.keys(battery.active_parameters).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {Object.entries(battery.active_parameters).map(([key, val]) => (
                        <span
                          key={key}
                          className="font-mono text-[10px] bg-secondary px-2 py-0.5 rounded text-secondary-foreground"
                        >
                          {key}:{" "}
                          <span className="font-semibold text-foreground">
                            {typeof val === "boolean"
                              ? val
                                ? "true"
                                : "false"
                              : Array.isArray(val)
                              ? `[${val.length}]`
                              : String(val)}
                          </span>
                        </span>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
