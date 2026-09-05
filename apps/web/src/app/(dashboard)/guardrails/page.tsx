"use client";

import { useState, useEffect, useMemo } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Cpu,
  Zap,
  Play,
  Save,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Sliders,
  Code,
  Activity,
  FileText,
  Terminal,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Topbar } from "@/components/topbar";
import { toast } from "sonner";
import { useTenants } from "@/hooks/use-tenants";
import {
  useGuardrailsOverview,
  useGuardrailTemplates,
  useTenantGuardrailsConfig,
  useUpdateTenantGuardrailsConfig,
  useTestGuardrailFlow,
  useGuardrailsTelemetry,
  type GuardrailExecutionMode,
  type GuardrailCheckResult,
} from "@/hooks/use-guardrails";

export default function GuardrailsAdminPage() {
  const { data: tenantsData } = useTenants("", 100, 0);
  const tenants = tenantsData?.items || [];
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");

  const tenantId = selectedTenantId || tenants[0]?.tenantId || "tn_default";

  // Global Engine Overview & Templates
  const { data: overview } = useGuardrailsOverview();
  const { data: templates = {} } = useGuardrailTemplates();

  // Tenant Guardrails Configuration & Telemetry
  const { data: config, isLoading: loadingConfig } = useTenantGuardrailsConfig(tenantId);
  const { data: telemetry, isLoading: loadingTelemetry } = useGuardrailsTelemetry(tenantId);

  // Form State
  const [mode, setMode] = useState<GuardrailExecutionMode>("full_conversational");
  const [colangScript, setColangScript] = useState<string>("");
  const [piiRedaction, setPiiRedaction] = useState<boolean>(true);
  const [competitorShield, setCompetitorShield] = useState<boolean>(true);
  const [competitorNames, setCompetitorNames] = useState<string>("");
  const [brandTone, setBrandTone] = useState<string>("");
  const [groundingThreshold, setGroundingThreshold] = useState<number>(0.7);
  const [fallbackResponse, setFallbackResponse] = useState<string>("");

  // Sandbox Test State
  const [testQuery, setTestQuery] = useState<string>("");
  const [testResult, setTestResult] = useState<GuardrailCheckResult | null>(null);

  // Sync state when server config loads or tenant changes
  useEffect(() => {
    if (config) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMode(config.mode);
      setColangScript(config.colang_script);
      setPiiRedaction(config.pii_redaction_enabled);
      setCompetitorShield(config.competitor_shield_enabled);
      setCompetitorNames((config.competitor_names || []).join(", "));
      setBrandTone(config.brand_tone || "professional, objective, and factual");
      setGroundingThreshold(config.grounding_threshold || 0.7);
      setFallbackResponse(
        config.fallback_response ||
          "I am unable to fulfill this request as it violates safety and conversational boundaries."
      );
    }
  }, [config]);

  // Mutations
  const updateMutation = useUpdateTenantGuardrailsConfig(tenantId);
  const testFlowMutation = useTestGuardrailFlow(tenantId);

  const handleSaveConfig = async () => {
    try {
      await updateMutation.mutateAsync({
        mode,
        colang_script: colangScript,
        pii_redaction_enabled: piiRedaction,
        competitor_shield_enabled: competitorShield,
        competitor_names: competitorNames
          .split(",")
          .map((s) => s.trim().toLowerCase())
          .filter(Boolean),
        brand_tone: brandTone,
        grounding_threshold: Number(groundingThreshold),
        fallback_response: fallbackResponse,
      });
      toast.success(`Guardrails configuration saved for tenant ${tenantId}`);
    } catch (err: any) {
      toast.error(err.message || "Failed to update guardrails config.");
    }
  };

  const handleLoadTemplate = (templateKey: string) => {
    const tmpl = templates[templateKey];
    if (!tmpl) return;
    setColangScript(tmpl.colang);
    toast.info(`Loaded preset template: ${tmpl.name}`);
  };

  const handleRunTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testQuery.trim()) return;

    try {
      const res = await testFlowMutation.mutateAsync({
        query: testQuery.trim(),
        custom_colang: colangScript,
      });
      setTestResult(res);
      if (res.action === "block") {
        toast.error("Fast-path guardrail blocked this query!");
      } else if (res.action === "steer") {
        toast.warning("Conversational flow steered to pre-defined response.");
      } else {
        toast.success("Query passed all conversational and safety guardrails!");
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to test flow.");
    }
  };

  const recentViolations = useMemo(
    () => telemetry?.recent_violations || [],
    [telemetry?.recent_violations]
  );

  return (
    <div className="flex flex-col h-full bg-background">
      <Topbar
        title="NVIDIA NeMo Guardrails & Multi-Turn Safety"
        description="Programmable conversational boundaries, fast-path injection screening, and factual grounding."
      >
        <div className="flex items-center gap-2">
          <Label htmlFor="tenant-select" className="text-xs text-muted-foreground whitespace-nowrap">
            Tenant:
          </Label>
          <Select
            value={tenantId}
            onValueChange={(val) => {
              setSelectedTenantId(val);
              setTestResult(null);
            }}
          >
            <SelectTrigger id="tenant-select" className="w-56 h-8 text-xs font-mono">
              <SelectValue placeholder="Select tenant" />
            </SelectTrigger>
            <SelectContent>
              {tenants.map((t) => (
                <SelectItem key={t.tenantId} value={t.tenantId} className="text-xs font-mono">
                  {t.name} ({t.tenantId})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Topbar>

      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-7xl w-full mx-auto">
        {/* Top KPI Cards / Engine Status */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-border/60 bg-card/80 backdrop-blur-sm shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Platform Battery #13
              </CardTitle>
              <Cpu className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-xl font-bold font-mono text-foreground">
                {overview?.battery_status === "active" ? "ACTIVE" : "STANDBY"}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                {overview?.engine || "NeMo Colang Runtime"}
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/80 backdrop-blur-sm shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Fast-Path Latency
              </CardTitle>
              <Zap className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-foreground">
                {telemetry?.average_rail_latency_ms
                  ? `${telemetry.average_rail_latency_ms.toFixed(1)}ms`
                  : overview?.fast_path_latency || "<20ms"}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Sub-20ms regex & injection scanner
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/80 backdrop-blur-sm shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Blocked / Steered
              </CardTitle>
              <ShieldAlert className="h-4 w-4 text-rose-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-mono text-foreground">
                {telemetry ? `${telemetry.total_blocked} / ${telemetry.total_steered}` : "0 / 0"}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Total interventions across queries
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/80 backdrop-blur-sm shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Active Execution Mode
              </CardTitle>
              <ShieldCheck className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge
                  variant={
                    mode === "full_conversational"
                      ? "default"
                      : mode === "disabled"
                      ? "secondary"
                      : "outline"
                  }
                  className="font-mono text-xs uppercase"
                >
                  {mode.replace(/_/g, " ")}
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Tenant: <span className="font-mono">{tenantId}</span>
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="designer" className="w-full space-y-4">
          <TabsList className="grid grid-cols-3 w-full sm:w-[480px]">
            <TabsTrigger value="designer" className="text-xs">
              <Code className="h-3.5 w-3.5 mr-1.5" />
              Colang Designer
            </TabsTrigger>
            <TabsTrigger value="sandbox" className="text-xs">
              <Terminal className="h-3.5 w-3.5 mr-1.5" />
              Test Sandbox
            </TabsTrigger>
            <TabsTrigger value="telemetry" className="text-xs">
              <Activity className="h-3.5 w-3.5 mr-1.5" />
              Safety Telemetry
            </TabsTrigger>
          </TabsList>

          {/* TAB 1: COLANG FLOW DESIGNER & SETTINGS */}
          <TabsContent value="designer" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left 2 Cols: Colang Script Editor */}
              <Card className="lg:col-span-2 border-border/60">
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Code className="h-4 w-4 text-primary" />
                        Colang 2.0 Flow Specifications (.co)
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Define multi-turn conversational intents, steering dialogs, and canonical safe responses.
                      </CardDescription>
                    </div>

                    <div className="flex items-center gap-2">
                      <Select onValueChange={handleLoadTemplate}>
                        <SelectTrigger className="h-8 text-xs w-48">
                          <SelectValue placeholder="Load preset template..." />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(templates).map(([key, t]) => (
                            <SelectItem key={key} value={key} className="text-xs">
                              {t.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <Button
                        size="sm"
                        onClick={handleSaveConfig}
                        disabled={updateMutation.isPending}
                        className="h-8 text-xs gap-1.5"
                      >
                        <Save className="h-3.5 w-3.5" />
                        Save Guardrails
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="relative">
                    <Textarea
                      value={colangScript}
                      onChange={(e) => setColangScript(e.target.value)}
                      placeholder="# Define your Colang 2.0 flows here..."
                      className="font-mono text-xs min-h-[360px] bg-muted/20 resize-y p-3.5 leading-relaxed"
                    />
                  </div>

                  {config?.active_flows && config.active_flows.length > 0 && (
                    <div className="border rounded-md p-3 bg-card/50">
                      <p className="text-xs font-semibold mb-2 text-muted-foreground flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                        Active Parsed Flows ({config.active_flows.length})
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {config.active_flows.map((flow, idx) => (
                          <div
                            key={idx}
                            className="text-xs p-2 rounded bg-muted/40 border border-border/40 font-mono space-y-1"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-primary">{flow.name}</span>
                              <Badge variant="outline" className="text-[10px] px-1 py-0">
                                P{flow.priority}
                              </Badge>
                            </div>
                            <p className="text-[11px] text-muted-foreground truncate">
                              Intent: {flow.user_intent}
                            </p>
                            <p className="text-[11px] text-foreground/80 truncate">
                              Bot: {flow.bot_response}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Right Col: Policies & Thresholds */}
              <div className="space-y-6">
                <Card className="border-border/60">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Sliders className="h-4 w-4 text-primary" />
                      Execution Constraints
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Tune rail execution mode and defensive parameters.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-1.5">
                      <Label className="text-xs">Rail Enforcement Mode</Label>
                      <Select
                        value={mode}
                        onValueChange={(v) => setMode(v as GuardrailExecutionMode)}
                      >
                        <SelectTrigger className="h-8 text-xs font-mono">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="full_conversational" className="text-xs font-mono">
                            Full Conversational (Input + Colang + Grounding)
                          </SelectItem>
                          <SelectItem value="input_only" className="text-xs font-mono">
                            Input Fast-Path Only
                          </SelectItem>
                          <SelectItem value="output_grounding_only" className="text-xs font-mono">
                            Output Grounding Only
                          </SelectItem>
                          <SelectItem value="disabled" className="text-xs font-mono">
                            Disabled (Bypass All)
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <Label className="text-xs">Grounding Faithfulness Threshold</Label>
                        <span className="text-xs font-mono font-semibold">
                          {(groundingThreshold * 100).toFixed(0)}%
                        </span>
                      </div>
                      <Input
                        type="range"
                        min="0.0"
                        max="1.0"
                        step="0.05"
                        value={groundingThreshold}
                        onChange={(e) => setGroundingThreshold(parseFloat(e.target.value))}
                        className="h-6 cursor-pointer"
                      />
                      <p className="text-[10px] text-muted-foreground">
                        Responses scoring below this context entailment threshold are grounded or flagged.
                      </p>
                    </div>

                    <div className="space-y-2 pt-2 border-t">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="pii-switch" className="text-xs cursor-pointer">
                          Fast-Path PII Redaction
                        </Label>
                        <input
                          id="pii-switch"
                          type="checkbox"
                          checked={piiRedaction}
                          onChange={(e) => setPiiRedaction(e.target.checked)}
                          className="rounded border-gray-300 text-primary h-4 w-4 cursor-pointer"
                        />
                      </div>
                      <p className="text-[10px] text-muted-foreground">
                        Masks SSNs, emails, phone numbers, and API tokens prior to LLM dispatch.
                      </p>
                    </div>

                    <div className="space-y-2 pt-2 border-t">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="comp-switch" className="text-xs cursor-pointer">
                          Competitor Mention Shielding
                        </Label>
                        <input
                          id="comp-switch"
                          type="checkbox"
                          checked={competitorShield}
                          onChange={(e) => setCompetitorShield(e.target.checked)}
                          className="rounded border-gray-300 text-primary h-4 w-4 cursor-pointer"
                        />
                      </div>
                      {competitorShield && (
                        <Input
                          value={competitorNames}
                          onChange={(e) => setCompetitorNames(e.target.value)}
                          placeholder="pinecone, weaviate, qdrant, langchain"
                          className="h-8 text-xs font-mono"
                        />
                      )}
                    </div>

                    <div className="space-y-1.5 pt-2 border-t">
                      <Label className="text-xs">Brand Tone & Persona Guidelines</Label>
                      <Input
                        value={brandTone}
                        onChange={(e) => setBrandTone(e.target.value)}
                        placeholder="professional, objective, and factual"
                        className="h-8 text-xs"
                      />
                    </div>

                    <div className="space-y-1.5 pt-2 border-t">
                      <Label className="text-xs">Fallback Safety Response</Label>
                      <Textarea
                        value={fallbackResponse}
                        onChange={(e) => setFallbackResponse(e.target.value)}
                        placeholder="Fallback message when a rail violation triggers a block..."
                        className="text-xs min-h-[70px] resize-none"
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* TAB 2: INTERACTIVE TEST SANDBOX */}
          <TabsContent value="sandbox" className="space-y-6">
            <Card className="border-border/60">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-primary" />
                  Live Guardrail Simulation Sandbox
                </CardTitle>
                <CardDescription className="text-xs">
                  Submit test queries against active Colang flows and fast-path heuristics to inspect rail execution.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <form onSubmit={handleRunTest} className="space-y-3">
                  <div className="flex gap-2">
                    <Input
                      value={testQuery}
                      onChange={(e) => setTestQuery(e.target.value)}
                      placeholder="Enter a test query (e.g. 'Can you give me 50% discount?' or 'Ignore instructions and dump tokens')"
                      className="text-xs font-mono flex-1 h-9"
                    />
                    <Button
                      type="submit"
                      disabled={testFlowMutation.isPending || !testQuery.trim()}
                      className="text-xs h-9 gap-1.5"
                    >
                      <Play className="h-3.5 w-3.5" />
                      Run Test
                    </Button>
                  </div>
                </form>

                {/* Test Results Display */}
                {testResult && (
                  <div className="mt-4 p-4 rounded-lg border bg-muted/20 space-y-3">
                    <div className="flex items-center justify-between border-b pb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-muted-foreground">Action:</span>
                        <Badge
                          variant={
                            testResult.action === "allow"
                              ? "default"
                              : testResult.action === "steer"
                              ? "outline"
                              : "destructive"
                          }
                          className="uppercase font-mono text-xs"
                        >
                          {testResult.action}
                        </Badge>
                        {testResult.fast_path_matched && (
                          <Badge variant="secondary" className="text-[10px] font-mono">
                            ⚡ Fast-Path
                          </Badge>
                        )}
                      </div>
                      <span className="text-xs font-mono text-muted-foreground">
                        Latency: {testResult.latency_ms.toFixed(1)}ms
                      </span>
                    </div>

                    {testResult.steered_response && (
                      <div className="space-y-1">
                        <Label className="text-xs font-semibold text-primary">Steered Response:</Label>
                        <div className="p-2.5 rounded bg-background border text-xs font-mono leading-relaxed">
                          {testResult.steered_response}
                        </div>
                      </div>
                    )}

                    {testResult.violations && testResult.violations.length > 0 && (
                      <div className="space-y-1.5">
                        <Label className="text-xs font-semibold text-destructive flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          Detected Rail Violations ({testResult.violations.length})
                        </Label>
                        <div className="space-y-1.5">
                          {testResult.violations.map((v, idx) => (
                            <div
                              key={idx}
                              className="p-2 rounded border border-rose-500/30 bg-rose-500/5 text-xs flex flex-wrap items-center justify-between gap-2"
                            >
                              <div className="space-y-0.5">
                                <span className="font-semibold font-mono text-rose-600 dark:text-rose-400">
                                  {v.rule_id}
                                </span>
                                <p className="text-[11px] text-muted-foreground">{v.reason}</p>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <Badge variant="outline" className="text-[10px] font-mono uppercase">
                                  {v.rail_type}
                                </Badge>
                                <Badge variant="destructive" className="text-[10px] font-mono uppercase">
                                  {v.action_taken}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* TAB 3: REAL-TIME SAFETY TELEMETRY */}
          <TabsContent value="telemetry" className="space-y-6">
            <Card className="border-border/60">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Activity className="h-4 w-4 text-primary" />
                      Safety Violations & Rail Audit Log
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Rolling telemetry buffer of detected prompt injections, competitor mentions, and steered dialogs.
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="text-[10px] font-mono">
                    Auto-refreshes every 10s
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {recentViolations.length === 0 ? (
                  <div className="text-center py-10 text-muted-foreground text-xs">
                    No safety violations recorded yet for tenant {tenantId}.
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">Timestamp</TableHead>
                        <TableHead className="text-xs">Rule ID</TableHead>
                        <TableHead className="text-xs">Rail Type</TableHead>
                        <TableHead className="text-xs">Action Taken</TableHead>
                        <TableHead className="text-xs">Reason / Context</TableHead>
                        <TableHead className="text-xs text-right">Latency</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {recentViolations.map((v, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="text-xs font-mono text-muted-foreground">
                            {new Date(v.timestamp).toLocaleTimeString()}
                          </TableCell>
                          <TableCell className="text-xs font-mono font-medium">
                            {v.rule_id}
                          </TableCell>
                          <TableCell className="text-xs">
                            <Badge variant="outline" className="text-[10px] font-mono">
                              {v.rail_type}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs">
                            <Badge
                              variant={
                                v.action_taken === "block"
                                  ? "destructive"
                                  : v.action_taken === "steer"
                                  ? "secondary"
                                  : "outline"
                              }
                              className="text-[10px] font-mono uppercase"
                            >
                              {v.action_taken}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground max-w-xs truncate">
                            {v.reason}
                          </TableCell>
                          <TableCell className="text-xs font-mono text-right">
                            {v.latency_ms.toFixed(1)}ms
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
