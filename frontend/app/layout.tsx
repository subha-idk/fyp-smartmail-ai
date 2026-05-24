"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users as UsersIcon,
  Mail,
  BarChart3,
  Menu,
  X,
  Radio,
  ShoppingBag,
} from "lucide-react";
import "./globals.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [isMobileOpen, setIsMobileOpen] = React.useState(false);
  const [isApiHealthy, setIsApiHealthy] = React.useState<boolean | null>(null);

  // Check backend health status
  React.useEffect(() => {
    const checkHealth = async () => {
      try {
        const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        const res = await fetch(`${base}/api/health`);
        if (res.ok) {
          const data = await res.json();
          setIsApiHealthy(data.status === "ok");
        } else {
          setIsApiHealthy(false);
        }
      } catch {
        setIsApiHealthy(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Users", href: "/users", icon: UsersIcon },
    { name: "Campaigns", href: "/campaigns", icon: Mail },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
    { name: "Demo Store", href: "/demo", icon: ShoppingBag },
  ];

  // Breadcrumb map
  const breadcrumbMap: Record<string, string> = {
    "/": "Dashboard Overview",
    "/users": "Users Directory",
    "/campaigns": "Campaign History",
    "/analytics": "Analytics & Performance",
    "/demo": "Zypheron Demo Store",
  };
  const breadcrumb =
    breadcrumbMap[pathname] ??
    (pathname.startsWith("/users/") ? "Customer Profile" : "Dashboard");

  const SidebarContent = ({ mobile = false }: { mobile?: boolean }) => (
    <>
      {/* Logo */}
      <div
        className={`flex h-16 items-center justify-between px-5 border-b border-[rgba(99,102,241,0.1)] ${
          mobile ? "" : ""
        }`}
      >
        <Link
          href="/"
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => mobile && setIsMobileOpen(false)}
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white text-xs font-bold shadow-[0_0_12px_rgba(99,102,241,0.4)]">
            SM
          </span>
          <span className="text-sm font-bold text-white tracking-wide">
            SmartMail AI+
          </span>
        </Link>
        {mobile && (
          <button
            onClick={() => setIsMobileOpen(false)}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-[rgba(99,102,241,0.1)] transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1" aria-label="Main navigation">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => mobile && setIsMobileOpen(false)}
              className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 cursor-pointer relative ${
                isActive
                  ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                  : "text-slate-400 hover:bg-[rgba(99,102,241,0.08)] hover:text-slate-200"
              }`}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-indigo-500 rounded-full" />
              )}
              <Icon
                className={`h-4 w-4 shrink-0 ${
                  isActive ? "text-indigo-400" : "text-slate-500"
                }`}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Version */}
      <div className="px-5 py-4 border-t border-[rgba(99,102,241,0.1)]">
        <p className="text-xs text-slate-600 font-mono">v1.0.0</p>
        <p className="text-[10px] text-slate-700 mt-0.5">FYP 2026 · SmartMail AI+</p>
      </div>
    </>
  );

  return (
    <html lang="en" className="h-full" style={{ backgroundColor: "#0a0f1e" }}>
      <head>
        <title>SmartMail AI+ — AI-Powered Email CRM</title>
        <meta
          name="description"
          content="SmartMail AI+: Enterprise AI-powered B2B SaaS analytics dashboard for email automation and customer engagement."
        />
      </head>
      <body className="h-full font-sans antialiased" style={{ backgroundColor: "#0a0f1e", color: "#f1f5f9" }}>
        <div className="flex h-full min-h-screen overflow-hidden">
          {/* ── Desktop Sidebar ─────────────────────────── */}
          <aside
            className="hidden w-64 md:flex md:flex-col flex-shrink-0"
            style={{ backgroundColor: "#080d1a", borderRight: "1px solid rgba(99,102,241,0.1)" }}
          >
            <SidebarContent />
          </aside>

          {/* ── Mobile Sidebar Overlay ───────────────────── */}
          {isMobileOpen && (
            <div className="fixed inset-0 z-50 flex md:hidden">
              <div
                className="fixed inset-0 bg-black/70 backdrop-blur-sm"
                onClick={() => setIsMobileOpen(false)}
              />
              <aside
                className="relative flex w-64 flex-col z-10 animate-slide-in-left"
                style={{ backgroundColor: "#080d1a", borderRight: "1px solid rgba(99,102,241,0.1)" }}
              >
                <SidebarContent mobile />
              </aside>
            </div>
          )}

          {/* ── Main Content Area ─────────────────────────── */}
          <div
            className="flex flex-1 flex-col overflow-hidden"
            style={{ backgroundColor: "#0a0f1e" }}
          >
            {/* Top Header */}
            <header
              className="flex h-14 items-center justify-between px-6 flex-shrink-0"
              style={{
                backgroundColor: "rgba(8,13,26,0.8)",
                borderBottom: "1px solid rgba(99,102,241,0.08)",
                backdropFilter: "blur(12px)",
              }}
            >
              <div className="flex items-center gap-4">
                {/* Mobile hamburger */}
                <button
                  onClick={() => setIsMobileOpen(true)}
                  className="p-2 -ml-1 rounded-md md:hidden text-slate-400 hover:text-white hover:bg-[rgba(99,102,241,0.1)] transition-colors cursor-pointer"
                  aria-label="Open navigation"
                >
                  <Menu className="h-5 w-5" />
                </button>
                {/* Breadcrumb */}
                <div className="hidden md:flex items-center gap-2 text-sm">
                  <span className="text-slate-600">SmartMail AI+</span>
                  <span className="text-slate-700">/</span>
                  <span className="text-slate-300 font-medium">{breadcrumb}</span>
                </div>
                {/* Mobile title */}
                <h1 className="text-sm font-semibold text-slate-200 md:hidden">
                  SmartMail AI+
                </h1>
              </div>

              {/* API Status */}
              <div className="flex items-center gap-2">
                <div
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
                  style={{
                    background: "rgba(15,23,41,0.8)",
                    border: "1px solid rgba(99,102,241,0.15)",
                  }}
                >
                  <Radio
                    className={`h-3 w-3 ${
                      isApiHealthy ? "text-emerald-400 animate-pulse" : "text-red-400"
                    }`}
                  />
                  <span className="text-slate-400 font-medium">API</span>
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      isApiHealthy === null
                        ? "bg-amber-400"
                        : isApiHealthy
                        ? "bg-emerald-400"
                        : "bg-red-400"
                    }`}
                  />
                  <span
                    className={`font-semibold ${
                      isApiHealthy === null
                        ? "text-amber-400"
                        : isApiHealthy
                        ? "text-emerald-400"
                        : "text-red-400"
                    }`}
                  >
                    {isApiHealthy === null
                      ? "checking"
                      : isApiHealthy
                      ? "online"
                      : "offline"}
                  </span>
                </div>
              </div>
            </header>

            {/* Page Content */}
            <main className="flex-1 overflow-y-auto p-6 md:p-8">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
