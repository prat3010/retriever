/**
 * Ingestion Tools for Indexing Knowledge, Rules, and Story Lore
 */

import { z } from "zod";
import type { RetrieverClient } from "../client.js";

export function registerIngestionTools(server: any, client: RetrieverClient) {
  // 5. retriever_ingest_text
  server.tool(
    "retriever_ingest_text",
    "Ingest raw text/markdown snippet into the tenant's vector database and GraphRAG knowledge base.",
    {
      tenant_id: z.string().describe("The UUID of the tenant to ingest into."),
      filename: z.string().describe("Logical filename (e.g. 'primordial_ecology.md', 'character_kaelen.md')."),
      content: z.string().describe("The raw text or markdown body to chunk and index."),
      tags: z.array(z.string()).optional().default([]).describe("Optional metadata tags for chronological or domain filtering."),
    },
    async ({
      tenant_id,
      filename,
      content,
      tags,
    }: {
      tenant_id: string;
      filename: string;
      content: string;
      tags: string[];
    }) => {
      try {
        const result = await client.ingestText(tenant_id, filename, content, tags);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  success: true,
                  message: `Content successfully uploaded and queued for vector embedding.`,
                  result,
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
          content: [{ type: "text", text: `Error ingesting text: ${err.message}` }],
        };
      }
    }
  );

  // 6. retriever_upload_file
  server.tool(
    "retriever_upload_file",
    "Upload a local file (Markdown, PDF, TXT) from the filesystem into the tenant's vector knowledge base.",
    {
      tenant_id: z.string().describe("The UUID of the tenant to upload into."),
      file_path: z.string().describe("Absolute or relative path to the local file."),
    },
    async ({ tenant_id, file_path }: { tenant_id: string; file_path: string }) => {
      try {
        const result = await client.uploadFile(tenant_id, file_path);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  success: true,
                  message: `File '${file_path}' successfully uploaded and queued for vector embedding.`,
                  result,
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
          content: [{ type: "text", text: `Error uploading file: ${err.message}` }],
        };
      }
    }
  );

  // 7. retriever_list_documents
  server.tool(
    "retriever_list_documents",
    "List all indexed documents, chunk counts, and ingestion statuses for a tenant.",
    {
      tenant_id: z.string().describe("The UUID of the tenant."),
      limit: z.number().optional().default(50).describe("Maximum documents to return."),
    },
    async ({ tenant_id, limit }: { tenant_id: string; limit: number }) => {
      try {
        const docs = await client.listDocuments(tenant_id, limit);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(docs, null, 2),
            },
          ],
        };
      } catch (err: any) {
        return {
          isError: true,
          content: [{ type: "text", text: `Error listing documents: ${err.message}` }],
        };
      }
    }
  );
}
