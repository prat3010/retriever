"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Building2,
  UserPlus,
  Settings,
  Sun,
  Moon,
  ScrollText,
  LogOut,
  Database,
  Zap,
  Puzzle,
  Bot,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/tenants", label: "Tenants", icon: Building2 },
  { href: "/prompts", label: "Prompt Optimization", icon: Sparkles },
  { href: "/batteries", label: "Batteries & Engines", icon: Zap },
  { href: "/integrations", label: "Integrations & Plugins", icon: Puzzle },
  { href: "/orchestration", label: "Agentic Orchestration", icon: Bot },
  { href: "/onboard", label: "Onboard Client", icon: UserPlus },
  { href: "/audit-log", label: "Audit Log", icon: ScrollText },
  { href: "/system-data", label: "System Data", icon: Database },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const clearKey = useAuthStore((s) => s.clearKey);
  const router = useRouter();
  const { theme, setTheme } = useTheme();

  function handleLogout() {
    clearKey();
    router.push("/login");
  }

  return (
    <aside className="flex h-full w-64 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-6">
        <Link href="/" className="flex items-center gap-2 font-heading text-lg font-bold">
          <Building2 className="h-5 w-5" aria-hidden="true" />
          <span>Retriever</span>
        </Link>
      </div>

      <nav aria-label="Main Navigation" className="flex-1 space-y-1 p-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4 space-y-1">
        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun className="mr-2 h-4 w-4" aria-hidden="true" /> : <Moon className="mr-2 h-4 w-4" aria-hidden="true" />}
          {theme === "dark" ? "Light Mode" : "Dark Mode"}
        </Button>
        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground"
          onClick={handleLogout}
          aria-label="Logout of admin session"
        >
          <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
          Logout
        </Button>
      </div>
    </aside>
  );
}
