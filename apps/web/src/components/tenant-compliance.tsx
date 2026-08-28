"use client";

import { useState } from "react";
import { useAnonymizeTest, usePurgeTenantData, useRunRetentionPurge } from "@/hooks/use-compliance";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

interface TenantComplianceTabProps {
  tenantId: string;
}

export function TenantComplianceTab({ tenantId }: TenantComplianceTabProps) {
  const [testText, setTestText] = useState("User SSN is 123-45-6789 and contact email is alice@example.com.");
  const [showPurgeConfirm, setShowPurgeConfirm] = useState(false);

  const anonymizeMutation = useAnonymizeTest(tenantId);
  const purgeMutation = usePurgeTenantData(tenantId);
  const retentionMutation = useRunRetentionPurge(tenantId);

  const handleTestAnonymizer = () => {
    if (!testText.trim()) return;
    anonymizeMutation.mutate(testText);
  };

  const handlePurgeTenant = () => {
    purgeMutation.mutate(undefined, {
      onSuccess: () => setShowPurgeConfirm(false),
    });
  };

  return (
    <div className="space-y-6">
      {/* PII Anonymization Testing Card */}
      <Card>
        <CardHeader>
          <CardTitle>Zero-Footprint PII Anonymization Tester</CardTitle>
          <CardDescription>Test inline PII redaction pass-through for SSNs, credit cards, emails, and custom regex tokens.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="pii-sample-text">Sample Input Text</Label>
            <Textarea
              id="pii-sample-text"
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
              rows={3}
              placeholder="Enter text containing sensitive PII..."
            />
          </div>
          <Button onClick={handleTestAnonymizer} disabled={anonymizeMutation.isPending} aria-label="Run PII Anonymizer Test">
            {anonymizeMutation.isPending ? "Testing..." : "Test PII Anonymizer"}
          </Button>

          {anonymizeMutation.data && (
            <div role="region" aria-label="PII redaction output" className="p-4 bg-muted rounded-lg space-y-2 font-mono text-sm">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-muted-foreground uppercase">Anonymized Output</span>
                <Badge variant="secondary">{anonymizeMutation.data.pii_detected_count} PII Tokens Masked</Badge>
              </div>
              <p className="text-emerald-600 dark:text-emerald-400 font-sans font-medium">
                {anonymizeMutation.data.anonymized_text}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Retention SLA Worker Card */}
      <Card>
        <CardHeader>
          <CardTitle>SLA Data Retention Scheduler</CardTitle>
          <CardDescription>Trigger automated retention purge scanning document creation dates against tenant SLAs.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            variant="outline"
            onClick={() => retentionMutation.mutate()}
            disabled={retentionMutation.isPending}
          >
            {retentionMutation.isPending ? "Running Purge..." : "Run SLA Retention Purge Now"}
          </Button>

          {retentionMutation.data && (
            <p className="text-sm font-medium text-emerald-600">
              ✅ SLA Purge Complete: {retentionMutation.data.purged_count} expired documents purged.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Danger Zone: GDPR Hard Purge */}
      <Card className="border-red-500/50 dark:border-red-900/50">
        <CardHeader>
          <CardTitle className="text-red-600 dark:text-red-400">GDPR & SOC 2 Right-to-be-Forgot Hard Purge</CardTitle>
          <CardDescription>
            Permanently erase all documents, chunks, vectors, cache keys, and graph triples belonging to this tenant.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!showPurgeConfirm ? (
            <Button variant="destructive" onClick={() => setShowPurgeConfirm(true)}>
              ⚠️ Trigger GDPR Hard Purge
            </Button>
          ) : (
            <div className="p-4 border border-red-500/40 rounded-lg bg-red-500/10 space-y-3">
              <p className="text-sm font-bold text-red-600 dark:text-red-400">
                Are you absolute sure? This will hard-delete ALL vectors and documents for workspace {tenantId}.
              </p>
              <div className="flex gap-2">
                <Button variant="destructive" onClick={handlePurgeTenant} disabled={purgeMutation.isPending}>
                  {purgeMutation.isPending ? "Purging All Data..." : "Confirm & Execute Purge"}
                </Button>
                <Button variant="outline" onClick={() => setShowPurgeConfirm(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {purgeMutation.data && (
            <div className="p-3 bg-red-500/20 text-red-600 rounded text-sm font-mono">
              Status: {purgeMutation.data.status} | Deleted Docs: {purgeMutation.data.deleted_documents} | Deleted Chunks: {purgeMutation.data.deleted_chunks}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
