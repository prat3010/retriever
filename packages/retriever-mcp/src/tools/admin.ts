/**
 * Admin Tools for Tenant Provisioning and Key Management
 */

import { z } from "zod";
import type { RetrieverClient } from "../client.js";

export function registerAdminTools(server: any, client: RetrieverClient) {
  // 1. retriever_create_tenant
  server.tool(
    "retriever_create_tenant",
    "Provision a brand-new customer workspace / story world tenant on the Retriever engine.",
    {
      name: z.string().describe("Unique name for the workspace (e.g. 'genesis-chronicles', 'acme-corp')."),
      tier: z.enum(["standard", "premium", "enterprise"]).default("standard").describe("Tenant tier (defaults to 'standard')."),
    },
    async ({ name, tier }: { name: string; tier: string }) => {
      try {
        const tenant = await client.createTenant(name, tier);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  success: true,
                  message: `Tenant '${name}' successfully provisioned.`,
                  tenant,
                },
                null,
                2
              ),
            },
          ],
        };
      } catch (err: any) {
        return {
          isError: true,
          content: [{ type: "text", text: `Error provisioning tenant: ${err.message}` }],
        };
      }
    }
  );

  // 2. retriever_list_tenants
  server.tool(
    "retriever_list_tenants",
    "List registered customer workspaces/tenants with their creation dates, tiers, and statuses.",
    {
      limit: z.number().optional().default(50).describe("Maximum number of tenants to return (default 50)."),
      search: z.string().optional().describe("Optional search term to filter tenants by name."),
    },
    async ({ limit, search }: { limit: number; search?: string }) => {
      try {
        const result = await client.listTenants(limit, search);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (err: any) {
        return {
          isError: true,
          content: [{ type: "text", text: `Error listing tenants: ${err.message}` }],
        };
      }
    }
  );

  // 3. retriever_inspect_tenant
  server.tool(
    "retriever_inspect_tenant",
    "Inspect details, tier, and status of a specific tenant by tenantId.",
    {
      tenant_id: z.string().describe("The UUID of the tenant to inspect."),
    },
    async ({ tenant_id }: { tenant_id: string }) => {
      try {
        const tenant = await client.getTenant(tenant_id);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(tenant, null, 2),
            },
          ],
        };
      } catch (err: any) {
        return {
          isError: true,
          content: [{ type: "text", text: `Error inspecting tenant: ${err.message}` }],
        };
      }
    }
  );

  // 4. retriever_issue_api_key
  server.tool(
    "retriever_issue_api_key",
    "Generate a new scoped API key for a tenant to access chat, search, and document APIs.",
    {
      tenant_id: z.string().describe("The UUID of the tenant to issue the key for."),
      name: z.string().describe("Label for the key (e.g. 'Genesis Story Engine Key')."),
      role: z.enum(["client", "admin"]).default("client").describe("Key role (default 'client')."),
    },
    async ({ tenant_id, name, role }: { tenant_id: string; name: string; role: "client" | "admin" }) => {
      try {
        const keyInfo = await client.issueApiKey(tenant_id, name, role);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  success: true,
                  message: `API Key successfully issued. Store this key securely; it will not be displayed again.`,
                  key: keyInfo,
                },
                null,
                2
              ),
            },
          ],
        };
      } catch (err: any) {
        return {
          isError: true,
          content: [{ type: "text", text: `Error issuing API key: ${err.message}` }],
        };
      }
    }
  );

  // 4b. retriever_system_health
  server.tool(
    "retriever_system_health",
    "Inspect health, readiness, active embedding models, and platform connectivity of the Retriever engine.",
    {},
    async () => {
      try {
        const health = await client.getSystemHealth();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(health, null, 2),
            },
          ],
        };
      } catch (err: any) {
        return {
          isError: true,
          content: [{ type: "text", text: `Error checking system health: ${err.message}` }],
        };
      }
    }
  );
}
