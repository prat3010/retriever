"use client";

import type { ReactNode } from "react";

interface TopbarProps {
  title: string;
  description?: string;
  children?: ReactNode;
}

export function Topbar({ title, description, children }: TopbarProps) {
  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b px-6">
      <div>
        <h1 className="font-heading text-lg font-semibold">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </header>
  );
}
