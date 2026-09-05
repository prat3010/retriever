"use client";

import { useState, useEffect } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Zap,
  Play,
  Save,
  CheckCircle2,
  AlertTriangle,
  Sliders,
  Code,
  Activity,
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
import { toast } from "sonner";
import {
  useTenantGuardrailsConfig,
  useUpdateTenantGuardrailsConfig,
  useTestGuardrailFlow,
  useGuardrailsTelemetry,
  useGuardrailTemplates,
  type GuardrailExecutionMode,
  type GuardrailCheckResult,
} from "@/hooks/use-guardrails";

interface TenantGuardrailsTabProps {
  tenantId: string;
}

export function TenantGuardrailsTab({ tenantId }: TenantGuardrailsTabProps) {
  const { data: templates = {} } = useGuardrailTemplates();
  const { data: config, isLoading: loadingConfig } = useTenantGuardrailsConfig(tenantId);
  const { data: telemetry } = useGuardrailsTelemetry(tenantId);

  // Form State
  const [mode, setMode] = useState<GuardrailExecutionMode>("full_conversational");
  const [colangScript, setColangScript] = useState<string>("");
  const [piiRedaction, setPiiRedaction] = useState<boolean>(true);
  const [competitorShield, setCompetitorShield] = useState<boolean>(true);
  const [competitorNames, setCompetitorNames] = useState<string>("");
  const [brandTone, setBrandTone] = useState<string>("");
  const [groundingThreshold, setGroundingThreshold] = useState<number>(0.7);
  const [fallbackResponse, setFallbackResponse] = useState<string>("");

  // Test Sandbox State
  const [testQuery, setTestQuery] = useState<string>("");
  const [testResult, setTestResult] = useState<GuardrailCheckResult | null>(null);

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

  const updateMutation = useUpdateTenantGuardrailsConfig(tenantId);
  const testFlowMutation = useTestGuardrailFlow(tenantId);

  const handleSave = async () => {
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
      toast.success("Tenant guardrails configuration updated successfully!");
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

  if (loadingConfig) {
    return <div className="p-6 text-sm text-muted-foreground">Loading guardrail configuration...</div>;
  }

  const recentViolations = telemetry?.recent_violations || [];

  return (
    <div className="space-y-6">
      {/* Top Status & Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-border/60 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Enforcement Mode
            </CardTitle>
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <Badge variant="default" className="font-mono text-xs uppercase">
              {mode.replace(/_/g, " ")}
            </Badge>
            <p className="text-[11px] text-muted-foreground mt-1">
              Active NeMo conversational policy
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Rail Latency SLA
            </CardTitle>
            <Zap className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-foreground">
              {telemetry?.average_rail_latency_ms
                ? `${telemetry.average_rail_latency_ms.toFixed(1)}ms`
                : "<20ms"}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              Sub-20ms regex & injection scanner
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/80">
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
              Interventions recorded for this tenant
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="designer" className="space-y-4">
        <TabsList className="grid grid-cols-3 w-full sm:w-[450px]">
          <TabsTrigger value="designer" className="text-xs">
            <Code className="h-3.5 w-3.5 mr-1.5" />
            Colang Flows
          </TabsTrigger>
          <TabsTrigger value="sandbox" className="text-xs">
            <Terminal className="h-3.5 w-3.5 mr-1.5" />
            Test Sandbox
          </TabsTrigger>
          <TabsTrigger value="telemetry" className="text-xs">
            <Activity className="h-3.5 w-3.5 mr-1.5" />
            Telemetry
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Designer */}
        <TabsContent value="designer" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 border-border/60">
              <CardHeader>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <Code className="h-4 w-4 text-primary" />
                      Colang 2.0 Script (.co)
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Multi-turn intent definitions, steering branches, and canonical bot responses.
                    </CardDescription>
                  </div>

                  <div className="flex items-center gap-2">
                    <Select onValueChange={handleLoadTemplate}>
                      <SelectTrigger className="h-8 text-xs w-44">
                        <SelectValue placeholder="Preset template..." />
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
                      onClick={handleSave}
                      disabled={updateMutation.isPending}
                      className="h-8 text-xs gap-1.5"
                    >
                      <Save className="h-3.5 w-3.5" />
                      Save
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  value={colangScript}
                  onChange={(e) => setColangScript(e.target.value)}
                  placeholder="# Define Colang flows..."
                  className="font-mono text-xs min-h-[320px] bg-muted/20 resize-y p-3.5 leading-relaxed"
                />

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
                          <span className="font-semibold text-primary">{flow.name}</span>
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

            {/* Sidebar Policies */}
            <Card className="border-border/60">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Sliders className="h-4 w-4 text-primary" />
                  Policy Controls
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1.5">
                  <Label className="text-xs">Execution Mode</Label>
                  <Select
                    value={mode}
                    onValueChange={(v) => setMode(v as GuardrailExecutionMode)}
                  >
                    <SelectTrigger className="h-8 text-xs font-mono">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="full_conversational" className="text-xs font-mono">
                        Full Conversational
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
                    <Label className="text-xs">Grounding Threshold</Label>
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
                </div>

                <div className="space-y-2 pt-2 border-t">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="pii-t-switch" className="text-xs cursor-pointer">
                      PII Redaction
                    </Label>
                    <input
                      id="pii-t-switch"
                      type="checkbox"
                      checked={piiRedaction}
                      onChange={(e) => setPiiRedaction(e.target.checked)}
                      className="rounded border-gray-300 text-primary h-4 w-4 cursor-pointer"
                    />
                  </div>
                </div>

                <div className="space-y-2 pt-2 border-t">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="comp-t-switch" className="text-xs cursor-pointer">
                      Competitor Shield
                    </Label>
                    <input
                      id="comp-t-switch"
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
                      placeholder="pinecone, weaviate, qdrant"
                      className="h-8 text-xs font-mono"
                    />
                  )}
                </div>

                <div className="space-y-1.5 pt-2 border-t">
                  <Label className="text-xs">Brand Tone</Label>
                  <Input
                    value={brandTone}
                    onChange={(e) => setBrandTone(e.target.value)}
                    placeholder="professional, objective"
                    className="h-8 text-xs"
                  />
                </div>

                <div className="space-y-1.5 pt-2 border-t">
                  <Label className="text-xs">Fallback Safety Response</Label>
                  <Textarea
                    value={fallbackResponse}
                    onChange={(e) => setFallbackResponse(e.target.value)}
                    placeholder="Fallback response on violation..."
                    className="text-xs min-h-[60px] resize-none"
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab 2: Test Sandbox */}
        <TabsContent value="sandbox" className="space-y-4">
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Terminal className="h-4 w-4 text-primary" />
                Prompt Evaluation Sandbox
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <form onSubmit={handleRunTest} className="flex gap-2">
                <Input
                  value={testQuery}
                  onChange={(e) => setTestQuery(e.target.value)}
                  placeholder="Enter a test query..."
                  className="text-xs font-mono flex-1 h-9"
                />
                <Button
                  type="submit"
                  disabled={testFlowMutation.isPending || !testQuery.trim()}
                  className="text-xs h-9 gap-1.5"
                >
                  <Play className="h-3.5 w-3.5" />
                  Test
                </Button>
              </form>

              {testResult && (
                <div className="p-4 rounded-lg border bg-muted/20 space-y-3">
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
                        Violations ({testResult.violations.length})
                      </Label>
                      <div className="space-y-1.5">
                        {testResult.violations.map((v, idx) => (
                          <div
                            key={idx}
                            className="p-2 rounded border border-rose-500/30 bg-rose-500/5 text-xs flex items-center justify-between gap-2"
                          >
                            <span className="font-mono text-rose-600 dark:text-rose-400 font-semibold">
                              {v.rule_id}
                            </span>
                            <span className="text-muted-foreground truncate">{v.reason}</span>
                            <Badge variant="destructive" className="text-[10px] uppercase font-mono">
                              {v.action_taken}
                            </Badge>
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

        {/* Tab 3: Telemetry */}
        <TabsContent value="telemetry" className="space-y-4">
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                Recent Safety Violations
              </CardTitle>
            </CardHeader>
            <CardContent>
              {recentViolations.length === 0 ? (
                <div className="text-center py-8 text-xs text-muted-foreground">
                  No violations logged for this tenant.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Timestamp</TableHead>
                      <TableHead className="text-xs">Rule ID</TableHead>
                      <TableHead className="text-xs">Rail Type</TableHead>
                      <TableHead className="text-xs">Action</TableHead>
                      <TableHead className="text-xs">Reason</TableHead>
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
                        <TableCell className="text-xs font-mono">{v.rail_type}</TableCell>
                        <TableCell className="text-xs">
                          <Badge
                            variant={v.action_taken === "block" ? "destructive" : "outline"}
                            className="text-[10px] uppercase font-mono"
                          >
                            {v.action_taken}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground truncate max-w-xs">
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
  );
}
