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
  Sun,
  Moon,
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
  
  // Theme State
  const [theme, setTheme] = React.useState<"light" | "dark">("light");

  // Initialize theme from localStorage
  React.useEffect(() => {
    const saved = localStorage.getItem("theme") as "light" | "dark" | null;
    const initial = saved || "light";
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  // Toggle Theme handler
  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    localStorage.setItem("theme", next);
    document.documentElement.setAttribute("data-theme", next);
  };

  // Check backend health status
  React.useEffect(() => {
    const checkHealth = async () => {
      try {
        const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
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
    "/demo": "SmartMail Plus Demo Store",
  };
  
  const isDemoStore = pathname === "/demo";
  
  const breadcrumb =
    breadcrumbMap[pathname] ??
    (pathname.startsWith("/users/") ? "Customer Profile" : "Dashboard");

  const SidebarContent = ({ mobile = false }: { mobile?: boolean }) => (
    <div className="flex flex-col h-full bg-[var(--color-sidebar)] text-slate-300">
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-5 border-b border-white/5">
        <Link
          href="/"
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => mobile && setIsMobileOpen(false)}
        >
          <span className="flex h-8 w-8 items-center justify-center rounded bg-[#0060ff] text-white text-xs font-bold shadow-[0_2px_8px_rgba(0,96,255,0.4)]">
            SM
          </span>
          <span className="text-sm font-bold text-white tracking-wide">
            SmartMail Plus
          </span>
        </Link>
        {mobile && (
          <button
            onClick={() => setIsMobileOpen(false)}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
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
              className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded transition-all duration-200 cursor-pointer relative ${
                isActive
                  ? "bg-[#0060ff]/15 text-[#3b82f6] border border-[#0060ff]/25 font-semibold"
                  : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
              }`}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-[#0060ff] rounded-full" />
              )}
              <Icon
                className={`h-4 w-4 shrink-0 ${
                  isActive ? "text-[#3b82f6]" : "text-slate-500"
                }`}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Version */}
      <div className="px-5 py-4 border-t border-white/5">
        <p className="text-xs text-slate-600 font-mono">v1.0.0</p>
        <p className="text-[10px] text-slate-500 mt-0.5">FYP 2026 · SmartMail Plus</p>
      </div>
    </div>
  );

  // If loading the demo store, bypass Zoho layout styling, keep it full width
  if (isDemoStore) {
    return (
      <html lang="en" className="h-full">
        <head>
          <title>SmartMail Plus — Demo Store</title>
        </head>
        <body className="h-full font-sans antialiased bg-[#f1f3f6] text-slate-800">
          <main className="p-6 md:p-8">{children}</main>
        </body>
      </html>
    );
  }

  return (
    <html lang="en" className="h-full" data-theme={theme}>
      <head>
        <title>SmartMail Plus — AI-Powered Email CRM</title>
        <meta
          name="description"
          content="SmartMail Plus: Enterprise AI-powered B2B SaaS analytics dashboard for email automation and customer engagement."
        />
      </head>
      <body className="h-full font-sans antialiased bg-[var(--color-bg)] text-[var(--color-text)] transition-colors duration-200">
        <div className="flex h-full min-h-screen overflow-hidden">
          
          {/* Desktop Sidebar */}
          <aside className="hidden w-64 md:flex md:flex-col flex-shrink-0 border-r border-white/5 bg-[var(--color-sidebar)]">
            <SidebarContent />
          </aside>

          {/* Mobile Sidebar Overlay */}
          {isMobileOpen && (
            <div className="fixed inset-0 z-50 flex md:hidden">
              <div
                className="fixed inset-0 bg-black/70 backdrop-blur-sm"
                onClick={() => setIsMobileOpen(false)}
              />
              <aside className="relative flex w-64 flex-col z-10 bg-[var(--color-sidebar)] border-r border-white/5">
                <SidebarContent mobile />
              </aside>
            </div>
          )}

          {/* Main Content Area */}
          <div className="flex flex-1 flex-col overflow-hidden bg-[var(--color-bg)]">
            
            {/* Top Header */}
            <header className="flex h-14 items-center justify-between px-6 flex-shrink-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] shadow-sm">
              <div className="flex items-center gap-4">
                {/* Mobile hamburger */}
                <button
                  onClick={() => setIsMobileOpen(true)}
                  className="p-2 -ml-1 rounded md:hidden text-slate-400 hover:bg-slate-700/10 transition-colors cursor-pointer"
                  aria-label="Open navigation"
                >
                  <Menu className="h-5 w-5" />
                </button>
                
                {/* Breadcrumb */}
                <div className="hidden md:flex items-center gap-2 text-sm">
                  <span className="text-[var(--color-muted)]">SmartMail Plus</span>
                  <span className="text-slate-400">/</span>
                  <span className="text-[var(--color-text)] font-semibold">{breadcrumb}</span>
                </div>
                
                {/* Mobile title */}
                <h1 className="text-sm font-semibold text-[var(--color-text)] md:hidden">
                  SmartMail Plus
                </h1>
              </div>

              {/* Tools & Status Indicators */}
              <div className="flex items-center gap-3">
                
                {/* Theme Toggle Button */}
                <button
                  onClick={toggleTheme}
                  className="p-2 rounded-md hover:bg-slate-700/10 text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors cursor-pointer flex items-center justify-center border border-[var(--color-border)] bg-[var(--color-surface)]"
                  title={`Switch to ${theme === "light" ? "Dark" : "Light"} Mode`}
                >
                  {theme === "light" ? (
                    <Moon className="h-4 w-4 text-slate-600" />
                  ) : (
                    <Sun className="h-4 w-4 text-amber-400" />
                  )}
                </button>

                {/* API Status */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-[var(--color-border)] bg-[var(--color-surface)] text-xs shadow-sm">
                  <Radio
                    className={`h-3 w-3 ${
                      isApiHealthy ? "text-emerald-500 animate-pulse" : "text-red-500"
                    }`}
                  />
                  <span className="text-[var(--color-muted)] font-medium">API</span>
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      isApiHealthy === null
                        ? "bg-amber-500"
                        : isApiHealthy
                        ? "bg-emerald-500"
                        : "bg-red-500"
                    }`}
                  />
                  <span
                    className={`font-semibold uppercase tracking-wider text-[9px] ${
                      isApiHealthy === null
                        ? "text-amber-500"
                        : isApiHealthy
                        ? "text-emerald-500"
                        : "text-red-500"
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
            <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-[var(--color-bg)]">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
