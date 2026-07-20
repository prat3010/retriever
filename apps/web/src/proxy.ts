import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL
  || process.env.API_URL
  || "http://localhost:8000";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/_next") || pathname.startsWith("/api")) {
    return NextResponse.next();
  }

  if (pathname === "/login") {
    return NextResponse.next();
  }

  const adminKey = request.cookies.get("admin_key")?.value;

  if (!adminKey) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (request.cookies.has("admin_key_validated")) {
    return NextResponse.next();
  }

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

    const response = NextResponse.next();
    response.cookies.set("admin_key", adminKey, {
      path: "/",
      maxAge: 86400,
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    });
    response.cookies.set("admin_key_validated", "1", {
      path: "/",
      maxAge: 300,
      httpOnly: true,
      sameSite: "lax",
    });
    return response;
  } catch {
    return NextResponse.next();
  }
}
