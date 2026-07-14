import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
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
  }

  return NextResponse.next();
}
