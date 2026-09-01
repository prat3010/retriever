"use client";

import { useState, useMemo } from "react";
import {
  useTenantProjections,
  useProjectEmbeddingsMutation,
  ProjectedPoint,
  ProjectionCentroid,
  EmbeddingProjectionRequest,
} from "@/hooks/use-projections";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Compass, Sparkles, Search, Layers, RefreshCw, Loader2, Info } from "lucide-react";

interface TenantVectorSpaceTabProps {
  tenantId: string;
}

const CLUSTER_COLORS = [
  "#3B82F6", // blue
  "#10B981", // emerald
  "#8B5CF6", // violet
  "#F59E0B", // amber
  "#EC4899", // pink
  "#06B6D4", // cyan
  "#84CC16", // lime
  "#F97316", // orange
];

export function TenantVectorSpaceTab({ tenantId }: TenantVectorSpaceTabProps) {
  const [method, setMethod] = useState<"pca" | "tsne" | "umap">("pca");
  const [dimensions, setDimensions] = useState<number>(2);
  const [perplexity, setPerplexity] = useState<number>(15);
  const [queryInput, setQueryInput] = useState<string>("");
  const [selectedPoint, setSelectedPoint] = useState<ProjectedPoint | null>(null);

  const requestParams: EmbeddingProjectionRequest = useMemo(
    () => ({
      method,
      dimensions,
      perplexity,
      normalize: true,
      query_text: queryInput.trim() || undefined,
    }),
    [method, dimensions, perplexity, queryInput]
  );

  const { data: projection, isLoading, isFetching, refetch } = useTenantProjections(tenantId, requestParams);
  const projectMutation = useProjectEmbeddingsMutation(tenantId);

  const handleTestQuery = (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryInput.trim()) return;
    refetch();
    toast.info(`Projecting active search vector for: "${queryInput}"`);
  };

  const points = projection?.points || [];
  const centroids = projection?.centroids || [];
  const queryPoint = projection?.query_point || null;
  const silhouette = projection?.silhouette_score;
  const varianceExplained = projection?.variance_explained;

  // ViewBox coordinate mapping
  // Coordinates are normalized to [-90, 90], map to [40, 560] on a 600x600 SVG canvas
  const mapCoord = (val: number) => 300 + val * 2.8;

  return (
    <div className="space-y-6">
      {/* Top Metrics Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Vector Chunks Mapped</CardDescription>
            <CardTitle className="text-2xl font-bold flex items-center gap-2">
              <Layers className="h-5 w-5 text-blue-500" />
              {projection?.total_points ?? 0}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Manifold Engine</CardDescription>
            <CardTitle className="text-xl font-semibold uppercase text-purple-600 dark:text-purple-400">
              {projection?.method_used || method} {dimensions}D
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Silhouette Cluster Index</CardDescription>
            <CardTitle className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {silhouette !== null && silhouette !== undefined ? `${(silhouette * 100).toFixed(1)}%` : "--"}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Topic Clusters</CardDescription>
            <CardTitle className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {centroids.length} Identified
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Control Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div className="space-y-2">
              <Label htmlFor="proj-method">Manifold Algorithm</Label>
              <Select value={method} onValueChange={(v: "pca" | "tsne" | "umap") => setMethod(v)}>
                <SelectTrigger id="proj-method">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pca">PCA (Deterministic SVD)</SelectItem>
                  <SelectItem value="tsne">t-SNE (Nonlinear Manifold)</SelectItem>
                  <SelectItem value="umap">UMAP (Topological Cluster)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="proj-dims">Coordinates Dimension</Label>
              <Select value={String(dimensions)} onValueChange={(v) => setDimensions(Number(v))}>
                <SelectTrigger id="proj-dims">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2">2D Plane Projection</SelectItem>
                  <SelectItem value="3">3D Isometric Manifold</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <form onSubmit={handleTestQuery} className="space-y-2 md:col-span-2 flex gap-2 items-end">
              <div className="flex-1 space-y-2">
                <Label htmlFor="proj-query">Query Vector Simulation</Label>
                <Input
                  id="proj-query"
                  placeholder="Type query to project active vector (e.g. SOW deliverables)..."
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                />
              </div>
              <Button type="submit" variant="secondary" disabled={!queryInput.trim() || isFetching}>
                <Search className="h-4 w-4 mr-1" />
                Plot Vector
              </Button>
            </form>
          </div>
        </CardContent>
      </Card>

      {/* Main Manifold Canvas & Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Canvas Area */}
        <Card className="lg:col-span-2 overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Compass className="h-4 w-4 text-primary" />
                <span>Embedding Coordinate Space & Cluster Topologies</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Interactive manifold projection of all ingested knowledge chunks. Click any point to inspect chunk contents.
              </CardDescription>
            </div>
            {isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </CardHeader>
          <CardContent className="flex justify-center p-4">
            {isLoading ? (
              <Skeleton className="h-[460px] w-full" />
            ) : points.length === 0 ? (
              <div className="text-center py-24 text-muted-foreground space-y-2">
                <p className="text-sm font-medium">No embedded documents found for this tenant.</p>
                <p className="text-xs">Upload and process PDF or markdown documents in the Documents tab to project vector space.</p>
              </div>
            ) : (
              <div className="relative w-full max-w-[560px] aspect-square border rounded-xl bg-card/50 overflow-hidden shadow-inner">
                {/* SVG Coordinate Scatter Plane */}
                <svg viewBox="0 0 600 600" className="w-full h-full">
                  {/* Cartesian Axis Lines */}
                  <line x1="300" y1="20" x2="300" y2="580" stroke="currentColor" strokeOpacity="0.1" strokeDasharray="4 4" />
                  <line x1="20" y1="300" x2="580" y2="300" stroke="currentColor" strokeOpacity="0.1" strokeDasharray="4 4" />

                  {/* Centroids Halo */}
                  {centroids.map((c, idx) => {
                    const cx = mapCoord(c.coordinates[0] || 0);
                    const cy = mapCoord(c.coordinates[1] || 0);
                    const color = CLUSTER_COLORS[idx % CLUSTER_COLORS.length];
                    return (
                      <g key={c.cluster_id}>
                        <circle cx={cx} cy={cy} r="28" fill={color} fillOpacity="0.12" />
                        <circle cx={cx} cy={cy} r="4" fill={color} stroke="#fff" strokeWidth="1.5" />
                        <text x={cx + 6} y={cy - 6} fill="currentColor" fontSize="10" fontWeight="600" opacity="0.8">
                          {c.label}
                        </text>
                      </g>
                    );
                  })}

                  {/* Document Chunk Nodes */}
                  {points.map((pt) => {
                    const cx = mapCoord(pt.coordinates[0] || 0);
                    const cy = mapCoord(pt.coordinates[1] || 0);
                    const isSelected = selectedPoint?.chunk_id === pt.chunk_id;
                    const color = CLUSTER_COLORS[Math.abs(pt.cluster_id) % CLUSTER_COLORS.length];

                    return (
                      <circle
                        key={pt.chunk_id}
                        cx={cx}
                        cy={cy}
                        r={isSelected ? "7" : "4.5"}
                        fill={color}
                        stroke={isSelected ? "#ffffff" : "rgba(0,0,0,0.3)"}
                        strokeWidth={isSelected ? "2.5" : "1"}
                        className="cursor-pointer transition-transform hover:scale-125"
                        onClick={() => setSelectedPoint(pt)}
                      >
                        <title>{`${pt.document_title}: ${pt.text_preview.slice(0, 80)}...`}</title>
                      </circle>
                    );
                  })}

                  {/* Query Vector Marker */}
                  {queryPoint && (
                    <g>
                      <circle
                        cx={mapCoord(queryPoint.coordinates[0] || 0)}
                        cy={mapCoord(queryPoint.coordinates[1] || 0)}
                        r="10"
                        fill="#FFB300"
                        fillOpacity="0.25"
                        className="animate-ping"
                      />
                      <polygon
                        points={`${mapCoord(queryPoint.coordinates[0] || 0)},${mapCoord(queryPoint.coordinates[1] || 0) - 8} ${mapCoord(queryPoint.coordinates[0] || 0) + 7},${mapCoord(queryPoint.coordinates[1] || 0) + 6} ${mapCoord(queryPoint.coordinates[0] || 0) - 7},${mapCoord(queryPoint.coordinates[1] || 0) + 6}`}
                        fill="#FFB300"
                        stroke="#000"
                        strokeWidth="1"
                      />
                      <text
                        x={mapCoord(queryPoint.coordinates[0] || 0) + 12}
                        y={mapCoord(queryPoint.coordinates[1] || 0) + 4}
                        fill="#FFB300"
                        fontSize="11"
                        fontWeight="bold"
                      >
                        🎯 Query Vector
                      </text>
                    </g>
                  )}
                </svg>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Selected Chunk & Topology Inspector */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Inspector & Chunk Details</CardTitle>
              <CardDescription className="text-xs">Click any manifold point to inspect its text contents and cluster affiliation.</CardDescription>
            </CardHeader>
            <CardContent>
              {selectedPoint ? (
                <div className="space-y-3 font-mono text-xs">
                  <div>
                    <span className="text-muted-foreground uppercase text-[10px]">Document Source</span>
                    <p className="font-sans font-semibold text-sm truncate">{selectedPoint.document_title}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground uppercase text-[10px]">Cluster Affinity</span>
                    <div>
                      <Badge variant="outline" className="mt-1 font-sans">
                        {selectedPoint.cluster_label}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <span className="text-muted-foreground uppercase text-[10px]">Cartesian Coordinates</span>
                    <p className="text-primary font-bold">
                      [{selectedPoint.coordinates.map((c) => c.toFixed(2)).join(", ")}]
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground uppercase text-[10px]">Chunk Preview</span>
                    <p className="p-2.5 bg-muted rounded-lg font-sans text-xs mt-1 leading-relaxed max-h-48 overflow-y-auto">
                      {selectedPoint.text_preview}
                    </p>
                  </div>
                  <Button size="sm" variant="ghost" className="w-full text-xs" onClick={() => setSelectedPoint(null)}>
                    Clear Selection
                  </Button>
                </div>
              ) : (
                <div className="py-12 text-center text-muted-foreground text-xs space-y-1">
                  <Info className="h-6 w-6 mx-auto opacity-50 mb-2" />
                  <p>No chunk selected</p>
                  <p>Click any node on the vector space scatter plot.</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Variance Explained (for PCA) */}
          {varianceExplained && varianceExplained.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold uppercase text-muted-foreground">Variance Retained (PCA)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                {varianceExplained.map((v, i) => (
                  <div key={i} className="flex justify-between items-center">
                    <span>Component PC_{i + 1}</span>
                    <Badge variant="secondary" className="font-mono text-xs">
                      {(v * 100).toFixed(1)}%
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
