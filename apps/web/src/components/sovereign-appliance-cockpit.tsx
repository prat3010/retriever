"use client";

import { useState } from "react";
import {
  useApplianceStatus,
  useAuditNetwork,
  useSealVectorStore,
  useUnsealVectorStore,
  useVoiceRAGQuery,
} from "@/hooks/use-appliance";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  Unlock,
  Mic,
  Cpu,
  HardDrive,
  RefreshCw,
  Activity,
  Layers,
  Terminal,
  Volume2,
} from "lucide-react";

interface SovereignApplianceCockpitProps {
  tenantId: string;
}

export function SovereignApplianceCockpit({ tenantId }: SovereignApplianceCockpitProps) {
  const { data: status, isLoading, refetch } = useApplianceStatus();
  const auditMutation = useAuditNetwork();
  const sealMutation = useSealVectorStore(tenantId);
  const unsealMutation = useUnsealVectorStore(tenantId);
  const voiceMutation = useVoiceRAGQuery(tenantId);

  const [plainDbPath, setPlainDbPath] = useState("/appliance/data/tenant_vectors.db");
  const [sealedDbPath, setSealedDbPath] = useState("/appliance/data/sealed/tenant_vectors.db.sealed");
  const [restoredDbPath, setRestoredDbPath] = useState("/appliance/data/unsealed_vectors.db");
  const [voiceQueryText, setVoiceQueryText] = useState("Status check on sovereign tactical network");

  const isCompliant = status?.network_state === "isolated_compliant";
  const isSealed = status?.sealing_state === "sealed";

  const handleSimulateVoiceQuery = () => {
    // Generate a synthetic 16-bit PCM waveform sample (320 samples @ 16kHz)
    const buffer = new ArrayBuffer(640);
    const view = new DataView(buffer);
    for (let i = 0; i < 320; i++) {
      const sample = (i % 2 === 0 ? 1 : -1) * 12000;
      view.setInt16(i * 2, sample, true);
    }
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const base64Audio = btoa(binary);

    voiceMutation.mutate({
      tenant_id: tenantId,
      audio_bytes_base64: base64Audio,
      sample_rate_hz: 16000,
      top_k: 3,
      timbre: "neural_natural",
    });
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Air-Gap Security Shield */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl border bg-card/60 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <div
            className={`p-3 rounded-xl border ${
              isCompliant
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-amber-500/10 border-amber-500/30 text-amber-400"
            }`}
          >
            {isCompliant ? <ShieldCheck className="h-7 w-7" /> : <ShieldAlert className="h-7 w-7" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold tracking-tight">Sovereign Air-Gapped Appliance</h2>
              <Badge variant={isCompliant ? "default" : "destructive"}>
                {status?.deployment_mode?.toUpperCase() || "AIR_GAPPED_STRICT"}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">
              Zero-Egress Strict Mode: {isCompliant ? "Active & Compliant" : "Audit Pending / Non-compliant"} •
              Hardware Vector Sealing: {status?.sealing_state?.toUpperCase() || "UNSEALED"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => auditMutation.mutate({ strict_enforce: false })}
            disabled={auditMutation.isPending}
          >
            <Activity className={`h-4 w-4 mr-1.5 ${auditMutation.isPending ? "animate-spin" : ""}`} />
            Audit Isolation
          </Button>
          <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Grid: Attestation, Storage & Sealing */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Hardware Root Attestation Card */}
        <Card className="border-border/60">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="h-5 w-5 text-cyan-400" />
                <CardTitle className="text-base">Hardware Root of Trust</CardTitle>
              </div>
              <Badge variant="outline" className="font-mono text-xs">
                {status?.hardware_attestation?.hardware_root || "TPM 2.0 PCR0"}
              </Badge>
            </div>
            <CardDescription>Silicon-bound cryptographic PCR measurement and hardware key</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-xs font-mono">
            <div>
              <Label className="text-xs text-muted-foreground">Host Silicon Platform</Label>
              <div className="mt-1 p-2 rounded bg-muted/40 border truncate">
                {status?.hardware_attestation?.platform || "darwin-arm64-apple-silicon"}
              </div>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">PCR Measurement Digest (SHA-256)</Label>
              <div className="mt-1 p-2 rounded bg-muted/40 border truncate text-cyan-300">
                {status?.hardware_attestation?.pcr_measurement || "pcr0:00000000000000000000000000000000"}
              </div>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Attestation Signature</Label>
              <div className="mt-1 p-2 rounded bg-muted/40 border truncate text-muted-foreground">
                {status?.hardware_attestation?.signature || "sig_valid_hardware_quote"}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Hardware Vector Sealer & SQLite Storage Card */}
        <Card className="border-border/60">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HardDrive className="h-5 w-5 text-indigo-400" />
                <CardTitle className="text-base">Embedded Vector Sealing</CardTitle>
              </div>
              <Badge variant={isSealed ? "default" : "secondary"}>
                {isSealed ? <Lock className="h-3 w-3 mr-1 inline" /> : <Unlock className="h-3 w-3 mr-1 inline" />}
                {isSealed ? "AES-256-GCM SEALED" : "UNSEALED"}
              </Badge>
            </div>
            <CardDescription>At-rest vector encryption bound to host hardware root</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <Label className="text-xs">Plaintext SQLite Path</Label>
              <Input
                className="h-8 font-mono text-xs"
                value={plainDbPath}
                onChange={(e) => setPlainDbPath(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Sealed Ciphertext Path</Label>
              <Input
                className="h-8 font-mono text-xs"
                value={sealedDbPath}
                onChange={(e) => setSealedDbPath(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2 pt-2">
              <Button
                size="sm"
                className="w-1/2"
                onClick={() =>
                  sealMutation.mutate({
                    plain_db_path: plainDbPath,
                    sealed_db_path: sealedDbPath,
                    chunk_count: 120,
                  })
                }
                disabled={sealMutation.isPending}
              >
                <Lock className="h-3.5 w-3.5 mr-1.5" />
                Seal Database
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-1/2"
                onClick={() =>
                  unsealMutation.mutate({
                    sealed_db_path: sealedDbPath,
                    unsealed_db_path: restoredDbPath,
                  })
                }
                disabled={unsealMutation.isPending}
              >
                <Unlock className="h-3.5 w-3.5 mr-1.5" />
                Unseal Database
              </Button>
            </div>
            {sealMutation.isSuccess && (
              <p className="text-xs text-emerald-400 mt-2">✓ Vector store sealed with AES-256-GCM.</p>
            )}
            {unsealMutation.isSuccess && (
              <p className="text-xs text-emerald-400 mt-2">✓ Vector store unsealed with hardware verification.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Offline Full-Duplex Neural Voice RAG Simulator */}
      <Card className="border-border/60">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Mic className="h-5 w-5 text-emerald-400" />
              <CardTitle className="text-base">Offline Full-Duplex Neural Voice RAG</CardTitle>
            </div>
            <Badge variant="outline" className="text-xs">
              Whisper ASR + SQLite Search + Piper TTS
            </Badge>
          </div>
          <CardDescription>
            Tactical edge voice interface operating with zero external cloud API connections
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <Input
              value={voiceQueryText}
              onChange={(e) => setVoiceQueryText(e.target.value)}
              placeholder="Spoken tactical inquiry..."
              className="font-mono text-sm"
            />
            <Button
              onClick={handleSimulateVoiceQuery}
              disabled={voiceMutation.isPending}
              className="min-w-[140px]"
            >
              <Mic className={`h-4 w-4 mr-2 ${voiceMutation.isPending ? "animate-pulse text-red-400" : ""}`} />
              {voiceMutation.isPending ? "Processing..." : "Speak Query"}
            </Button>
          </div>

          {voiceMutation.isSuccess && (
            <div className="mt-4 p-4 rounded-xl border bg-muted/30 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Voice Interaction Session: {voiceMutation.data.session_id}
                </span>
                <span className="text-xs font-mono text-emerald-400">
                  Total Latency: {voiceMutation.data.total_latency_ms.toFixed(1)}ms
                </span>
              </div>

              <div>
                <Label className="text-xs text-muted-foreground">Transcribed Audio (Whisper ASR)</Label>
                <p className="text-sm font-medium mt-0.5">&ldquo;{voiceMutation.data.transcribed_text}&rdquo;</p>
              </div>

              <div>
                <Label className="text-xs text-muted-foreground">Grounded Tactical Answer</Label>
                <p className="text-sm mt-0.5 text-foreground/90">{voiceMutation.data.answer_text}</p>
              </div>

              {voiceMutation.data.citations.length > 0 && (
                <div>
                  <Label className="text-xs text-muted-foreground">Local Grounding Citations</Label>
                  <div className="mt-1 space-y-1">
                    {voiceMutation.data.citations.map((c, i) => (
                      <div key={i} className="text-xs font-mono p-1.5 rounded bg-background/50 border truncate">
                        [{c.document_id || "local_corpus"}] {c.content}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Latency Waterfall */}
              <div className="pt-2 border-t flex flex-wrap gap-4 text-xs font-mono text-muted-foreground">
                <span>ASR: {voiceMutation.data.asr_latency_ms.toFixed(1)}ms</span>
                <span>•</span>
                <span>Retrieval: {voiceMutation.data.retrieval_latency_ms.toFixed(1)}ms</span>
                <span>•</span>
                <span>Synthesis: {voiceMutation.data.synthesis_latency_ms.toFixed(1)}ms</span>
                <span>•</span>
                <span>TTS: {voiceMutation.data.tts_latency_ms.toFixed(1)}ms</span>
                <span>•</span>
                <span className="text-cyan-400 flex items-center gap-1">
                  <Volume2 className="h-3.5 w-3.5" /> Audio: {voiceMutation.data.audio_duration_ms.toFixed(0)}ms PCM16
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pre-baked Embedded Models Inventory */}
      <Card className="border-border/60">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-amber-400" />
            <CardTitle className="text-base">Pre-Baked Sovereign Model Inventory</CardTitle>
          </div>
          <CardDescription>Local offline model weights pre-loaded into container volume</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="pb-2">Model Name</th>
                  <th className="pb-2">Domain Role</th>
                  <th className="pb-2">Quantization</th>
                  <th className="pb-2">Size</th>
                  <th className="pb-2">Integrity SHA-256</th>
                  <th className="pb-2 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {(status?.embedded_models || []).map((m, idx) => (
                  <tr key={idx} className="hover:bg-muted/20">
                    <td className="py-2.5 font-semibold text-foreground">{m.model_name}</td>
                    <td className="py-2.5 text-muted-foreground">{m.model_type}</td>
                    <td className="py-2.5">{m.quantization}</td>
                    <td className="py-2.5">{(m.file_size_bytes / 1024 / 1024).toFixed(0)} MB</td>
                    <td className="py-2.5 text-muted-foreground truncate max-w-[120px]">{m.sha256_checksum.slice(0, 16)}...</td>
                    <td className="py-2.5 text-right">
                      <Badge variant="outline" className="text-emerald-400 border-emerald-500/30 text-[10px]">
                        ONLINE
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
