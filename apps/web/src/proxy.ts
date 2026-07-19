import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function proxy(request: NextRequest) {
  const adminKey = request.cookies.get("admin_key")?.value
    ?? request.headers.get("x-admin-key")
    ?? "";

  if (
    !request.nextUrl.pathname.startsWith("/login")
    && !request.nextUrl.pathname.startsWith("/_next")
    && !request.nextUrl.pathname.startsWith("/api")
  ) {
    if (!adminKey) {
      return NextResponse.redirect(new URL("/login", request.url));
    }

    if (!request.cookies.has("admin_key_validated")) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        const res = await fetch(`${API_BASE}/v1/admin/verify-key`, {
          headers: { "X-Admin-Master-Key": adminKey },
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (!res.ok) {
          const response = NextResponse.redirect(new URL("/login", request.url));
          response.cookies.delete("admin_key");
          response.cookies.delete("admin_key_validated");
          return response;
        }
        const validated = NextResponse.next();
        validated.cookies.set("admin_key_validated", "1", {
          path: "/",
          maxAge: 300,
          httpOnly: true,
          sameSite: "lax",
        });
        return validated;
      } catch {
        return NextResponse.next();
      }
    }
  }

  return NextResponse.next();
}
