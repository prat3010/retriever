"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Globe,
  Server,
  Activity,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Zap,
  Radio,
  ArrowRightLeft,
  CheckCircle2,
  Database,
  Layers,
} from "lucide-react";
import { toast } from "sonner";

interface CloudRegionNode {
  node_id: string;
  cloud_provider: string;
  region: string;
  endpoint_url: string;
  role: "primary_leader" | "standby_replica" | "edge_follower" | "degraded" | "offline";
  is_voting_member: boolean;
  priority_weight: number;
  latency_ms: number;
  consecutive_failures: number;
  last_heartbeat_at: string;
  metadata?: Record<string, any>;
}

interface ClusterTopology {
  cluster_id: string;
  active_leader_region: string;
  active_leader_node_id: string;
  generation_term: number;
  total_nodes: number;
  healthy_nodes: number;
  quorum_state: string;
  nodes: CloudRegionNode[];
  last_failover_at?: string;
  last_failover_reason?: string;
  environment_mode: string;
}

interface MultiCloudOverview {
  topology: ClusterTopology;
  active_battery?: {
    id: string;
    name: string;
    status: string;
    algorithm_foundation: string;
    latency_profile: string;
    milestone: string;
    active_parameters?: Record<string, any>;
  };
  probes_summary: {
    total_nodes: number;
    healthy_count: number;
    voting_quorum_ratio: string;
    quorum_state: string;
    environment_mode: string;
  };
}

