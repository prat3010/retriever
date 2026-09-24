"use client";

import { useState, useRef, useCallback } from "react";
import {
  DAGNode,
  DAGNodeType,
  WorkflowDAGGraph,
  DAGExecutionResult,
  DAGCompilerResult,
  useWorkflowTemplates,
  useCompileDAG,
  useExecuteDAG,
} from "@/hooks/use-workflow";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Play,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  CheckCircle2,
  Layers,
  Sparkles,
  Database,
  ShieldCheck,
  Cpu,
  Sliders,
  DollarSign,
  Clock,
  Trash2,
  Plus,
} from "lucide-react";

interface VisualDagCanvasProps {
  tenantId: string;
}

const DEFAULT_EMPTY_GRAPH: WorkflowDAGGraph = {
  id: "custom_dag",
  name: "Custom Cognitive DAG",
  nodes: [],
  edges: [],
};

const NODE_COLORS: Record<DAGNodeType, { bg: string; border: string; text: string }> = {
  input: { bg: "bg-blue-500/10", border: "border-blue-500/40", text: "text-blue-500" },
  retrieval: { bg: "bg-emerald-500/10", border: "border-emerald-500/40", text: "text-emerald-500" },
  guardrail: { bg: "bg-amber-500/10", border: "border-amber-500/40", text: "text-amber-500" },
  transform: { bg: "bg-purple-500/10", border: "border-purple-500/40", text: "text-purple-500" },
  prompt: { bg: "bg-cyan-500/10", border: "border-cyan-500/40", text: "text-cyan-500" },
  llm: { bg: "bg-violet-500/10", border: "border-violet-500/40", text: "text-violet-500" },
  evaluator: { bg: "bg-teal-500/10", border: "border-teal-500/40", text: "text-teal-500" },
  router: { bg: "bg-orange-500/10", border: "border-orange-500/40", text: "text-orange-500" },
  output: { bg: "bg-rose-500/10", border: "border-rose-500/40", text: "text-rose-500" },
};

function getNodeIcon(type: DAGNodeType) {
  switch (type) {
    case "input":
      return <Layers className="w-4 h-4 text-blue-500" />;
    case "retrieval":
      return <Database className="w-4 h-4 text-emerald-500" />;
    case "guardrail":
      return <ShieldCheck className="w-4 h-4 text-amber-500" />;
    case "transform":
      return <Sliders className="w-4 h-4 text-purple-500" />;
    case "prompt":
      return <Sparkles className="w-4 h-4 text-cyan-500" />;
    case "llm":
      return <Cpu className="w-4 h-4 text-violet-500" />;
    case "evaluator":
      return <CheckCircle2 className="w-4 h-4 text-teal-500" />;
    case "router":
      return <Sliders className="w-4 h-4 text-orange-500" />;
    case "output":
      return <CheckCircle2 className="w-4 h-4 text-rose-500" />;
  }
}

