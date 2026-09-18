/**
 * Cognitive Tools: Hybrid Search, GraphRAG, and Graph-of-Thought Planning
 */

import { z } from "zod";
import type { RetrieverClient } from "../client.js";

export function registerCognitiveTools(server: any, client: RetrieverClient) {
  // 8. retriever_hybrid_search
  server.tool(
    "retriever_hybrid_search",
    "Perform dense vector + BM25 hybrid search across a tenant's knowledge documents with cited context chunks.",
    {
      tenant_id: z.string().describe("The UUID of the tenant to search within."),
      query: z.string().describe("Natural language search query."),
      top_k: z.number().optional().default(5).describe("Number of context chunks to retrieve (default 5)."),
    },
    async ({
      tenant_id,
      query,
      top_k,
    }: {
      tenant_id: string;
      query: string;
      top_k: number;
    }) => {
      try {
        const results = await client.hybridSearch(tenant_id, query, top_k);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  query,
                  total_results: results.length,
                  results,
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
          content: [{ type: "text", text: `Error executing hybrid search: ${err.message}` }],
        };
      }
    }
  );

  // 9. retriever_got_plan
  server.tool(
    "retriever_got_plan",
    "Execute Battery #38 Graph-of-Thoughts (GoT) planning to generate branching, causal reasoning paths for complex scenarios or story turns.",
    {
      tenant_id: z.string().describe("The UUID of the tenant."),
      prompt: z.string().describe("The decision dilemma or scenario prompt to explore branches for."),
      branching_factor: z.number().optional().default(3).describe("Number of speculative branches to synthesize (default 3)."),
    },
    async ({
      tenant_id,
      prompt,
      branching_factor,
    }: {
      tenant_id: string;
      prompt: string;
      branching_factor: number;
    }) => {
      try {
        const plan = await client.createGotPlan(tenant_id, prompt, branching_factor);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(plan, null, 2),
            },
          ],
        };
      } catch (err: any) {
        return {
          isError: true,
          content: [{ type: "text", text: `Error generating GoT plan: ${err.message}` }],
        };
      }
    }
  );
}
