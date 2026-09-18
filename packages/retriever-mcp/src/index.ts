#!/usr/bin/env node

/**
 * Retriever Model Context Protocol (MCP) Server
 * Exposes tenant provisioning, document ingestion, hybrid search, and GoT reasoning
 * to AI coding assistants and autonomous agents.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import dotenv from "dotenv";
import { RetrieverClient } from "./client.js";
import { registerAdminTools } from "./tools/admin.js";
import { registerCognitiveTools } from "./tools/cognitive.js";
import { registerIngestionTools } from "./tools/ingestion.js";

dotenv.config();

const server = new McpServer({
  name: "retriever-mcp",
  version: "0.1.0",
});

const client = new RetrieverClient({
  baseUrl: process.env.RETRIEVER_API_URL || "https://rag.prateeq.in",
  adminMasterKey: process.env.RETRIEVER_ADMIN_MASTER_KEY,
  defaultTenantId: process.env.RETRIEVER_TENANT_ID,
  apiKey: process.env.RETRIEVER_API_KEY,
});

// Register tool suites
registerAdminTools(server, client);
registerIngestionTools(server, client);
registerCognitiveTools(server, client);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(
    `[Retriever MCP] Server active on stdio, connected to ${process.env.RETRIEVER_API_URL || "https://rag.prateeq.in"}`
  );
}

main().catch((err) => {
  console.error("[Retriever MCP] Fatal error:", err);
  process.exit(1);
});
