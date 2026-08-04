"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useGraphStatus,
  useSwitchGraphEngine,
  useGraphQuery,
  useDeleteGraphTriple,
  type GraphQueryResult,
  type GraphTriple,
} from "@/hooks/use-graph";
import { toast } from "sonner";
import {
  Cpu,
  Database,
  GitFork,
  Layers,
  Network,
  RefreshCw,
  Search,
  ShieldAlert,
  Trash2,
  Zap,
  Loader2,
} from "lucide-react";

export function TenantGraphTab({ tenantId }: { tenantId: string }) {
  const { data: status, isLoading, isError, error, refetch } = useGraphStatus(tenantId);
  const switchEngine = useSwitchGraphEngine(tenantId);
  const graphQuery = useGraphQuery(tenantId);
  const deleteTriple = useDeleteGraphTriple(tenantId);

  const [searchEntity, setSearchEntity] = useState("");
  const [maxHops, setMaxHops] = useState(2);
  const [queryResult, setQueryResult] = useState<GraphQueryResult | null>(null);
  const [lastQuery, setLastQuery] = useState<{ entity: string; hops: number } | null>(null);

  const [deletingTriple, setDeletingTriple] = useState<GraphTriple | null>(null);

  const capabilities = status?.capabilities ?? null;
  const summary = status?.summary ?? null;
  const isLeanMode = capabilities?.machine_profile === "oracle_vm_lean";
  const activeEngine = capabilities?.active_engine || "postgres";
  const neo4jOnline = capabilities?.neo4j_status === "online";

  const handleEngineSwitch = async (targetEngine: "postgres" | "neo4j") => {
    try {
      await switchEngine.mutateAsync(targetEngine);
      toast.success(`Switched graph engine to ${targetEngine}.`);
    } catch (err: any) {
      toast.error(err.message || "Engine switch failed.");
    }
  };

  const handleEntitySearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchEntity.trim()) return;
    const entity = searchEntity.trim();
    try {
      const result = await graphQuery.mutateAsync({ entity, maxHops });
      setQueryResult(result);
      setLastQuery({ entity, hops: maxHops });
    } catch (err: any) {
      toast.error(err.message || "Failed to query knowledge graph.");
    }
  };

  const handleDeleteTriple = async () => {
    const triple = deletingTriple;
    if (!triple?.triple_id) return;
    setDeletingTriple(null);
    try {
      await deleteTriple.mutateAsync(triple.triple_id);
      toast.success(`Deleted triple: ${triple.subject} → ${triple.object}`);
      if (lastQuery) {
        const result = await graphQuery.mutateAsync({ entity: lastQuery.entity, maxHops: lastQuery.hops });
        setQueryResult(result);
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to delete triple.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">GraphRAG Knowledge Graph</h3>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 mr-1.5 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {isError && (
        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-4 py-3">
          <ShieldAlert className="h-4 w-4" />
          {error instanceof Error ? error.message : "Failed to load graph status."}
        </div>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Cpu className="h-4 w-4 text-primary" />
            Host Hardware Profile
          </CardTitle>
          {isLoading ? (
            <Skeleton className="h-5 w-28" />
          ) : (
            <Badge variant={neo4jOnline ? "default" : isLeanMode ? "secondary" : "outline"}>
              Neo4j: {neo4jOnline ? "Online" : isLeanMode ? "Unsupported (RAM Safetynet)" : "Offline"}
            </Badge>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-64" />
              <Skeleton className="h-3 w-full" />
            </div>
          ) : (
            <>
              <div>
                <p className="font-medium">
                  {isLeanMode ? "Oracle Cloud VM (LEAN Mode)" : "MacBook Air M4 (Standard Mode)"}
                </p>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {capabilities?.message || "Auto-detecting hardware capabilities..."}
                </p>
              </div>

              <div className="pt-4 border-t flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-2 text-sm">
                  <Layers className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">Active Storage Engine</span>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant={activeEngine === "postgres" ? "default" : "outline"}
                    size="sm"
                    onClick={() => handleEngineSwitch("postgres")}
                    disabled={switchEngine.isPending}
                  >
                    <Database className="h-4 w-4 mr-1.5" />
                    PostgreSQL
                  </Button>
                  <Button
                    variant={activeEngine === "neo4j" ? "default" : "outline"}
                    size="sm"
                    onClick={() => handleEngineSwitch("neo4j")}
                    disabled={switchEngine.isPending || isLeanMode}
                    title={isLeanMode ? "Neo4j is disabled on LEAN Oracle VM to prevent RAM crashes" : "Switch to Neo4j Cypher Engine"}
                  >
                    {switchEngine.isPending && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}
                    Neo4j {isLeanMode && "(locked)"}
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground flex items-center gap-2">
              <GitFork className="h-4 w-4 text-primary" />
              Total Graph Triples
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-7 w-16" /> : <p className="text-2xl font-semibold">{summary?.total_triples ?? 0}</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground flex items-center gap-2">
              <Database className="h-4 w-4 text-primary" />
              Unique Entities
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-7 w-16" /> : <p className="text-2xl font-semibold">{summary?.unique_entities ?? 0}</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary" />
              Active Engine
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-7 w-24" />
            ) : (
              <p className="text-xl font-semibold uppercase">{summary?.storage_engine || activeEngine}</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Search className="h-4 w-4 text-primary" />
            Multi-Hop Entity Inspector
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleEntitySearch} className="flex gap-2 flex-wrap">
            <Input
              type="text"
              placeholder="Search entity (e.g. Alice, Payment Gateway)..."
              value={searchEntity}
              onChange={(e) => setSearchEntity(e.target.value)}
              className="flex-1 min-w-[220px]"
            />
            <Select
              value={String(maxHops)}
              onValueChange={(v) => setMaxHops(Number(v))}
            >
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Max hops" />
              </SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4, 5].map((hops) => (
                  <SelectItem key={hops} value={String(hops)}>
                    {hops}-Hop Depth
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button type="submit" disabled={graphQuery.isPending || !searchEntity.trim()}>
              {graphQuery.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                  Searching...
                </>
              ) : (
                "Traverse Graph"
              )}
            </Button>
          </form>

          {queryResult && (
            <div>
              <p className="text-sm text-muted-foreground">
                Root Entity: <span className="font-medium text-foreground">{queryResult.root_entity}</span>
                {" "}| Connected Entities: {queryResult.connected_entities.length}
              </p>

              {queryResult.triples.length === 0 ? (
                <div className="text-sm text-muted-foreground italic px-4 py-3 bg-muted/40 rounded-md mt-3">
                  No triples found for entity &ldquo;{queryResult.root_entity}&rdquo;. Try uploading a document or searching another entity.
                </div>
              ) : (
                <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3 mt-3">
                  {queryResult.triples.map((triple, idx) => (
                    <div
                      key={triple.triple_id || idx}
                      className="border rounded-lg p-3 bg-card flex items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-semibold text-primary truncate">{triple.subject}</span>
                        <Badge variant="secondary" className="shrink-0 text-[10px]">{triple.predicate}</Badge>
                        <span className="font-semibold text-green-600 dark:text-green-400 truncate">{triple.object}</span>
                      </div>
                      {triple.triple_id && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                          onClick={() => setDeletingTriple(triple)}
                          title="Delete triple"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={deletingTriple !== null} onOpenChange={(open) => !open && setDeletingTriple(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete triple?</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{deletingTriple?.subject} &rarr; {deletingTriple?.object}&rdquo;? This permanently removes the relationship from the knowledge graph.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingTriple(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteTriple} disabled={deleteTriple.isPending}>
              {deleteTriple.isPending && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
