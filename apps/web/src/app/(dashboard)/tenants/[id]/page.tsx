"use client";

import { useTenant } from "@/hooks/use-tenants";
import { useParams } from "next/navigation";
import { Topbar } from "@/components/topbar";
import Link from "next/link";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { OverviewTab } from "@/components/tenant-overview";
import { UsersTab } from "@/components/tenant-users";
import { ApiKeysTab } from "@/components/tenant-api-keys";
import { ConfigTab } from "@/components/tenant-config";
import { TenantDocumentsTab } from "@/components/tenant-documents";
import { TenantPromptsTab } from "@/components/tenant-prompts";
import { TenantSandboxTab } from "@/components/tenant-sandbox";

export default function TenantDetailPage() {
  const params = useParams();
  const tenantId = params.id as string;
  const { data: tenant, isLoading } = useTenant(tenantId);

  if (isLoading) {
    return (
      <div>
        <Topbar title="Loading..." />
        <div className="p-6 space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  if (!tenant) {
    return (
      <div>
        <Topbar title="Tenant not found" />
        <div className="p-6 text-muted-foreground">
          The requested tenant does not exist.
        </div>
      </div>
    );
  }

  return (
    <div>
      <Topbar title={tenant.name} description={`Tenant ID: ${tenant.tenantId}`} />
      <div className="p-6">
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="users">Users</TabsTrigger>
            <TabsTrigger value="api-keys">API Keys</TabsTrigger>
            <TabsTrigger value="prompts">Prompts</TabsTrigger>
            <TabsTrigger value="sandbox">Sandbox</TabsTrigger>
            <TabsTrigger value="config">Config</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewTab tenant={tenant} tenantId={tenantId} />
          </TabsContent>

          <TabsContent value="users">
            <UsersTab tenantId={tenantId} />
          </TabsContent>

          <TabsContent value="api-keys">
            <ApiKeysTab tenantId={tenantId} />
          </TabsContent>

          <TabsContent value="documents">
            <TenantDocumentsTab tenantId={tenantId} />
          </TabsContent>
          <TabsContent value="prompts">
            <TenantPromptsTab tenantId={tenantId} />
          </TabsContent>
          <TabsContent value="sandbox">
            <TenantSandboxTab tenantId={tenantId} />
          </TabsContent>
          <TabsContent value="config">
            <ConfigTab tenantId={tenantId} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
