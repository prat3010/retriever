"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Topbar } from "@/components/topbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useCreateTenant } from "@/hooks/use-tenants";
import { useCreateApiKey } from "@/hooks/use-api-keys";
import { API_BASE } from "@/lib/api";
import { useCreateUser } from "@/hooks/use-users";
import { toast } from "sonner";
import { CheckCircle, Copy, ArrowLeft, Loader2 } from "lucide-react";

type Step = "tenant" | "key" | "user" | "done";

export default function OnboardPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("tenant");
  const [createdTenantId, setCreatedTenantId] = useState<string | null>(null);
  const [createdApiKey, setCreatedApiKey] = useState<string | null>(null);
  const [createdUserId, setCreatedUserId] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  const createTenant = useCreateTenant();
  const createApiKey = useCreateApiKey(createdTenantId ?? "");
  const createUser = useCreateUser(createdTenantId ?? "");

  const [tenantForm, setTenantForm] = useState({ name: "", tier: "standard", isolation_level: "logical" });
  const [keyForm, setKeyForm] = useState<{ name: string; role: "admin" | "client"; expires_in_days: number }>({ name: "Default Client Key", role: "client", expires_in_days: 365 });
  const [userForm, setUserForm] = useState({ display_name: "", external_id: "" });

  async function handleCreateTenant() {
    const res = await createTenant.mutateAsync(tenantForm);
    setCreatedTenantId(res.tenantId);
    setUserForm({ display_name: tenantForm.name, external_id: `${tenantForm.name.toLowerCase().replace(/\s+/g, ".")}@client.local` });
    setStep("key");
  }

  async function handleCreateKey() {
    if (!createdTenantId) return;
    try {
      const res = await createApiKey.mutateAsync(keyForm);
      setCreatedApiKey(res.apiKey);
      setStep("user");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create key";
      toast.error(msg);
    }
  }

  async function handleCreateUser() {
    if (!createdTenantId) return;
    try {
      const res = await createUser.mutateAsync({
        external_id: userForm.external_id || `${createdTenantId.slice(0, 8)}@client.local`,
        display_name: userForm.display_name || undefined,
      });
      setCreatedUserId(res.userId);
      setStep("done");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create user";
      toast.error(msg);
    }
  }

  function copyKey() {
    if (createdApiKey) {
      navigator.clipboard.writeText(createdApiKey);
      setCopiedKey(true);
      toast.success("API key copied");
    }
  }

  return (
    <div>
      <Topbar title="Onboard Client" description="Create a new tenant and generate credentials" />
      <div className="p-6 max-w-2xl mx-auto space-y-6">
        {/* Steps indicator */}
        <div className="flex items-center gap-2 text-sm">
          <span className={step === "tenant" ? "font-semibold text-primary" : "text-muted-foreground"}>
            1. Tenant
          </span>
          <span className="text-muted-foreground">→</span>
          <span className={step === "key" ? "font-semibold text-primary" : "text-muted-foreground"}>
            2. API Key
          </span>
          <span className="text-muted-foreground">→</span>
          <span className={step === "user" ? "font-semibold text-primary" : "text-muted-foreground"}>
            3. User
          </span>
          <span className="text-muted-foreground">→</span>
          <span className={step === "done" ? "font-semibold text-primary" : "text-muted-foreground"}>
            4. Credentials
          </span>
        </div>

        {step === "tenant" && (
          <Card>
            <CardHeader>
              <CardTitle>Tenant Details</CardTitle>
              <CardDescription>Create a new workspace for your client</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Tenant Name</Label>
                <Input
                  id="name"
                  placeholder="Acme Corp"
                  value={tenantForm.name}
                  onChange={(e) => setTenantForm({ ...tenantForm, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tier">Tier</Label>
                <Select
                  value={tenantForm.tier}
                  onValueChange={(v) => setTenantForm({ ...tenantForm, tier: v })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">Standard</SelectItem>
                    <SelectItem value="premium">Premium</SelectItem>
                    <SelectItem value="enterprise">Enterprise</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="isolation">Isolation Level</Label>
                <Select
                  value={tenantForm.isolation_level}
                  onValueChange={(v) => setTenantForm({ ...tenantForm, isolation_level: v })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="logical">Logical</SelectItem>
                    <SelectItem value="schema">Schema</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button
                className="w-full"
                onClick={handleCreateTenant}
                disabled={!tenantForm.name.trim() || createTenant.isPending}
              >
                {createTenant.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Tenant
              </Button>
            </CardContent>
          </Card>
        )}

        {step === "key" && (
          <Card>
            <CardHeader>
              <CardTitle>Generate API Key</CardTitle>
              <CardDescription>Create an API key for your new tenant</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="keyname">Key Name</Label>
                <Input
                  id="keyname"
                  value={keyForm.name}
                  onChange={(e) => setKeyForm({ ...keyForm, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Select
                  value={keyForm.role}
                  onValueChange={(v) => setKeyForm({ ...keyForm, role: v as "admin" | "client" })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="client">Client</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setStep("tenant")}>
                  <ArrowLeft className="mr-2 h-4 w-4" /> Back
                </Button>
                <Button className="flex-1" onClick={handleCreateKey} disabled={createApiKey.isPending}>
                  {createApiKey.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Generate Key
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {step === "user" && (
          <Card>
            <CardHeader>
              <CardTitle>Create User</CardTitle>
              <CardDescription>Create an initial user for the new tenant</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="displayName">Display Name</Label>
                <Input
                  id="displayName"
                  value={userForm.display_name}
                  onChange={(e) => setUserForm({ ...userForm, display_name: e.target.value })}
                  placeholder={tenantForm.name}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="externalId">External ID</Label>
                <Input
                  id="externalId"
                  value={userForm.external_id}
                  onChange={(e) => setUserForm({ ...userForm, external_id: e.target.value })}
                  placeholder="user@example.com"
                />
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setStep("key")}>
                  <ArrowLeft className="mr-2 h-4 w-4" /> Back
                </Button>
                <Button className="flex-1" onClick={handleCreateUser} disabled={createUser.isPending}>
                  {createUser.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Create User
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {step === "done" && (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <CardTitle>Client Onboarded</CardTitle>
              </div>
              <CardDescription>Share these credentials with your client</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg border bg-muted/50 p-4 space-y-3 font-mono text-sm">
                <div>
                  <span className="text-muted-foreground">API URL: </span>
                  <span className="font-semibold">{API_BASE}/v1</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Tenant ID: </span>
                  <span className="font-semibold">{createdTenantId}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">User ID: </span>
                  <span className="font-semibold">{createdUserId}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-muted-foreground">API Key: </span>
                    <span className="font-semibold">{createdApiKey?.slice(0, 20)}...</span>
                  </div>
                  <Button size="sm" variant="outline" onClick={copyKey}>
                    <Copy className="mr-1 h-3 w-3" />
                    {copiedKey ? "Copied" : "Copy"}
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Quick-start: curl</Label>
                <pre className="rounded-lg bg-muted p-3 text-xs overflow-x-auto">
{`curl ${API_BASE}/v1/tenants/${createdTenantId}/documents \\
  -H "Authorization: Bearer ${createdApiKey?.slice(0, 20)}..." \\
  -H "X-User-ID: ${createdUserId}"

curl ${API_BASE}/v1/tenants/${createdTenantId}/search \\
  -X POST \\
  -H "Authorization: Bearer ${createdApiKey?.slice(0, 20)}..." \\
  -H "X-User-ID: ${createdUserId}" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "hello world", "limit": 5}'`}
                </pre>
              </div>

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => router.push(`/tenants/${createdTenantId}`)}>
                  View Tenant
                </Button>
                <Button variant="outline" onClick={() => { setStep("tenant"); setTenantForm({ name: "", tier: "standard", isolation_level: "logical" }); setCreatedTenantId(null); setCreatedApiKey(null); setCreatedUserId(null); setCopiedKey(false); }}>
                  Onboard Another
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