export function VisualDagCanvas({ tenantId }: VisualDagCanvasProps) {
  const { data: templates } = useWorkflowTemplates(tenantId);
  const compileMutation = useCompileDAG(tenantId);
  const executeMutation = useExecuteDAG(tenantId);

  // Active custom graph state or template selection
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [userGraph, setUserGraph] = useState<WorkflowDAGGraph | null>(null);
  const idCounterRef = useRef<number>(100);

  // Resolve active graph without synchronous setState in effect
  const activeTemplate =
    templates?.find((t) => t.id === selectedTemplateId) ?? templates?.[0] ?? DEFAULT_EMPTY_GRAPH;
  const graph: WorkflowDAGGraph = userGraph ?? activeTemplate;

  const updateGraph = useCallback(
    (updater: (prev: WorkflowDAGGraph) => WorkflowDAGGraph) => {
      setUserGraph((prev) => updater(prev ?? activeTemplate));
    },
    [activeTemplate]
  );

  // Canvas Viewport Pan & Zoom
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 40, y: 40 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const startPanRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Selected & Dragging Node
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const dragStartPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const nodeStartPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Interactive Edge Creation
  const [connectingSourceId, setConnectingSourceId] = useState<string | null>(null);

  // Execution & Stepper Results
  const [executionResult, setExecutionResult] = useState<DAGExecutionResult | null>(null);
  const [compileResult, setCompileResult] = useState<DAGCompilerResult | null>(null);
  const [queryInput, setQueryInput] = useState<string>("Analyze regulatory compliance and indemnity.");

  // Handle Pan Events
  const handleMouseDownCanvas = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget || (e.target as HTMLElement).tagName === "svg") {
      setIsPanning(true);
      startPanRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
      setSelectedNodeId(null);
    }
  };

  const handleMouseMoveCanvas = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (isPanning) {
        setPan({
          x: e.clientX - startPanRef.current.x,
          y: e.clientY - startPanRef.current.y,
        });
      } else if (draggingNodeId) {
        const dx = (e.clientX - dragStartPosRef.current.x) / zoom;
        const dy = (e.clientY - dragStartPosRef.current.y) / zoom;
        updateGraph((prev) => ({
          ...prev,
          nodes: prev.nodes.map((n) =>
            n.id === draggingNodeId
              ? {
                  ...n,
                  position: {
                    x: Math.round(nodeStartPosRef.current.x + dx),
                    y: Math.round(nodeStartPosRef.current.y + dy),
                  },
                }
              : n
          ),
        }));
      }
    },
    [isPanning, draggingNodeId, zoom, updateGraph]
  );

  const handleMouseUpCanvas = () => {
    setIsPanning(false);
    setDraggingNodeId(null);
  };

  // Node Drag Handlers
  const handleNodeMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    const node = graph.nodes.find((n) => n.id === nodeId);
    if (!node) return;
    setSelectedNodeId(nodeId);
    setDraggingNodeId(nodeId);
    dragStartPosRef.current = { x: e.clientX, y: e.clientY };
    nodeStartPosRef.current = { x: node.position.x, y: node.position.y };
  };

  // Port Connection Click Handlers
  const handlePortClick = (e: React.MouseEvent, nodeId: string, isSource: boolean) => {
    e.stopPropagation();
    if (isSource) {
      setConnectingSourceId(nodeId);
    } else if (connectingSourceId && connectingSourceId !== nodeId) {
      idCounterRef.current += 1;
      const edgeId = `e_${connectingSourceId}_${nodeId}_${idCounterRef.current}`;
      updateGraph((prev) => ({
        ...prev,
        edges: [...prev.edges, { id: edgeId, source: connectingSourceId, target: nodeId }],
      }));
      setConnectingSourceId(null);
    }
  };

  // Node Deletion
  const handleDeleteNode = (nodeId: string) => {
    updateGraph((prev) => ({
      ...prev,
      nodes: prev.nodes.filter((n) => n.id !== nodeId),
      edges: prev.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
    }));
    if (selectedNodeId === nodeId) setSelectedNodeId(null);
  };

  // Add Node from Palette
  const handleAddNode = (type: DAGNodeType) => {
    idCounterRef.current += 1;
    const id = `${type}_${idCounterRef.current}`;
    const newNode: DAGNode = {
      id,
      type,
      title: `${type.toUpperCase()} Node`,
      description: `New ${type} operation`,
      position: { x: 150 + graph.nodes.length * 40, y: 150 + (graph.nodes.length % 3) * 60 },
      config: type === "retrieval" ? { k: 5 } : type === "llm" ? { model: "llama3.2" } : {},
      input_keys: type === "input" ? [] : ["query"],
      output_keys: type === "output" ? [] : ["response"],
    };
    updateGraph((prev) => ({ ...prev, nodes: [...prev.nodes, newNode] }));
    setSelectedNodeId(id);
  };

  // Compile DAG
  const handleCompile = async () => {
    try {
      const res = await compileMutation.mutateAsync(graph);
      setCompileResult(res);
    } catch {
      // handled by mutation
    }
  };

  // Execute DAG Pipeline
  const handleExecute = async () => {
    try {
      const res = await executeMutation.mutateAsync({
        graph,
        input_payload: { query: queryInput },
      });
      setExecutionResult(res);
    } catch {
      // handled by mutation
    }
  };

  // Node Dimensions for Bézier Curve Calculation
  const NODE_WIDTH = 220;
  const NODE_HEIGHT = 100;

  return (
    <div className="flex flex-col h-[750px] border rounded-xl overflow-hidden bg-background">
      {/* Top Action Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 border-b bg-card">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-xs">
            Visual DAG Studio
          </Badge>
          <span className="font-semibold text-sm">{graph.name}</span>

          {/* Template Selector */}
          {templates && templates.length > 0 && (
            <select
              className="text-xs bg-muted border rounded px-2 py-1 ml-2"
              onChange={(e) => {
                setSelectedTemplateId(e.target.value);
                setUserGraph(null);
                setExecutionResult(null);
                setCompileResult(null);
              }}
              value={graph.id}
              aria-label="Select enterprise workflow template"
            >
              {templates.map((tpl) => (
                <option key={tpl.id} value={tpl.id}>
                  Template: {tpl.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Input Query for Execution */}
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <Input
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            placeholder="Test query payload..."
            className="text-xs h-8"
          />
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleCompile}
            disabled={compileMutation.isPending}
            className="text-xs h-8"
          >
            {compileMutation.isPending ? "Validating..." : "Validate & Cycle Check"}
          </Button>

          <Button
            size="sm"
            onClick={handleExecute}
            disabled={executeMutation.isPending}
            className="text-xs h-8 bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            <Play className="w-3.5 h-3.5 mr-1" />
            {executeMutation.isPending ? "Stepping DAG..." : "Execute Pipeline"}
          </Button>

          {/* Canvas Pan/Zoom Controls */}
          <div className="flex items-center border rounded bg-muted/40 p-0.5 ml-2">
            <button
              onClick={() => setZoom((z) => Math.min(1.8, z + 0.15))}
              className="p-1 hover:bg-muted rounded text-xs"
              title="Zoom In"
              aria-label="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}
              className="p-1 hover:bg-muted rounded text-xs"
              title="Zoom Out"
              aria-label="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => {
                setZoom(1.0);
                setPan({ x: 40, y: 40 });
              }}
              className="p-1 hover:bg-muted rounded text-xs"
              title="Reset View"
              aria-label="Reset View"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Canvas + Sidebars */}
      <div className="flex flex-1 relative overflow-hidden">
        {/* Node Palette Sidebar */}
        <div className="w-48 border-r bg-muted/20 p-3 space-y-3 z-10 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Add Node
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              {(
                [
                  "input",
                  "retrieval",
                  "guardrail",
                  "transform",
                  "prompt",
                  "llm",
                  "evaluator",
                  "router",
                  "output",
                ] as DAGNodeType[]
              ).map((type) => (
                <button
                  key={type}
                  onClick={() => handleAddNode(type)}
                  className="flex items-center gap-2 p-1.5 rounded border bg-card hover:bg-accent text-xs transition-colors text-left"
                >
                  <Plus className="w-3 h-3 text-muted-foreground" />
                  {getNodeIcon(type)}
                  <span className="capitalize">{type}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Interactive Connection Helper */}
          {connectingSourceId && (
            <div className="p-2 border rounded bg-amber-500/10 border-amber-500/40 text-xs text-amber-700 dark:text-amber-300">
              <p className="font-semibold">Connect Node</p>
              <p className="text-[10px] mt-1">Click the left port on a target node to complete edge.</p>
              <Button
                size="sm"
                variant="ghost"
                className="text-[10px] h-6 mt-1 w-full"
                onClick={() => setConnectingSourceId(null)}
              >
                Cancel
              </Button>
            </div>
          )}
        </div>

        {/* Interactive Infinite Canvas */}
        <div
          className="flex-1 relative cursor-grab active:cursor-grabbing overflow-hidden bg-dot-grid"
          onMouseDown={handleMouseDownCanvas}
          onMouseMove={handleMouseMoveCanvas}
          onMouseUp={handleMouseUpCanvas}
        >
          {/* SVG Connector Edges */}
          <svg
            className="absolute inset-0 pointer-events-none w-full h-full"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "0 0",
            }}
          >
            <defs>
              <marker
                id="dag-arrow"
                viewBox="0 0 10 10"
                refX="6"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="currentColor" className="text-muted-foreground" />
              </marker>
            </defs>

            {graph.edges.map((edge) => {
              const sourceNode = graph.nodes.find((n) => n.id === edge.source);
              const targetNode = graph.nodes.find((n) => n.id === edge.target);
              if (!sourceNode || !targetNode) return null;

              const x1 = sourceNode.position.x + NODE_WIDTH;
              const y1 = sourceNode.position.y + NODE_HEIGHT / 2;
              const x2 = targetNode.position.x;
              const y2 = targetNode.position.y + NODE_HEIGHT / 2;

              const dx = Math.max(40, Math.abs(x2 - x1) * 0.45);
              const pathData = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

              return (
                <g key={edge.id}>
                  <path
                    d={pathData}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeDasharray={edge.condition ? "4 4" : undefined}
                    className="text-border hover:text-primary transition-colors pointer-events-stroke"
                    markerEnd="url(#dag-arrow)"
                  />
                  {edge.condition && (
                    <text
                      x={(x1 + x2) / 2}
                      y={(y1 + y2) / 2 - 8}
                      fill="currentColor"
                      className="text-[10px] font-mono fill-muted-foreground"
                      textAnchor="middle"
                    >
                      [{edge.condition}]
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Canvas Nodes Container */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "0 0",
            }}
          >
            {graph.nodes.map((node) => {
              const colors = NODE_COLORS[node.type];
              const isSelected = selectedNodeId === node.id;
              const stepRecord = executionResult?.step_details[node.id];
              const isRunning = executeMutation.isPending && !stepRecord;
              const isCompleted = stepRecord?.status === "completed";
              const isFailed = stepRecord?.status === "failed";
              const isSkipped = stepRecord?.status === "skipped";

              return (
                <div
                  key={node.id}
                  onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                  style={{
                    left: `${node.position.x}px`,
                    top: `${node.position.y}px`,
                    width: `${NODE_WIDTH}px`,
                  }}
                  className={`absolute pointer-events-auto rounded-lg border bg-card p-3 shadow-sm select-none transition-shadow ${
                    isSelected ? "ring-2 ring-primary shadow-md" : "hover:border-primary/50"
                  } ${isCompleted ? "border-emerald-500 ring-1 ring-emerald-500/30" : ""} ${
                    isFailed ? "border-rose-500 ring-1 ring-rose-500/30" : ""
                  } ${isSkipped ? "opacity-40" : ""}`}
                >
                  {/* Left Connection Port (Input) */}
                  <div
                    onClick={(e) => handlePortClick(e, node.id, false)}
                    className="absolute -left-2.5 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full border-2 border-primary bg-background hover:scale-125 transition-transform flex items-center justify-center cursor-crosshair"
                    title="Connect input port"
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                  </div>

                  {/* Right Connection Port (Output) */}
                  <div
                    onClick={(e) => handlePortClick(e, node.id, true)}
                    className="absolute -right-2.5 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full border-2 border-primary bg-background hover:scale-125 transition-transform flex items-center justify-center cursor-crosshair"
                    title="Connect output port"
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                  </div>

                  {/* Node Header */}
                  <div className="flex items-center justify-between gap-1 mb-1.5">
                    <div className="flex items-center gap-1.5">
                      {getNodeIcon(node.type)}
                      <span className="font-semibold text-xs truncate max-w-[130px]">{node.title}</span>
                    </div>
                    <Badge variant="outline" className={`text-[10px] px-1 py-0 ${colors.text} ${colors.bg}`}>
                      {node.type}
                    </Badge>
                  </div>

                  {/* Node Description & Parameters */}
                  <p className="text-[10px] text-muted-foreground truncate mb-2">{node.description}</p>

                  {/* Step Execution Telemetry Indicator */}
                  {stepRecord && (
                    <div className="flex items-center justify-between text-[10px] pt-1 border-t text-muted-foreground font-mono">
                      <span>{stepRecord.latency_ms}ms</span>
                      <span>{stepRecord.tokens_used} tok</span>
                      <span className="text-emerald-600">${stepRecord.cost_usd.toFixed(5)}</span>
                    </div>
                  )}

                  {isRunning && (
                    <div className="text-[10px] font-mono text-amber-500 animate-pulse">Running step...</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Node Inspector Drawer */}
        {selectedNodeId && (
          <div className="w-72 border-l bg-card p-4 space-y-4 z-10 overflow-y-auto">
            {(() => {
              const node = graph.nodes.find((n) => n.id === selectedNodeId);
              if (!node) return null;
              const stepInfo = executionResult?.step_details[node.id];

              return (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      {getNodeIcon(node.type)}
                      <span className="font-bold text-sm">Node Inspector</span>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteNode(node.id)}
                      className="text-rose-500 hover:text-rose-600 h-7 px-2"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs">Node Title</Label>
                    <Input
                      value={node.title}
                      onChange={(e) => {
                        const val = e.target.value;
                        updateGraph((prev) => ({
                          ...prev,
                          nodes: prev.nodes.map((n) => (n.id === node.id ? { ...n, title: val } : n)),
                        }));
                      }}
                      className="text-xs h-8"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs">Operational Parameters</Label>
                    <pre className="p-2 bg-muted rounded text-[10px] font-mono overflow-auto max-h-36">
                      {JSON.stringify(node.config, null, 2)}
                    </pre>
                  </div>

                  {stepInfo && (
                    <div className="space-y-2 pt-2 border-t">
                      <div className="text-xs font-semibold">Step Telemetry</div>
                      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                        <div className="p-2 border rounded bg-muted/40">
                          <div className="text-[10px] text-muted-foreground">LATENCY</div>
                          <div className="font-bold">{stepInfo.latency_ms} ms</div>
                        </div>
                        <div className="p-2 border rounded bg-muted/40">
                          <div className="text-[10px] text-muted-foreground">COST</div>
                          <div className="font-bold text-emerald-600">${stepInfo.cost_usd.toFixed(6)}</div>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <Label className="text-[10px] text-muted-foreground uppercase">Step Output</Label>
                        <pre className="p-2 bg-muted rounded text-[10px] font-mono overflow-auto max-h-36">
                          {JSON.stringify(stepInfo.outputs, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}
      </div>

      {/* Bottom Telemetry & Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-2.5 border-t bg-card text-xs font-mono">
        <div className="flex items-center gap-4">
          {compileResult && (
            <div className="flex items-center gap-1.5">
              <Badge variant={compileResult.is_valid ? "outline" : "destructive"}>
                {compileResult.is_valid ? "✓ DAG Valid" : "❌ Cycle / Error"}
              </Badge>
              {compileResult.is_valid && (
                <span className="text-muted-foreground text-[11px]">
                  Order: {compileResult.topological_order.join(" → ")}
                </span>
              )}
            </div>
          )}

          {executionResult && (
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 text-emerald-600 font-bold">
                <CheckCircle2 className="w-3.5 h-3.5" /> Pipeline Completed
              </span>
              <span className="flex items-center gap-1 text-muted-foreground">
                <Clock className="w-3.5 h-3.5" /> {executionResult.total_latency_ms}ms
              </span>
              <span className="flex items-center gap-1 text-muted-foreground">
                <DollarSign className="w-3.5 h-3.5 text-emerald-500" /> ${executionResult.total_cost_usd.toFixed(5)} USD
              </span>
              <span className="text-muted-foreground">({executionResult.total_tokens} tokens)</span>
            </div>
          )}
        </div>

        <div className="text-[11px] text-muted-foreground">
          Platform Battery #40 Active • Kahn Cycle Detection Guaranteed
        </div>
      </div>
    </div>
  );
}
