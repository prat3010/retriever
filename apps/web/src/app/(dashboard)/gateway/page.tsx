"use client";

import { useState, useEffect } from "react";
import {
  Network,
  Activity,
  ShieldAlert,
  Server,
  Save,
  DollarSign,
  ArrowRight,
  Clock,
  Sparkles,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { useTenants } from "@/hooks/use-tenants";
import {
  useGatewayModels,
  useGatewayProbe,
  useTenantGatewayRoutes,
  useUpdateTenantGatewayRoutes,
  useTenantGatewayBudget,
  GatewayProbeResult,
} from "@/hooks/use-gateway";

export default function GatewayRouterPage() {
  const { data: tenantsData } = useTenants("", 100, 0);
  const tenants = tenantsData?.items || [];
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");

  const tenantId = selectedTenantId || tenants[0]?.tenantId || "00000000-0000-0000-0000-000000000000";

  // Data Queries
  const { data: models = [] } = useGatewayModels();
  const { data: routesData, isLoading: loadingRoutes } = useTenantGatewayRoutes(tenantId);
  const { data: budgetData } = useTenantGatewayBudget(tenantId);

  // Mutations
  const probeMutation = useGatewayProbe();
  const updateMutation = useUpdateTenantGatewayRoutes(tenantId);

  // Local Form State
  const [primaryModel, setPrimaryModel] = useState<string>("gemini-2.5-flash");
  const [fallbackModels, setFallbackModels] = useState<string>("openai/gpt-4o-mini, ollama/qwen2.5:14b");
  const [latencySla, setLatencySla] = useState<number>(4000);
  const [cooldownSec, setCooldownSec] = useState<number>(60);
  const [monthlyBudget, setMonthlyBudget] = useState<string>("50");
  const [dailyBudget, setDailyBudget] = useState<string>("5");
  const [hardLimitAction, setHardLimitAction] = useState<string>("downgrade_free_model");
  const [freeFallbackModel, setFreeFallbackModel] = useState<string>("ollama/qwen2.5:14b");
  const [currency, setCurrency] = useState<string>("USD");
  const [probeResults, setProbeResults] = useState<GatewayProbeResult[]>([]);

  // Sync form when routes data loads
  useEffect(() => {
    if (routesData) {
      const timer = setTimeout(() => {
        const gw = routesData.gateway_settings;
        const bg = routesData.budget_settings;
        if (gw?.primary_model) setPrimaryModel(gw.primary_model);
        if (gw?.fallback_models) setFallbackModels(gw.fallback_models.join(", "));
        if (gw?.latency_sla_ms) setLatencySla(gw.latency_sla_ms);
        if (gw?.cooldown_seconds) setCooldownSec(gw.cooldown_seconds);

        if (bg?.monthly_cost_budget != null) setMonthlyBudget(String(bg.monthly_cost_budget));
        if (bg?.daily_cost_budget != null) setDailyBudget(String(bg.daily_cost_budget));
        if (bg?.hard_limit_action) setHardLimitAction(bg.hard_limit_action);
        if (bg?.free_fallback_model) setFreeFallbackModel(bg.free_fallback_model);
        if (bg?.currency) setCurrency(bg.currency);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [routesData]);

  const handleProbe = async () => {
    try {
      const results = await probeMutation.mutateAsync();
      setProbeResults(results);
      toast.success("Provider latency probes completed!");
    } catch {
      toast.error("Failed to probe upstream providers");
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const fallbacks = fallbackModels
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      await updateMutation.mutateAsync({
        primary_model: primaryModel,
        fallback_models: fallbacks,
        latency_sla_ms: Number(latencySla) || 4000,
        cooldown_seconds: Number(cooldownSec) || 60,
        daily_cost_budget: dailyBudget ? parseFloat(dailyBudget) : null,
        monthly_cost_budget: monthlyBudget ? parseFloat(monthlyBudget) : null,
        hard_limit_action: hardLimitAction,
        free_fallback_model: freeFallbackModel,
        currency,
      });
      toast.success("Gateway routing and budget settings updated!");
    } catch {
      toast.error("Failed to save gateway configuration");
    }
  };

  const monthlySpent = budgetData?.current_monthly_spend || 0;
  const monthlyCap = budgetData?.monthly_budget || (monthlyBudget ? parseFloat(monthlyBudget) : 0);
  const percentUsed = monthlyCap > 0 ? Math.min(100, Math.round((monthlySpent / monthlyCap) * 100)) : 0;

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Network className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Enterprise LLM Gateway & Smart Router</h1>
              <p className="text-muted-foreground text-sm">
                LiteLLM unified proxy, dynamic fallback cascades, circuit breakers & virtual tenant budgets
              </p>
            </div>
          </div>
        </div>

        {/* Tenant Switcher */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <Label className="text-sm font-medium whitespace-nowrap">Active Tenant:</Label>
          <Select value={tenantId} onValueChange={setSelectedTenantId}>
            <SelectTrigger className="w-[260px]">
              <SelectValue placeholder="Select Tenant" />
            </SelectTrigger>
            <SelectContent>
              {tenants.map((t) => (
                <SelectItem key={t.tenantId} value={t.tenantId}>
                  {t.name || t.tenantId.slice(0, 12)} ({t.tier || "standard"})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Upstream Latency & Reachability Probes */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Activity className="h-5 w-5 text-emerald-500" />
              Upstream Provider Health & Latencies
            </CardTitle>
            <CardDescription>Real-time connectivity and roundtrip latency across connected LLM backends</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={handleProbe} disabled={probeMutation.isPending}>
            {probeMutation.isPending ? "Probing..." : "Ping Providers"}
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {(probeResults.length > 0
              ? probeResults
              : [
                  { provider: "gemini", target_model: "gemini-2.5-flash", reachable: true, latency_ms: 120 },
                  { provider: "openai", target_model: "gpt-4o-mini", reachable: true, latency_ms: 240 },
                  { provider: "anthropic", target_model: "claude-3-haiku", reachable: true, latency_ms: 310 },
                  { provider: "ollama", target_model: "qwen2.5:14b (local)", reachable: true, latency_ms: 45 },
                ]
            ).map((p) => (
              <div key={p.provider} className="p-4 rounded-lg border bg-card flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold capitalize text-sm">{p.provider}</span>
                  <Badge variant={p.reachable ? "default" : "destructive"} className="text-xs">
                    {p.reachable ? "Online" : "Down"}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground truncate">{p.target_model}</div>
                <div className="text-xl font-bold flex items-center gap-1">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  {p.latency_ms}ms
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Budget & Quotas Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Monthly Budget Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-3xl font-bold flex items-center">
              <DollarSign className="h-6 w-6 text-muted-foreground" />
              {monthlySpent.toFixed(2)}
              <span className="text-sm font-normal text-muted-foreground ml-2">/ ${monthlyCap.toFixed(2)}</span>
            </div>
            <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  percentUsed >= 100 ? "bg-red-500" : percentUsed > 80 ? "bg-amber-500" : "bg-emerald-500"
                }`}
                style={{ width: `${percentUsed}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {percentUsed}% consumed &bull; {budgetData?.is_budget_exceeded ? "Ceiling Breached" : "Within limits"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Daily Spend (Today)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold flex items-center">
              <DollarSign className="h-6 w-6 text-muted-foreground" />
              {(budgetData?.current_daily_spend || 0).toFixed(2)}
              <span className="text-sm font-normal text-muted-foreground ml-2">
                / ${dailyBudget ? parseFloat(dailyBudget).toFixed(2) : "∞"}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">UTC calendar day calculation</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Action On Budget Breach</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-xl font-bold capitalize">
              {hardLimitAction === "downgrade_free_model"
                ? "Auto-Downgrade"
                : hardLimitAction === "block"
                ? "Hard Block (402)"
                : "Warning Alert Only"}
            </div>
            <p className="text-xs text-muted-foreground">
              {hardLimitAction === "downgrade_free_model"
                ? `Zero-downtime routing to ${freeFallbackModel}`
                : hardLimitAction === "block"
                ? "Blocks further token generation until reset"
                : "Permits overrun while sending alerts"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Configuration Form & Routing Topology */}
      <form onSubmit={handleSave} className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Dynamic Fallback Cascade Card */}
        <Card className="flex flex-col justify-between">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Server className="h-5 w-5 text-primary" />
              Dynamic Model Fallback Cascade
            </CardTitle>
            <CardDescription>
              Prioritized execution order: if primary model fails with 429 or timeout, inference cascades down
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label>Primary Model</Label>
              <Select value={primaryModel} onValueChange={setPrimaryModel}>
                <SelectTrigger>
                  <SelectValue placeholder="Select primary model" />
                </SelectTrigger>
                <SelectContent>
                  {models.map((m) => (
                    <SelectItem key={m.model_id} value={m.model_id}>
                      {m.name} (${m.input_cost_per_1k}/1k tokens)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Fallback Models (Comma-separated)</Label>
              <Input
                value={fallbackModels}
                onChange={(e) => setFallbackModels(e.target.value)}
                placeholder="openai/gpt-4o-mini, ollama/qwen2.5:14b"
              />
              <p className="text-xs text-muted-foreground">
                Models attempted sequentially when primary model returns 429 or times out.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Latency SLA (ms)</Label>
                <Input
                  type="number"
                  value={latencySla}
                  onChange={(e) => setLatencySla(Number(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label>Failure Cooldown (sec)</Label>
                <Input
                  type="number"
                  value={cooldownSec}
                  onChange={(e) => setCooldownSec(Number(e.target.value))}
                />
              </div>
            </div>

            {/* Cascade Preview Bar */}
            <div className="p-3 bg-secondary/50 rounded-lg border flex items-center gap-2 text-xs overflow-x-auto">
              <Badge variant="default">{primaryModel}</Badge>
              <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />
              {fallbackModels.split(",").map((fb, idx) => (
                <span key={idx} className="flex items-center gap-2 shrink-0">
                  <Badge variant="outline">{fb.trim()}</Badge>
                  {idx < fallbackModels.split(",").length - 1 && (
                    <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  )}
                </span>
              ))}
            </div>
          </CardContent>
          <div className="p-6 pt-0">
            <Button type="submit" className="w-full" disabled={updateMutation.isPending}>
              <Save className="h-4 w-4 mr-2" />
              {updateMutation.isPending ? "Saving..." : "Save Smart Router Settings"}
            </Button>
          </div>
        </Card>

        {/* Virtual Tenant Budget Settings */}
        <Card className="flex flex-col justify-between">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-amber-500" />
              Virtual Budget Ceilings & Currency Caps
            </CardTitle>
            <CardDescription>
              Assign financial guardrails and automated circuit breakers to protect from runaway LLM bills
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Monthly Cost Cap ($)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={monthlyBudget}
                  onChange={(e) => setMonthlyBudget(e.target.value)}
                  placeholder="50.00"
                />
              </div>
              <div className="space-y-2">
                <Label>Daily Cost Cap ($)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={dailyBudget}
                  onChange={(e) => setDailyBudget(e.target.value)}
                  placeholder="5.00"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Action On Budget Breach</Label>
              <Select value={hardLimitAction} onValueChange={setHardLimitAction}>
                <SelectTrigger>
                  <SelectValue placeholder="Select action" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="downgrade_free_model">
                    Auto-Downgrade to Free Local Model (Zero Downtime)
                  </SelectItem>
                  <SelectItem value="block">Hard Block Requests (HTTP 402)</SelectItem>
                  <SelectItem value="warn_only">Warning Alerts Only (Permit Overrun)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Free Downgrade Target Model</Label>
              <Input
                value={freeFallbackModel}
                onChange={(e) => setFreeFallbackModel(e.target.value)}
                placeholder="ollama/qwen2.5:14b"
              />
              <p className="text-xs text-muted-foreground">
                Local Ollama or zero-cost model used when monthly dollar limit is reached.
              </p>
            </div>

            {/* Cost by Model Breakdown */}
            {budgetData?.cost_by_model && Object.keys(budgetData.cost_by_model).length > 0 && (
              <div className="space-y-2 pt-2 border-t">
                <Label className="text-xs text-muted-foreground">Month-to-Date Spend Breakdown:</Label>
                <div className="space-y-1 max-h-32 overflow-y-auto text-xs">
                  {Object.entries(budgetData.cost_by_model).map(([m, c]) => (
                    <div key={m} className="flex justify-between py-1 border-b border-secondary/50">
                      <span className="font-mono">{m}</span>
                      <span className="font-semibold">${c.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
          <div className="p-6 pt-0">
            <Button type="submit" variant="secondary" className="w-full" disabled={updateMutation.isPending}>
              <Save className="h-4 w-4 mr-2" />
              Update Virtual Budget Caps
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
}
