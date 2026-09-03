"use client";

import { useState } from "react";
import {
  MaskingMode,
  PiiCategory,
  useAnonymizeTest,
  useComplianceCertificates,
  usePurgeTenantData,
  useRunRetentionPurge,
  useVerifyCertificate,
} from "@/hooks/use-compliance";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  Download,
  Key,
  Lock,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

interface TenantComplianceTabProps {
  tenantId: string;
}

const DEFAULT_SAMPLE_TEXT =
  "Patient record: MRN-10293847. Contact Alice at alice@hospital.org. " +
  "Card on file: 4532-0151-1283-0366, SSN: 123-45-6789. " +
  "Production secret: AKIAIOSFODNN7EXAMPLE. Server IP: 192.168.1.100.";

export function TenantComplianceTab({ tenantId }: TenantComplianceTabProps) {
  const [testText, setTestText] = useState(DEFAULT_SAMPLE_TEXT);
  const [maskingMode, setMaskingMode] = useState<MaskingMode>("redact");
  const [selectedCategories, setSelectedCategories] = useState<PiiCategory[]>([
    "financial",
    "identification",
    "secrets",
    "network",
    "health_hipaa",
    "contact",
  ]);
  const [showPurgeConfirm, setShowPurgeConfirm] = useState(false);
  const [activeCertificate, setActiveCertificate] = useState<any | null>(null);

  const anonymizeMutation = useAnonymizeTest(tenantId);
  const purgeMutation = usePurgeTenantData(tenantId);
  const retentionMutation = useRunRetentionPurge(tenantId);
  const { data: certificates, refetch: refetchCertificates } = useComplianceCertificates(tenantId);
  const verifyMutation = useVerifyCertificate();

  const toggleCategory = (cat: PiiCategory) => {
    setSelectedCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const handleTestAnonymizer = () => {
    if (!testText.trim()) return;
    anonymizeMutation.mutate({
      text: testText,
      masking_mode: maskingMode,
      categories: selectedCategories,
    });
  };

  const handlePurgeTenant = () => {
    purgeMutation.mutate(undefined, {
      onSuccess: (data) => {
        setShowPurgeConfirm(false);
        if (data.certificate) {
          setActiveCertificate(data.certificate);
        }
        refetchCertificates();
      },
    });
  };

  const handleDownloadCertificate = (cert: any) => {
    const blob = new Blob([JSON.stringify(cert, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${cert.certificate_id}_audit_certificate.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* ── 1. PII Redaction & Anonymization Engine ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-primary" />
                Enterprise PII Redactor & Zero-Footprint Sanitizer
              </CardTitle>
              <CardDescription>
                Context-aware inline entity scrubbing before vector embedding. Supports Luhn card validation,
                API secrets, HIPAA medical IDs, and deterministic pseudonymization.
              </CardDescription>
            </div>
            <Badge variant="outline" className="font-mono text-xs border-primary/30 text-primary">
              Milestone 88 Active
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Masking Mode Selector */}
          <div className="space-y-2">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Redaction Strategy / Masking Mode
            </Label>
            <div className="flex flex-wrap gap-2">
              {[
                { id: "redact", label: "Redact Tag", desc: "[REDACTED_TYPE]" },
                { id: "synthetic", label: "Synthetic Mask", desc: "****-1234 / ***-6789" },
                { id: "pseudonymize", label: "Cryptographic Pseudonym", desc: "[PSEUDONYM:sha256[:8]]" },
              ].map((mode) => (
                <Button
                  key={mode.id}
                  size="sm"
                  type="button"
                  variant={maskingMode === mode.id ? "default" : "outline"}
                  onClick={() => setMaskingMode(mode.id as MaskingMode)}
                  className="text-xs h-8"
                >
                  {mode.label}
                  <span className="ml-1.5 opacity-60 text-[10px] font-mono">({mode.desc})</span>
                </Button>
              ))}
            </div>
          </div>

          {/* Category Filter Pills */}
          <div className="space-y-2">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Active Protection Domains
            </Label>
            <div className="flex flex-wrap gap-1.5">
              {[
                { id: "financial", label: "Financial (Cards & IBAN)", icon: "💳" },
                { id: "identification", label: "Identity (SSN, Passport, PAN)", icon: "🪪" },
                { id: "secrets", label: "API Keys & Secrets (AKIA, sk-, ghp_)", icon: "🔑" },
                { id: "health_hipaa", label: "Health & Medical (HIPAA MRN)", icon: "🏥" },
                { id: "network", label: "Network (IPv4, MAC)", icon: "🌐" },
                { id: "contact", label: "Contact (Email, Phone)", icon: "✉️" },
              ].map((cat) => {
                const isSelected = selectedCategories.includes(cat.id as PiiCategory);
                return (
                  <Button
                    key={cat.id}
                    size="sm"
                    type="button"
                    variant={isSelected ? "secondary" : "ghost"}
                    onClick={() => toggleCategory(cat.id as PiiCategory)}
                    className={`text-xs h-7 border border-border/40 ${isSelected ? "border-primary/50 text-foreground" : "text-muted-foreground"}`}
                  >
                    <span className="mr-1">{cat.icon}</span>
                    {cat.label}
                  </Button>
                );
              })}
            </div>
          </div>

          {/* Sample Input Textarea */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="pii-sample-text">Live Input Text</Label>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[11px] text-muted-foreground"
                onClick={() => setTestText(DEFAULT_SAMPLE_TEXT)}
              >
                Reset Sample
              </Button>
            </div>
            <Textarea
              id="pii-sample-text"
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
              rows={3}
              placeholder="Enter text containing sensitive PII..."
              className="font-mono text-xs"
            />
          </div>

          <Button
            onClick={handleTestAnonymizer}
            disabled={anonymizeMutation.isPending}
            className="w-full sm:w-auto"
          >
            {anonymizeMutation.isPending ? "Redacting..." : "Execute Zero-Footprint Sanitization"}
          </Button>

          {/* Redaction Output */}
          {anonymizeMutation.data && (
            <div className="p-4 bg-muted/40 border border-border/50 rounded-lg space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-muted-foreground uppercase">
                  Sanitized Output ({anonymizeMutation.data.original_length} chars)
                </span>
                <Badge variant="secondary" className="font-mono text-[11px]">
                  {anonymizeMutation.data.total_redacted} Entities Scrubbed
                </Badge>
              </div>
              <p className="text-foreground bg-background p-3 rounded border border-border/40 font-mono text-xs whitespace-pre-wrap leading-relaxed">
                {anonymizeMutation.data.redacted_text}
              </p>

              {/* Detected Entities Badges */}
              {anonymizeMutation.data.entities_detected.length > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-border/30">
                  <span className="text-[11px] font-semibold text-muted-foreground">Scrubbed Entity Ledger:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {anonymizeMutation.data.entities_detected.map((ent, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-background border border-border/60 text-[10px]"
                      >
                        <span className="font-semibold text-primary uppercase">{ent.entity_type}</span>
                        <span className="text-muted-foreground line-through opacity-75">{ent.original_value}</span>
                        <span className="text-emerald-500 font-bold font-mono">{ent.masked_value}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── 2. SLA Data Retention Worker ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <RefreshCw className="h-5 w-5 text-muted-foreground" />
                Automated SLA Data Retention Scanner
              </CardTitle>
              <CardDescription>
                Enforce contractual data expiration policies. Automatically scans creation dates and hard-purges
                aged documents exceeding tenant retention SLAs.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            variant="outline"
            onClick={() => retentionMutation.mutate()}
            disabled={retentionMutation.isPending}
          >
            {retentionMutation.isPending ? "Scanning & Purging..." : "Run SLA Retention Purge Now"}
          </Button>

          {retentionMutation.data && (
            <div className="p-3 bg-muted/40 rounded border border-border/40 text-xs flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>
                SLA Scan Complete: <strong className="text-foreground">{retentionMutation.data.result.scanned}</strong> documents scanned,{" "}
                <strong className="text-foreground">{retentionMutation.data.result.purged}</strong> expired records purged.
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── 3. GDPR Hard Purge & Signed Certificate Authority ── */}
      <Card className="border-red-500/40 dark:border-red-900/40">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-red-600 dark:text-red-400 flex items-center gap-2">
                <ShieldAlert className="h-5 w-5" />
                GDPR Article 17 Right-to-be-Forgotten & Cryptographic Erasure
              </CardTitle>
              <CardDescription>
                Permanently destroys all documents, chunks, vector records, semantic caches, and graph triples.
                Instantly issues an immutable, HMAC-SHA256 signed Compliance Deletion Certificate for regulatory audits.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {!showPurgeConfirm ? (
            <Button variant="destructive" onClick={() => setShowPurgeConfirm(true)}>
              ⚠️ Trigger GDPR Hard Purge & Issue Erasure Certificate
            </Button>
          ) : (
            <div className="p-4 border border-red-500/40 rounded-lg bg-red-500/10 space-y-3">
              <p className="text-sm font-bold text-red-600 dark:text-red-400">
                Are you absolute sure? This will hard-delete ALL vectors, documents, and memory for workspace {tenantId}.
              </p>
              <div className="flex gap-2">
                <Button variant="destructive" onClick={handlePurgeTenant} disabled={purgeMutation.isPending}>
                  {purgeMutation.isPending ? "Purging & Signing Certificate..." : "Confirm & Sign Erasure Certificate"}
                </Button>
                <Button variant="outline" onClick={() => setShowPurgeConfirm(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Latest Issued Deletion Certificate */}
          {activeCertificate && (
            <div className="p-4 border border-emerald-500/40 rounded-lg bg-emerald-500/10 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-emerald-500" />
                  <span className="font-bold text-xs text-foreground uppercase tracking-wider">
                    GDPR Article 17 Erasure Certificate Issued
                  </span>
                </div>
                <Badge variant="outline" className="border-emerald-500/50 text-emerald-500 font-mono text-[10px]">
                  HMAC-SHA256 Authenticated
                </Badge>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                <div className="p-2 bg-background/80 rounded border border-border/40">
                  <span className="text-[10px] text-muted-foreground block">Certificate ID</span>
                  <strong className="text-foreground">{activeCertificate.certificate_id}</strong>
                </div>
                <div className="p-2 bg-background/80 rounded border border-border/40">
                  <span className="text-[10px] text-muted-foreground block">Scope</span>
                  <strong className="text-foreground">{activeCertificate.erasure_scope}</strong>
                </div>
                <div className="p-2 bg-background/80 rounded border border-border/40">
                  <span className="text-[10px] text-muted-foreground block">Timestamp</span>
                  <strong className="text-foreground">{new Date(activeCertificate.timestamp).toLocaleTimeString()}</strong>
                </div>
                <div className="p-2 bg-background/80 rounded border border-border/40">
                  <span className="text-[10px] text-muted-foreground block">Status</span>
                  <strong className="text-emerald-500">{activeCertificate.verification_status}</strong>
                </div>
              </div>

              <div className="p-2 bg-background/80 rounded border border-border/40 text-[11px] font-mono break-all space-y-1">
                <span className="text-[10px] text-muted-foreground block">Cryptographic SHA-256 Signature:</span>
                <span className="text-foreground font-semibold">{activeCertificate.sha256_audit_signature}</span>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDownloadCertificate(activeCertificate)}
                className="text-xs flex items-center gap-1.5"
              >
                <Download className="h-3.5 w-3.5" />
                Download Compliance Certificate (JSON)
              </Button>
            </div>
          )}

          {/* Historical Deletion Certificates Ledger */}
          {certificates && certificates.length > 0 && (
            <div className="space-y-2 pt-3 border-t border-border/40">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                Auditor Erasure Certificates Ledger
              </span>
              <div className="rounded-md border border-border/40 overflow-hidden">
                <table className="w-full text-xs text-left">
                  <thead className="bg-muted/50 text-muted-foreground font-medium border-b border-border/40">
                    <tr>
                      <th className="p-2.5">Certificate ID</th>
                      <th className="p-2.5">Scope</th>
                      <th className="p-2.5">Requester</th>
                      <th className="p-2.5">SHA-256 Digest</th>
                      <th className="p-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30 font-mono text-[11px]">
                    {certificates.map((cert) => (
                      <tr key={cert.certificate_id} className="hover:bg-muted/20">
                        <td className="p-2.5 font-bold text-foreground">{cert.certificate_id}</td>
                        <td className="p-2.5 uppercase text-muted-foreground">{cert.erasure_scope}</td>
                        <td className="p-2.5 text-muted-foreground">{cert.requester}</td>
                        <td className="p-2.5 text-muted-foreground font-mono text-[10px]">
                          {cert.sha256_audit_signature.slice(0, 16)}...
                        </td>
                        <td className="p-2.5 text-right space-x-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-[10px]"
                            onClick={() => verifyMutation.mutate(cert.certificate_id)}
                          >
                            Verify
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-6 px-2 text-[10px]"
                            onClick={() => handleDownloadCertificate(cert)}
                          >
                            JSON
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Verification Result Banner */}
          {verifyMutation.data && (
            <div
              className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
                verifyMutation.data.is_valid
                  ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-600 dark:text-emerald-400"
                  : "bg-red-500/10 border-red-500/40 text-red-600 dark:text-red-400"
              }`}
            >
              <div className="flex items-center gap-2">
                {verifyMutation.data.is_valid ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                ) : (
                  <Lock className="h-4 w-4 text-red-500" />
                )}
                <span>
                  Certificate <strong>{verifyMutation.data.certificate_id}</strong>: {verifyMutation.data.message}
                </span>
              </div>
              <Badge variant="outline" className="font-mono text-[10px]">
                {verifyMutation.data.is_valid ? "STATUS: VALID" : "STATUS: INVALID"}
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
