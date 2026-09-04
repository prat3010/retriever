"use client";

import { useState } from "react";
import {
  Puzzle,
  MessageSquare,
  Chrome,
  FolderSync,
  FileText,
  Copy,
  Check,
  Download,
  Play,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useIntegrationsOverview } from "@/hooks/use-integrations";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function IntegrationsPage() {
  const { data: overview, isLoading } = useIntegrationsOverview();

  const [copiedWebhook, setCopiedWebhook] = useState(false);
  const [copiedSlash, setCopiedSlash] = useState(false);
  const [testQuery, setTestQuery] = useState("What is our production deployment policy?");
  const [simulatedBlockKit, setSimulatedBlockKit] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);

  // Simulated sync states
  const [gdriveSyncing, setGdriveSyncing] = useState(false);
  const [gdriveSuccess, setGdriveSuccess] = useState(false);
  const [notionSyncing, setNotionSyncing] = useState(false);
  const [notionSuccess, setNotionSuccess] = useState(false);

  const webhookUrl = `${API_BASE}/v1/integrations/slack/slash`;
  const extensionDownloadUrl = `${API_BASE}/v1/integrations/extension/bundle`;

  function handleCopyWebhook() {
    navigator.clipboard.writeText(webhookUrl);
    setCopiedWebhook(true);
    setTimeout(() => setCopiedWebhook(false), 2000);
  }

  function handleCopySlash() {
    navigator.clipboard.writeText("/ask-retriever");
    setCopiedSlash(true);
    setTimeout(() => setCopiedSlash(false), 2000);
  }

  async function handleSimulateSlack() {
    if (!testQuery.trim()) return;
    setSimulating(true);
    try {
      const res = await fetch(webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: testQuery,
          user_name: "DevOps Engineer",
          channel_id: "C0123456789",
          team_id: "T0987654321",
        }),
      });
      const data = await res.json();
      setSimulatedBlockKit(data);
    } catch (e) {
      console.error(e);
    } finally {
      setSimulating(false);
    }
  }

  function handleTriggerGdriveSync() {
    setGdriveSyncing(true);
    setTimeout(() => {
      setGdriveSyncing(false);
      setGdriveSuccess(true);
      setTimeout(() => setGdriveSuccess(false), 3000);
    }, 1200);
  }

  function handleTriggerNotionSync() {
    setNotionSyncing(true);
    setTimeout(() => {
      setNotionSyncing(false);
      setNotionSuccess(true);
      setTimeout(() => setNotionSuccess(false), 1200);
    }, 1200);
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">Ecosystem Plugins & Integrations</h1>
            <Badge variant="outline" className="border-primary/40 text-primary">
              Milestone 90 • v0.75.0
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Embed Retriever directly into Slack workspaces, Chromium browser toolbars, and 2-way Cloud Storage.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="gap-1 font-mono text-xs">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
            HMAC-SHA256 Secured
          </Badge>
          <Badge variant="secondary" className="gap-1 font-mono text-xs">
            <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
            Manifest V3 Ready
          </Badge>
        </div>
      </div>

      {/* Grid of Core Integrations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 1. Slack Workspace Bot Card */}
        <Card className="border-border/60 bg-card overflow-hidden">
          <CardHeader className="border-b border-border/40 pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <MessageSquare className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold">Slack Workspace Bot</CardTitle>
                  <CardDescription className="text-xs">Interactive Block Kit Q&A in any channel</CardDescription>
                </div>
              </div>
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                Active & Live
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="p-5 space-y-4">
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                  Request URL (Slack Slash Command)
                </label>
                <div className="flex items-center gap-2 mt-1">
                  <Input readOnly value={webhookUrl} className="font-mono text-xs bg-muted/30" />
                  <Button size="sm" variant="outline" onClick={handleCopyWebhook} className="shrink-0 gap-1">
                    {copiedWebhook ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                    {copiedWebhook ? "Copied" : "Copy"}
                  </Button>
                </div>
              </div>

              <div>
                <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                  Configured Slash Command
                </label>
                <div className="flex items-center gap-2 mt-1">
                  <Input readOnly value="/ask-retriever" className="font-mono text-xs bg-muted/30 w-48" />
                  <Button size="sm" variant="ghost" onClick={handleCopySlash}>
                    {copiedSlash ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                  </Button>
                </div>
              </div>
            </div>

            {/* Test Simulator */}
            <div className="border border-border/40 rounded-lg p-3 bg-muted/10 space-y-2">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Play className="h-3.5 w-3.5 text-primary" /> Test Slack Slash Simulator
              </span>
              <div className="flex gap-2">
                <Input
                  value={testQuery}
                  onChange={(e) => setTestQuery(e.target.value)}
                  placeholder="Ask a question..."
                  className="text-xs bg-background"
                />
                <Button size="sm" onClick={handleSimulateSlack} disabled={simulating} className="shrink-0 gap-1">
                  {simulating ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                  Run
                </Button>
              </div>

              {simulatedBlockKit && (
                <div className="mt-3 p-3 rounded-md bg-zinc-950 border border-zinc-800 text-xs font-mono space-y-2">
                  <div className="text-zinc-400 font-semibold border-b border-zinc-800 pb-1 flex justify-between">
                    <span>Slack Block Kit Message</span>
                    <span className="text-emerald-400">HTTP 200 OK</span>
                  </div>
                  <p className="text-zinc-200 whitespace-pre-wrap">{simulatedBlockKit.text}</p>
                  <div className="flex items-center gap-2 pt-2 border-t border-zinc-800/80">
                    <span className="px-2 py-0.5 rounded bg-zinc-800 text-[10px] text-zinc-300">👍 Helpful</span>
                    <span className="px-2 py-0.5 rounded bg-zinc-800 text-[10px] text-zinc-300">👎 Inaccurate</span>
                    <span className="px-2 py-0.5 rounded bg-primary/20 text-primary text-[10px]">📄 Open Studio</span>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 2. Chrome Extension Card */}
        <Card className="border-border/60 bg-card overflow-hidden">
          <CardHeader className="border-b border-border/40 pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  <Chrome className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold">1-Click Chrome Ingestion Extension</CardTitle>
                  <CardDescription className="text-xs">Chromium Browser Manifest V3 Extension</CardDescription>
                </div>
              </div>
              <Badge variant="outline" className="bg-cyan-500/10 text-cyan-400 border-cyan-500/30">
                Manifest V3
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="p-5 space-y-4">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Clip full articles, technical documentation, and research PDFs directly from your browser into any client tenant with a single click.
            </p>

            <div className="rounded-lg border border-border/40 bg-muted/20 p-3 space-y-2">
              <span className="text-xs font-semibold text-foreground">3-Step Developer Mode Installation:</span>
              <ol className="text-xs text-muted-foreground list-decimal list-inside space-y-1">
                <li>Click button below to download <code className="font-mono text-primary">retriever-chrome-extension.zip</code>.</li>
                <li>Extract ZIP and open <code className="font-mono">chrome://extensions</code> in Chrome/Brave/Edge.</li>
                <li>Enable <b>Developer Mode</b> (top-right) and click <b>Load unpacked</b>.</li>
              </ol>
            </div>

            <a href={extensionDownloadUrl} download="retriever-chrome-extension.zip" className="block w-full">
              <Button className="w-full gap-2 bg-cyan-500 hover:bg-cyan-400 text-black font-semibold">
                <Download className="h-4 w-4" />
                Download Chrome Extension (.zip)
              </Button>
            </a>
          </CardContent>
        </Card>

        {/* 3. Google Drive 2-Way Sync Card */}
        <Card className="border-border/60 bg-card overflow-hidden">
          <CardHeader className="border-b border-border/40 pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  <FolderSync className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold">Google Drive 2-Way Sync</CardTitle>
                  <CardDescription className="text-xs">Google Drive v3 REST API Folder Ingestion</CardDescription>
                </div>
              </div>
              <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30">
                v3 REST API
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="p-5 space-y-4">
            <div className="space-y-2">
              <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Target Google Drive Folder ID
              </label>
              <Input
                defaultValue="1A2B3C4D5E6F7G8H9I0J"
                className="font-mono text-xs bg-muted/30"
                placeholder="Google Drive Folder ID"
              />
            </div>

            <div className="text-xs text-muted-foreground space-y-1">
              <div className="flex justify-between py-1 border-b border-border/30">
                <span>Auto Google Docs to Markdown:</span>
                <span className="font-semibold text-foreground">Enabled</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/30">
                <span>Differential MD5 Checksums:</span>
                <span className="font-semibold text-foreground">Active</span>
              </div>
              <div className="flex justify-between py-1">
                <span>Last Synced:</span>
                <span className="font-mono text-foreground">Just now</span>
              </div>
            </div>

            <Button
              variant="outline"
              onClick={handleTriggerGdriveSync}
              disabled={gdriveSyncing}
              className="w-full gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${gdriveSyncing ? "animate-spin text-primary" : ""}`} />
              {gdriveSyncing ? "Syncing Google Drive..." : gdriveSuccess ? "✓ Synced 12 Files" : "Sync Now"}
            </Button>
          </CardContent>
        </Card>

        {/* 4. Notion Workspace Connector Card */}
        <Card className="border-border/60 bg-card overflow-hidden">
          <CardHeader className="border-b border-border/40 pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold">Notion Knowledge Base</CardTitle>
                  <CardDescription className="text-xs">Recursive Block-to-Markdown Connector</CardDescription>
                </div>
              </div>
              <Badge variant="outline" className="bg-purple-500/10 text-purple-400 border-purple-500/30">
                v1 API
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="p-5 space-y-4">
            <div className="space-y-2">
              <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Target Notion Database ID
              </label>
              <Input
                defaultValue="db_engineering_wiki_492"
                className="font-mono text-xs bg-muted/30"
                placeholder="Notion Database ID"
              />
            </div>

            <div className="text-xs text-muted-foreground space-y-1">
              <div className="flex justify-between py-1 border-b border-border/30">
                <span>Block Tree Traversal:</span>
                <span className="font-semibold text-foreground">Headings, Lists, Code, Quotes</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/30">
                <span>Differential Re-indexing:</span>
                <span className="font-semibold text-foreground">via last_edited_time</span>
              </div>
              <div className="flex justify-between py-1">
                <span>Last Synced:</span>
                <span className="font-mono text-foreground">4 minutes ago</span>
              </div>
            </div>

            <Button
              variant="outline"
              onClick={handleTriggerNotionSync}
              disabled={notionSyncing}
              className="w-full gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${notionSyncing ? "animate-spin text-primary" : ""}`} />
              {notionSyncing ? "Syncing Notion Database..." : notionSuccess ? "✓ Synced 8 Pages" : "Sync Now"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