export default function MultiCloudPage() {
  const queryClient = useQueryClient();
  const [targetFailoverRegion, setTargetFailoverRegion] = useState<string>("aws-iad");
  const [failoverReason, setFailoverReason] = useState<string>("Operator scheduled test failover");

  const { data, isLoading, refetch } = useQuery<MultiCloudOverview>({
    queryKey: ["multicloud-clusters"],
    queryFn: () => api.get("/v1/admin/multicloud/clusters"),
    refetchInterval: 5000,
  });

  const { data: replStats } = useQuery({
    queryKey: ["multicloud-replication-status"],
    queryFn: () => api.get("/v1/admin/multicloud/replication-status"),
    refetchInterval: 5000,
  });

  const probeMutation = useMutation({
    mutationFn: () => api.post("/v1/admin/multicloud/probe", {}),
    onSuccess: (probes: any[]) => {
      toast.success(`Probed ${probes.length} cloud regions successfully.`);
      queryClient.invalidateQueries({ queryKey: ["multicloud-clusters"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Health probe failed");
    },
  });

  const failoverMutation = useMutation({
    mutationFn: (payload: { target_region: string; reason: string; force: boolean }) =>
      api.post("/v1/admin/multicloud/failover", payload),
    onSuccess: (res: any) => {
      if (res.success) {
        toast.success(res.message);
      } else {
        toast.error(res.message);
      }
      queryClient.invalidateQueries({ queryKey: ["multicloud-clusters"] });
      queryClient.invalidateQueries({ queryKey: ["multicloud-replication-status"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failover failed");
    },
  });

  const topology = data?.topology;
  const battery = data?.active_battery;

  return (
    <div className="flex flex-col h-full bg-background text-foreground">
      <Topbar title="Multi-Cloud & Turso LibSQL (M99)" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Header Ribbon */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight">Multi-Cloud Resiliency & Turso LibSQL</h1>
              <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 text-xs font-mono">
                Milestone 99 (v0.84.0)
              </Badge>
              <Badge variant="secondary" className="text-xs font-mono">
                Platform Battery #19
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Active-active quorum consensus leader election, automated circuit-breaker failover, and sub-1ms embedded Turso LibSQL replication.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => probeMutation.mutate()}
              disabled={probeMutation.isPending}
              className="gap-2"
            >
              <Activity className={`h-4 w-4 ${probeMutation.isPending ? "animate-spin text-primary" : ""}`} />
              Probe Regions
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Quorum & Leader Status Bar */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="border-border">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs">Active Primary Leader</CardDescription>
              <CardTitle className="text-xl flex items-center gap-2 font-mono text-emerald-500">
                <Server className="h-5 w-5" />
                {topology?.active_leader_region?.toUpperCase() || "OCI-BOM"}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Node: <span className="font-mono text-foreground">{topology?.active_leader_node_id || "node-oci-bom-01"}</span>
            </CardContent>
          </Card>

          <Card className="border-border">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs">Quorum Consensus</CardDescription>
              <CardTitle className="text-xl flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-emerald-500" />
                {topology?.quorum_state === "consensus_reached" ? "Quorum Reached" : "Quorum Lost"}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Voting Ratio: <span className="font-mono text-foreground">{data?.probes_summary?.voting_quorum_ratio || "3/3"}</span>
            </CardContent>
          </Card>

          <Card className="border-border">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs">Generation Term</CardDescription>
              <CardTitle className="text-xl font-mono">
                Term #{topology?.generation_term || 1}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Monotonic Raft sequence counter
            </CardContent>
          </Card>

          <Card className="border-border">
            <CardHeader className="pb-2">
              <CardDescription className="text-xs">LibSQL Avg Lag</CardDescription>
              <CardTitle className="text-xl font-mono text-sky-500 flex items-center gap-2">
                <Zap className="h-5 w-5" />
                {replStats?.average_lag_ms ? `${replStats.average_lag_ms} ms` : "< 1 ms"}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Local reads: <span className="font-mono text-foreground">{replStats?.reads_served_locally || 4290}</span>
            </CardContent>
          </Card>
        </div>

        {/* Distributed Region Nodes Grid */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Globe className="h-5 w-5 text-primary" />
              Multi-Cloud Region Mesh
            </h2>
            <span className="text-xs text-muted-foreground font-mono">
              Environment: {topology?.environment_mode || "hybrid_testnet"}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {topology?.nodes?.map((node) => {
              const isLeader = node.role === "primary_leader";
              return (
                <Card
                  key={node.node_id}
                  className={`border transition-all ${
                    isLeader ? "border-emerald-500/50 bg-emerald-500/5" : "border-border hover:border-primary/40"
                  }`}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <Badge
                        variant={isLeader ? "default" : "secondary"}
                        className={isLeader ? "bg-emerald-600 text-white" : ""}
                      >
                        {isLeader ? "PRIMARY LEADER" : node.role.replace("_", " ").toUpperCase()}
                      </Badge>
                      <span className="text-xs font-mono text-muted-foreground">{node.cloud_provider.toUpperCase()}</span>
                    </div>
                    <CardTitle className="text-base font-mono mt-2">{node.region}</CardTitle>
                    <CardDescription className="text-xs truncate">{node.endpoint_url}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2 text-xs">
                    <div className="flex justify-between border-t pt-2">
                      <span className="text-muted-foreground">EWMA Latency:</span>
                      <span className="font-mono font-medium">{node.latency_ms} ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Voting Member:</span>
                      <span className="font-mono">{node.is_voting_member ? "Yes (>50% quorum)" : "No (Edge Follower)"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Failures:</span>
                      <span className={`font-mono ${node.consecutive_failures > 0 ? "text-amber-500" : "text-emerald-500"}`}>
                        {node.consecutive_failures} / 3
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Priority Weight:</span>
                      <span className="font-mono">{node.priority_weight}</span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Failover Control & LibSQL Stream */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Manual Quorum Failover Controller */}
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <ArrowRightLeft className="h-5 w-5 text-primary" />
                Quorum Leader Failover Controller
              </CardTitle>
              <CardDescription className="text-xs">
                Gracefully drain traffic and execute a leader transition to a standby region with majority vote validation.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-medium">Target Failover Region</label>
                <select
                  value={targetFailoverRegion}
                  onChange={(e) => setTargetFailoverRegion(e.target_region || e.target.value)}
                  className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm font-mono"
                >
                  <option value="aws-iad">aws-iad (AWS US-East Northern Virginia)</option>
                  <option value="fly-fra">fly-fra (Fly.io Frankfurt EU)</option>
                  <option value="oci-bom">oci-bom (Oracle Mumbai VPS Primary)</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium">Failover Justification / Reason</label>
                <input
                  type="text"
                  value={failoverReason}
                  onChange={(e) => setFailoverReason(e.target.value)}
                  placeholder="e.g. Scheduled datacenter maintenance"
                  className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm font-mono"
                />
              </div>

              <Button
                className="w-full gap-2"
                onClick={() =>
                  failoverMutation.mutate({
                    target_region: targetFailoverRegion,
                    reason: failoverReason,
                    force: false,
                  })
                }
                disabled={failoverMutation.isPending}
              >
                <ArrowRightLeft className={`h-4 w-4 ${failoverMutation.isPending ? "animate-spin" : ""}`} />
                Execute Quorum Failover
              </Button>
            </CardContent>
          </Card>

          {/* Turso / LibSQL Replication Card */}
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-5 w-5 text-sky-500" />
                Turso / LibSQL Embedded Replication Stream
              </CardTitle>
              <CardDescription className="text-xs">
                Local embedded LibSQL read replicas with background WAL frame streaming and upstream transaction proxying.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="p-3 bg-secondary/50 rounded-lg space-y-2 font-mono">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Cluster URL:</span>
                  <span className="text-foreground truncate max-w-[260px]">
                    {replStats?.turso_cluster_url || "libsql://retriever-cluster.turso.io"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Replication Engine:</span>
                  <Badge variant="outline" className="text-[10px]">
                    {replStats?.engine || "libsql_embedded_wal"}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Global WAL Frame:</span>
                  <span className="text-emerald-500 font-bold">{replStats?.global_wal_frame || 1280}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span className="text-emerald-500 font-bold uppercase">{replStats?.sync_status || "synced"}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="p-3 border rounded-lg">
                  <div className="text-muted-foreground text-[10px]">Reads Served Locally</div>
                  <div className="text-xl font-bold font-mono text-sky-500 mt-1">
                    {replStats?.reads_served_locally || 4290}
                  </div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">&lt; 1 ms latency</div>
                </div>
                <div className="p-3 border rounded-lg">
                  <div className="text-muted-foreground text-[10px]">Writes Forwarded to Leader</div>
                  <div className="text-xl font-bold font-mono text-emerald-500 mt-1">
                    {replStats?.writes_forwarded || 14}
                  </div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">Proxy to primary</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Platform Battery #19 Card */}
        {battery && (
          <Card className="border-border bg-card/60">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-amber-500" />
                  <CardTitle className="text-base">{battery.name}</CardTitle>
                </div>
                <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-500 border-emerald-500/20 font-mono">
                  {battery.status.toUpperCase()}
                </Badge>
              </div>
              <CardDescription className="text-xs font-mono">
                {battery.algorithm_foundation}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-3 bg-secondary/30 rounded-lg">
                  <span className="text-muted-foreground block text-[10px]">Latency Profile</span>
                  <span className="font-mono text-foreground font-semibold">{battery.latency_profile}</span>
                </div>
                <div className="p-3 bg-secondary/30 rounded-lg">
                  <span className="text-muted-foreground block text-[10px]">Milestone Verification</span>
                  <span className="font-mono text-foreground font-semibold">{battery.milestone}</span>
                </div>
                <div className="p-3 bg-secondary/30 rounded-lg">
                  <span className="text-muted-foreground block text-[10px]">Quorum Gate</span>
                  <span className="font-mono text-foreground font-semibold">&gt; 50% Majority Threshold</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
