"use client";

import { Sidebar } from "@/components/sidebar";
import { ErrorBoundary } from "@/components/error-boundary";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-md focus:outline-none focus:ring-2 focus:ring-ring"
      >
        Skip to main content
      </a>
      <Sidebar />
      <main id="main-content" tabIndex={-1} className="flex-1 overflow-auto bg-background focus:outline-none">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>
    </div>
  );
}
