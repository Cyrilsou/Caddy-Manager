import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Globe,
  Server,
  FileCode,
  Shield,
  Cloud,
  ScrollText,
  Settings,
  LogOut,
  Menu,
  X,
  Sun,
  Moon,
  Gauge,
  Search,
  Terminal,
  Users,
  Box,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useUIStore } from "@/stores/ui-store";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/domains", label: "Domains", icon: Globe },
  { to: "/backends", label: "Backends", icon: Server },
  { to: "/config", label: "Configuration", icon: FileCode },
  { to: "/certificates", label: "Certificates", icon: Shield },
  { to: "/cloudflare", label: "Cloudflare", icon: Cloud },
  { to: "/cache", label: "Cache CDN", icon: Gauge },
  { to: "/dns-check", label: "DNS Check", icon: Search },
  { to: "/logs", label: "Live Logs", icon: Terminal },
  { to: "/users", label: "Users", icon: Users },
  { to: "/docker", label: "Docker", icon: Box },
  { to: "/audit", label: "Audit Log", icon: ScrollText },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const username = useAuthStore((s) => s.username);
  const { theme, toggleTheme } = useUIStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  const sidebarContent = (
    <>
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <Shield className="h-6 w-6 text-primary" />
        <span className="text-lg font-bold">Caddy Panel</span>
        <button className="ml-auto lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close menu">
          <X className="h-5 w-5" />
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const active = location.pathname === item.to;
          return (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Theme</span>
          <button onClick={toggleTheme} className="text-muted-foreground hover:text-foreground" aria-label="Toggle theme">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{username}</span>
          <button
            onClick={async () => {
              try { await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" }); } catch {}
              logout();
              window.location.href = "/login";
            }}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Logout"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <>
      <button
        className="fixed left-4 top-4 z-50 rounded-md p-2 text-foreground hover:bg-accent lg:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      <aside className={cn(
        "flex h-screen w-64 flex-col border-r bg-card transition-transform duration-200",
        "fixed z-50 lg:relative lg:translate-x-0",
        mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        {sidebarContent}
      </aside>
    </>
  );
}
