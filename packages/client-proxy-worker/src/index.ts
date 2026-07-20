export interface Env {
  // Configured in wrangler.toml
  RETRIEVER_API_URL: string;
  // Uploaded via `wrangler secret put RETRIEVER_API_KEY`
  RETRIEVER_API_KEY: string;
}

export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext
  ): Promise<Response> {
    // 1. Handle CORS preflight requests
    if (request.method === "OPTIONS") {
      return handleCorsPreflight();
    }

    try {
      const url = new URL(request.url);
      const path = url.pathname;

      // 2. Parse and authenticate client JWT
      const authHeader = request.headers.get("Authorization");
      if (!authHeader || !authHeader.startsWith("Bearer ")) {
        return errorResponse("Unauthorized: Missing or malformed Bearer Token", 401);
      }

      const token = authHeader.substring(7);
      const payload = parseJwtPayload(token);

      if (!payload) {
        return errorResponse("Unauthorized: Invalid JWT token structure", 401);
      }

      // Check token expiration (if exp claim exists)
      if (payload.exp && Date.now() >= payload.exp * 1000) {
        return errorResponse("Unauthorized: Token has expired", 401);
      }

      // Extract User ID from the token (standard 'sub' claim)
      const userId = payload.sub;
      if (!userId) {
        return errorResponse("Unauthorized: JWT token is missing 'sub' claim", 401);
      }

      // 3. Match and Route API calls
      // Map incoming proxy requests to the underlying Retriever tenant API
      let targetPath = "";
      
      // We match paths:
      // - /chat/sessions -> POST /v1/tenants/{tenantId}/chat/sessions
      // - /chat/sessions/:id/messages -> POST /v1/tenants/{tenantId}/chat/sessions/:id/messages
      // - /search -> POST /v1/tenants/{tenantId}/search
      // - /documents -> GET /v1/tenants/{tenantId}/documents

      // Note: You must bind your specific Tenant ID as a header or configuration.
      // Alternatively, you can embed the tenantId in the JWT if routing dynamically.
      const tenantId = payload.tenant_id;
      if (!tenantId) {
        return errorResponse("Bad Request: JWT token is missing 'tenant_id' claim", 400);
      }

      if (path === "/chat/sessions") {
        targetPath = `/v1/tenants/${tenantId}/chat/sessions`;
      } else if (path.startsWith("/chat/sessions/") && path.endsWith("/messages")) {
        const sessionId = path.split("/")[3];
        targetPath = `/v1/tenants/${tenantId}/chat/sessions/${sessionId}/messages`;
      } else if (path === "/search") {
        targetPath = `/v1/tenants/${tenantId}/search`;
      } else if (path === "/documents") {
        targetPath = `/v1/tenants/${tenantId}/documents`;
      } else {
        return errorResponse("Not Found: Endpoint not supported by proxy gateway", 404);
      }

      const targetUrl = `${env.RETRIEVER_API_URL}${targetPath}`;

      // 4. Construct Request Headers with Secrets Injected
      const newHeaders = new Headers();
      
      // Copy over essential headers
      const contentType = request.headers.get("content-type");
      if (contentType) newHeaders.set("content-type", contentType);

      const accept = request.headers.get("accept");
      if (accept) newHeaders.set("accept", accept);

      // Securely inject tenant authorization keys
      newHeaders.set("Authorization", `Bearer ${env.RETRIEVER_API_KEY}`);
      newHeaders.set("X-User-ID", userId);

      // 5. Proxy the request to the Retriever backend
      // Cloudflare Workers natively supports streaming both request and response bodies.
      const apiResponse = await fetch(targetUrl, {
        method: request.method,
        headers: newHeaders,
        body: request.body, // streams request payload (e.g. prompt)
      });

      // 6. Return response to client with proper CORS headers attached
      const responseHeaders = new Headers(apiResponse.headers);
      setCorsHeaders(responseHeaders);

      return new Response(apiResponse.body, {
        status: apiResponse.status,
        statusText: apiResponse.statusText,
        headers: responseHeaders,
      });

    } catch (err: any) {
      return errorResponse(`Internal Server Error: ${err.message}`, 500);
    }
  },
};

/**
 * Parses the base64url encoded payload of a JWT.
 * Note: For production use, you should verify the JWT signature using the Web Crypto API
 * matching your identity provider (e.g., Firebase, Supabase, or Auth0 JWKS public keys).
 */
function parseJwtPayload(token: string): any {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function handleCorsPreflight(): Response {
  const headers = new Headers();
  setCorsHeaders(headers);
  headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With");
  headers.set("Access-Control-Max-Age", "86400"); // 24 hours caching

  return new Response(null, {
    status: 204,
    headers,
  });
}

function setCorsHeaders(headers: Headers): void {
  headers.set("Access-Control-Allow-Origin", "*");
  headers.set("Access-Control-Allow-Credentials", "true");
}

function errorResponse(message: string, status: number): Response {
  const headers = new Headers({
    "Content-Type": "application/json",
  });
  setCorsHeaders(headers);
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers,
  });
}
