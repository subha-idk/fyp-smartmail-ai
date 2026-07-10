"use client";

import * as React from "react";
import Link from "next/link";
import {
  ShoppingCart,
  Eye,
  ArrowLeft,
  CheckCircle2,
  Tag,
  Star,
  Settings,
  Mail,
  Loader2,
  AlertTriangle,
  Play,
  Search
} from "lucide-react";

// ── Demo user UUID (mapped to Suvodip Patra in database) ───────────
const DEMO_USER_UUID = "863eeea6-048c-5778-9a41-39640d7bd051";

// ── Hardcoded product catalogue (mapped to seeded DB products) ──────
const PRODUCTS = [
  {
    id: "decd739b-9f46-5fb7-abb8-086460a78493",
    name: "Wireless Headphones Pro",
    category: "Electronics",
    price: 321.52,
    stock: 18,
    rating: 4.8,
    badge: "Best Seller",
    imageUrl: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80",
  },
  {
    id: "2d706e5e-8b7c-5654-9720-f9662dc9ad39",
    name: "Bluetooth Speaker X",
    category: "Electronics",
    price: 369.55,
    stock: 45,
    rating: 4.6,
    badge: "Hot Deal",
    imageUrl: "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&q=80",
  },
  {
    id: "9c03f0e3-f6af-55b4-9ad5-89629f1ca738",
    name: "Canvas Sneakers",
    category: "Footwear",
    price: 229.44,
    stock: 12,
    rating: 4.9,
    badge: "New Arrival",
    imageUrl: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80",
  },
  {
    id: "1c688edf-875d-563b-88e7-681df41d1439",
    name: "Yoga Mat Premium",
    category: "Sports",
    price: 296.28,
    stock: 30,
    rating: 4.7,
    badge: "Trending",
    imageUrl: "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=600&q=80",
  },
  {
    id: "a9f96a28-547c-5f1b-9a40-69c9695c6e08",
    name: "Vitamin C Serum",
    category: "Beauty",
    price: 256.29,
    stock: 8,
    rating: 4.5,
    badge: "Recommended",
    imageUrl: "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600&q=80",
  },
  {
    id: "f0e40bb9-2644-5f75-8df6-3a734a8506f2",
    name: "Wall Clock Modern",
    category: "Home",
    price: 229.59,
    stock: 22,
    rating: 4.4,
    badge: "Limited Stock",
    imageUrl: "https://images.unsplash.com/photo-1563861826100-9cb868fdad1c?w=600&q=80",
  },
] as const;

// ── Toast component ───────────────────────────────────────────────
function Toast({
  message,
  visible,
}: {
  message: string;
  visible: boolean;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded bg-slate-900 text-white text-sm font-semibold shadow-xl border border-slate-700 transition-all duration-300 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2 pointer-events-none"
      }`}
    >
      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
      {message}
    </div>
  );
}

// ── Product Card ──────────────────────────────────────────────────
function ProductCard({
  product,
  onTrack,
}: {
  product: (typeof PRODUCTS)[number];
  onTrack: (productId: string, eventType: string) => void;
}) {
  return (
    <div className="group bg-white rounded border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
      {/* Product Image */}
      <div className="h-56 bg-slate-50 relative flex items-center justify-center overflow-hidden">
        <img
          src={product.imageUrl}
          alt={product.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        {product.badge && (
          <span className="absolute top-2.5 left-2.5 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-sm bg-blue-600 text-white shadow-sm">
            {product.badge}
          </span>
        )}
        {product.stock <= 10 && (
          <span className="absolute top-2.5 right-2.5 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-sm bg-red-600 text-white">
            Low Stock
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider block mb-1">
            {product.category}
          </span>
          <h3 className="text-sm font-semibold text-slate-800 mb-1.5 hover:text-blue-600 cursor-pointer line-clamp-2">
            {product.name}
          </h3>

          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center gap-0.5 text-xs font-bold bg-green-600 text-white px-1.5 py-0.5 rounded-sm">
              {product.rating} <Star className="h-2.5 w-2.5 fill-white stroke-none" />
            </span>
            <span className="text-xs font-semibold text-slate-400">(45 Reviews)</span>
          </div>

          <div className="flex items-baseline gap-2 mb-4">
            <span className="text-lg font-bold text-slate-900">
              ₹{Math.round(product.price * 80).toLocaleString("en-IN")}
            </span>
            <span className="text-xs text-slate-400 line-through">
              ₹{Math.round(product.price * 80 * 1.3).toLocaleString("en-IN")}
            </span>
            <span className="text-xs text-green-600 font-bold">
              30% OFF
            </span>
          </div>
        </div>

        {/* Flipkart style orange and yellow CTAs */}
        <div className="flex gap-2">
          <button
            id={`cart-${product.id}`}
            onClick={() => onTrack(product.id, "cart_add")}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-bold rounded-sm bg-[#ff9f00] hover:bg-[#f29700] text-black cursor-pointer shadow-sm border-none uppercase transition-all"
          >
            <ShoppingCart className="h-3.5 w-3.5" />
            Add to Cart
          </button>
          <button
            id={`view-${product.id}`}
            onClick={() => onTrack(product.id, "product_view")}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-bold rounded-sm bg-[#fb641b] hover:bg-[#ea5c16] text-white cursor-pointer shadow-sm border-none uppercase transition-all"
          >
            <Eye className="h-3.5 w-3.5" />
            View Detail
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────
export default function DemoPage() {
  const [toastVisible, setToastVisible] = React.useState(false);
  const [toastMsg, setToastMsg] = React.useState("Event tracked ✓");
  const toastTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Presenter settings states
  const [panelOpen, setPanelOpen] = React.useState(true);
  const [passcode, setPasscode] = React.useState("");
  const [dbEmail, setDbEmail] = React.useState("");
  const [demoEmail, setDemoEmail] = React.useState("");
  const [dbName, setDbName] = React.useState("");
  const [demoName, setDemoName] = React.useState("");
  const [isUpdatingEmail, setIsUpdatingEmail] = React.useState(false);
  const [emailStatus, setEmailStatus] = React.useState<"idle" | "success" | "error" | "unauthorized">("idle");

  // Scheduler toggle states
  const [schedulerEnabled, setSchedulerEnabled] = React.useState(false);
  const [isTogglingScheduler, setIsTogglingScheduler] = React.useState(false);

  // Dispatch states
  const [dispatchStatus, setDispatchStatus] = React.useState<"idle" | "loading" | "success" | "error" | "skipped" | "unauthorized">("idle");
  const [dispatchDetails, setDispatchDetails] = React.useState<any>(null);
  const [dispatchError, setDispatchError] = React.useState("");

  // Live tracking events logs
  const [eventLogs, setEventLogs] = React.useState<Array<{ time: string; type: string; details: string }>>([]);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setToastVisible(true);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToastVisible(false), 3000);
  };

  // Load passcode from local storage on mount
  React.useEffect(() => {
    const saved = localStorage.getItem("presenter_passcode") || "";
    setPasscode(saved);
  }, []);

  const handlePasscodeChange = (val: string) => {
    setPasscode(val);
    localStorage.setItem("presenter_passcode", val);
  };

  // Fetch current database profile details & scheduler status on load
  React.useEffect(() => {
    const fetchDemoUser = async () => {
      try {
        const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
        const res = await fetch(`${base}/api/users?q=Suvodip`, {
          headers: {
            "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "",
          },
        });
        if (res.ok) {
          const data = await res.json();
          if (data.users && data.users.length > 0) {
            const user = data.users.find((u: any) => u.id === DEMO_USER_UUID);
            if (user) {
              setDbEmail(user.email);
              setDemoEmail(user.email);
              setDbName(user.name || "");
              setDemoName(user.name || "");
            }
          }
        }
      } catch (err) {
        console.error("Failed to load demo user", err);
      }
    };

    const fetchSchedulerStatus = async () => {
      try {
        const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
        const res = await fetch(`${base}/api/send-email/scheduler/status`, {
          headers: {
            "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "",
          },
        });
        if (res.ok) {
          const data = await res.json();
          setSchedulerEnabled(data.scheduler_autotrigger_enabled);
        }
      } catch (err) {
        console.error("Failed to load scheduler status", err);
      }
    };

    fetchDemoUser();
    fetchSchedulerStatus();
  }, []);

  const handleUpdateEmail = async () => {
    if (!demoEmail || !demoName) return;
    setIsUpdatingEmail(true);
    setEmailStatus("idle");
    try {
      const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
      const res = await fetch(`${base}/api/users/${DEMO_USER_UUID}/email`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "",
          "X-Presenter-Passcode": passcode,
        },
        body: JSON.stringify({ email: demoEmail, name: demoName }),
      });
      if (res.ok) {
        setDbEmail(demoEmail);
        setDbName(demoName);
        setEmailStatus("success");
        showToast("Recipient details updated in database!");
      } else if (res.status === 401) {
        setEmailStatus("unauthorized");
        showToast("Access Denied: Invalid Passcode.");
      } else {
        setEmailStatus("error");
      }
    } catch {
      setEmailStatus("error");
    } finally {
      setIsUpdatingEmail(false);
    }
  };

  const handleToggleScheduler = async () => {
    setIsTogglingScheduler(true);
    const targetState = !schedulerEnabled;
    try {
      const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
      const res = await fetch(`${base}/api/send-email/scheduler/toggle`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "",
          "X-Presenter-Passcode": passcode,
        },
        body: JSON.stringify({ enabled: targetState }),
      });
      if (res.ok) {
        setSchedulerEnabled(targetState);
        showToast(`Automatic email trigger ${targetState ? "ENABLED" : "DISABLED"}`);
      } else if (res.status === 401) {
        showToast("Access Denied: Invalid Passcode.");
      } else {
        showToast("Failed to toggle scheduler settings.");
      }
    } catch {
      showToast("Network error toggling scheduler.");
    } finally {
      setIsTogglingScheduler(false);
    }
  };

  const handleDispatchEmail = async () => {
    setDispatchStatus("loading");
    setDispatchError("");
    setDispatchDetails(null);
    try {
      const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
      const res = await fetch(`${base}/api/send-email/${DEMO_USER_UUID}?bypass_cooldown=true`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "",
          "X-Presenter-Passcode": passcode,
        },
      });
      const data = await res.json();
      if (res.ok) {
        if (data.status === "skipped") {
          setDispatchStatus("skipped");
        } else {
          setDispatchStatus("success");
          setDispatchDetails(data);
          showToast("AI Email Dispatched!");
        }
      } else if (res.status === 401) {
        setDispatchStatus("unauthorized");
        showToast("Access Denied: Invalid Passcode.");
      } else {
        setDispatchStatus("error");
        setDispatchError(data.detail || "Dispatch failed.");
      }
    } catch (err: any) {
      setDispatchStatus("error");
      setDispatchError(err.message || "Failed to trigger email dispatch.");
    }
  };

  const handleTrack = async (productId: string, eventType: string) => {
    const prodName = PRODUCTS.find((p) => p.id === productId)?.name || "Unknown Product";
    // Optimistically log event in live feed
    const now = new Date().toLocaleTimeString();
    setEventLogs((prev) => [
      { time: now, type: eventType, details: `${eventType.replace("_", " ")} on "${prodName}"` },
      ...prev,
    ]);

    try {
      const base = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
      const res = await fetch(`${base}/api/track`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "",
        },
        body: JSON.stringify({
          user_id: DEMO_USER_UUID,
          product_id: productId,
          event_type: eventType,
        }),
      });
      if (res.ok) {
        showToast(`Event tracked ✓`);
      } else {
        showToast(`Failed to track event (Status: ${res.status})`);
      }
    } catch {
      showToast("Tracking failed — connection error");
    }
  };

  return (
    <div className="min-h-screen bg-[#f1f3f6] text-slate-800 -m-6 md:-m-8 overflow-y-auto">
      {/* Flipkart Blue Header */}
      <header className="sticky top-0 z-30 bg-[#2874f0] text-white px-6 py-2.5 shadow-md">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          
          {/* Logo & Star */}
          <div className="flex items-center gap-8">
            <div className="flex flex-col">
              <div className="flex items-center gap-0.5">
                <span className="font-bold italic text-lg leading-none tracking-wide text-white">SmartMail</span>
                <span className="text-xs italic font-bold text-[#ffe500] leading-none flex items-center gap-0.5">
                  Plus<Star className="h-3 w-3 fill-[#ffe500] stroke-none" />
                </span>
              </div>
              <span className="text-[9px] text-[#f0f0f0] font-semibold tracking-wide">DEMO STORE</span>
            </div>

            {/* Mock Search Bar */}
            <div className="hidden md:flex items-center w-96 relative">
              <input
                type="text"
                placeholder="Search for products, brands and more"
                className="w-full bg-white text-slate-800 text-xs px-4 py-2 pr-10 rounded shadow-inner focus:outline-none placeholder-slate-400"
                disabled
              />
              <Search className="h-4 w-4 text-blue-600 absolute right-3" />
            </div>
          </div>

          {/* Action buttons & Links */}
          <div className="flex items-center gap-6 text-sm font-semibold">
            <button
              onClick={() => setPanelOpen(!panelOpen)}
              className="bg-white text-[#2874f0] px-6 py-1 rounded shadow-sm hover:bg-[#f0f0f0] text-xs cursor-pointer flex items-center gap-1.5 transition-all"
            >
              <Settings className={`h-3.5 w-3.5 ${panelOpen ? "animate-spin" : ""}`} />
              Presenter Panel
            </button>
            
            <Link
              href="/"
              className="flex items-center gap-1.5 text-xs text-white hover:underline transition-colors duration-150 cursor-pointer"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Presenter Control Panel (Sandbox) */}
      {panelOpen && (
        <section className="bg-slate-900 text-slate-100 border-b border-slate-700 px-6 py-6 shadow-inner animate-slide-down">
          <div className="max-w-6xl mx-auto flex flex-col gap-6">
            
            {/* Passcode Security Lock Bar */}
            <div className="bg-slate-950 p-4 rounded border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2.5">
                <span className={`h-2.5 w-2.5 rounded-full ${passcode ? "bg-emerald-500 animate-pulse" : "bg-red-500 animate-ping"}`} />
                <div>
                  <span className="text-xs font-bold text-slate-200 block">Presenter Sandbox Security</span>
                  <span className="text-[10px] text-slate-500 block leading-tight">Requires Server Passcode to execute DB writes or schedule triggers</span>
                </div>
              </div>
              <div className="flex gap-2 w-full sm:w-auto">
                <input
                  type="password"
                  placeholder="Enter Presenter Passcode (e.g. demo2026)"
                  value={passcode}
                  onChange={(e) => handlePasscodeChange(e.target.value)}
                  className="bg-slate-900 text-white text-xs px-3 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-blue-500 w-full sm:w-64 font-mono tracking-widest text-center"
                />
              </div>
            </div>

            {/* Config & Logs Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              
              {/* Column 1: Configuration */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-blue-400">1. Setup Presenter Profile</h3>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Enter your real email and name to receive the live demo emails addressed to you! (Requires SMTP config in backend .env).
                </p>
                
                <div className="space-y-2.5">
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Recipient Name</label>
                    <input
                      type="text"
                      value={demoName}
                      onChange={(e) => setDemoName(e.target.value)}
                      placeholder="Enter name"
                      className="w-full bg-slate-800 text-white text-xs px-3 py-2 rounded border border-slate-700 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Recipient Email</label>
                    <input
                      type="email"
                      value={demoEmail}
                      onChange={(e) => setDemoEmail(e.target.value)}
                      placeholder="Enter email address"
                      className="w-full bg-slate-800 text-white text-xs px-3 py-2 rounded border border-slate-700 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  
                  <button
                    onClick={handleUpdateEmail}
                    disabled={isUpdatingEmail}
                    className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-xs py-2 rounded cursor-pointer transition-all shadow"
                  >
                    {isUpdatingEmail ? "Saving..." : "Save Settings to Database"}
                  </button>
                  
                  {emailStatus === "success" && (
                    <p className="text-[11px] text-green-400 font-medium">✓ Profile details updated in DB successfully!</p>
                  )}
                  {emailStatus === "error" && (
                    <p className="text-[11px] text-red-400 font-medium">✗ Failed to update settings. Make sure backend is running.</p>
                  )}
                  {emailStatus === "unauthorized" && (
                    <p className="text-[11px] text-red-400 font-bold">✗ Access Denied: Invalid Presenter Passcode.</p>
                  )}
                  
                  <div className="text-[10px] text-slate-500 italic pt-1 border-t border-slate-800 flex justify-between">
                    <span>DB Name: <strong className="text-slate-300">{dbName || "Loading..."}</strong></span>
                    <span>DB Email: <strong className="text-slate-300">{dbEmail || "Loading..."}</strong></span>
                  </div>
                </div>
              </div>

              {/* Column 2: Trigger & Dispatch Status */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400">2. Trigger AI Email Dispatch</h3>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  After browsing products to generate events, click the button below to bypass the cooldown limits and trigger the personalized email pipeline.
                </p>

                <div className="space-y-3">
                  <button
                    onClick={handleDispatchEmail}
                    disabled={dispatchStatus === "loading"}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs py-2.5 px-4 rounded cursor-pointer flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/30"
                  >
                    {dispatchStatus === "loading" ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Evaluating &amp; Generating...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 fill-white text-none" />
                        Bypass Cooldown &amp; Send AI Email
                      </>
                    )}
                  </button>

                  {/* Scheduler Toggle Switch */}
                  <div className="bg-slate-950/50 rounded border border-slate-800 p-3 flex items-center justify-between gap-4">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-300 block">Automatic Scheduler</span>
                      <span className="text-[9px] text-slate-500 block leading-tight">Secured background cron triggers</span>
                    </div>
                    
                    <button
                      onClick={handleToggleScheduler}
                      disabled={isTogglingScheduler}
                      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                        schedulerEnabled ? "bg-emerald-600" : "bg-slate-700"
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                          schedulerEnabled ? "translate-x-5" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>
                </div>

                {/* Status Output Box */}
                <div className="bg-slate-950 rounded border border-slate-800 p-3 min-h-[80px] flex items-center justify-center text-xs">
                  {dispatchStatus === "idle" && (
                    <span className="text-slate-500 italic">Waiting to dispatch...</span>
                  )}
                  {dispatchStatus === "loading" && (
                    <div className="text-center text-slate-400 space-y-1">
                      <p className="font-semibold text-slate-300">Executing Email Pipeline</p>
                      <p className="text-[10px] text-slate-500">Checking model, recommending product, generating via LLM...</p>
                    </div>
                  )}
                  {dispatchStatus === "skipped" && (
                    <div className="text-center text-amber-400 space-y-1">
                      <p className="font-bold flex items-center justify-center gap-1">
                        <AlertTriangle className="h-4 w-4 text-amber-400" />
                        Dispatch Skipped
                      </p>
                      <p className="text-[10px] text-slate-500">User is currently in a cooldown period.</p>
                    </div>
                  )}
                  {dispatchStatus === "unauthorized" && (
                    <div className="text-center text-red-400 space-y-1">
                      <p className="font-bold">Access Denied</p>
                      <p className="text-[10px] text-slate-500 font-semibold">Invalid Presenter Passcode header values.</p>
                    </div>
                  )}
                  {dispatchStatus === "error" && (
                    <div className="text-center text-red-400 space-y-1">
                      <p className="font-bold">Dispatch Failed</p>
                      <p className="text-[10px] text-slate-500">{dispatchError}</p>
                    </div>
                  )}
                  {dispatchStatus === "success" && dispatchDetails && (
                    <div className="w-full text-left space-y-1.5">
                      <div className="flex justify-between items-center text-[10px]">
                        <span className="text-slate-500 uppercase font-bold">Campaign Type</span>
                        <span className="bg-blue-900/40 text-blue-300 font-bold px-1.5 py-0.5 rounded uppercase">
                          {dispatchDetails.email_type?.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="text-slate-200">
                        <span className="text-slate-500 block text-[9px] uppercase font-bold">Subject Line</span>
                        <p className="italic text-slate-300 font-medium font-sans">
                          &ldquo;{dispatchDetails.subject}&rdquo;
                        </p>
                      </div>
                      <div className="text-[10px] text-slate-400 pt-1 flex justify-between border-t border-slate-900">
                        <span>Recipient: <strong className="text-slate-300">{dbEmail}</strong></span>
                        <span className="text-emerald-400 font-bold">SENT SUCCESSFULLY</span>
                      </div>
                      <div className="text-[9px] text-slate-500 leading-none">
                        Note: View the formatted HTML email in the Mailhog inbox at <a href="http://localhost:8025" target="_blank" rel="noreferrer" className="text-blue-400 underline">http://localhost:8025</a>.
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Column 3: Live Behavior Tracker */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#ff9f00] animate-pulse" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-[#ff9f00]">3. Live Behavior Tracker</h3>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Clicking product cards below will emit events. See them logged live here and stored in the database.
                </p>

                <div className="bg-slate-950 rounded border border-slate-800 p-2.5 h-36 overflow-y-auto font-mono text-[10px] space-y-1.5">
                  {eventLogs.length === 0 ? (
                    <span className="text-slate-600 italic block text-center pt-8">No events emitted yet. Click products below.</span>
                  ) : (
                    eventLogs.map((log, index) => (
                      <div key={index} className="flex gap-2 text-slate-300">
                        <span className="text-slate-500 shrink-0">{log.time}</span>
                        <span className="text-blue-400 font-semibold shrink-0">[{log.type.toUpperCase()}]</span>
                        <span className="text-slate-400 truncate">{log.details}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>
          </div>
        </section>
      )}

      {/* Secondary Categories bar */}
      <div className="bg-white border-b border-slate-200 py-3 px-6 shadow-sm">
        <div className="max-w-6xl mx-auto flex items-center justify-start gap-8 md:gap-12 overflow-x-auto scrollbar-none text-slate-600 font-bold text-xs uppercase tracking-wider">
          <span className="text-blue-600 border-b-2 border-blue-600 pb-3 cursor-pointer shrink-0">All Products</span>
          <span className="hover:text-blue-600 cursor-pointer pb-3 shrink-0">Electronics</span>
          <span className="hover:text-blue-600 cursor-pointer pb-3 shrink-0">Footwear</span>
          <span className="hover:text-blue-600 cursor-pointer pb-3 shrink-0">Sports</span>
          <span className="hover:text-blue-600 cursor-pointer pb-3 shrink-0">Beauty</span>
          <span className="hover:text-blue-600 cursor-pointer pb-3 shrink-0">Home</span>
        </div>
      </div>

      {/* Hero Strip banner */}
      <section className="bg-white px-6 py-6 border-b border-slate-200">
        <div className="max-w-6xl mx-auto">
          {/* Flipkart-like Big Billion Day Promo Banner */}
          <div className="bg-gradient-to-r from-blue-700 to-indigo-900 text-white rounded-lg p-6 shadow-md relative overflow-hidden flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="space-y-2 z-10">
              <div className="inline-block bg-[#ffe500] text-blue-900 text-[10px] font-extrabold uppercase tracking-widest px-2.5 py-0.5 rounded-sm shadow-sm">
                BIG SHOPPING DAYS
              </div>
              <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight">Super Deals on Smart Collections</h2>
              <p className="text-xs text-blue-100 max-w-md">
                Browse, add to cart, and check out items. The AI Recommendation Engine tracks your interactions to build a real-time behavioral profile.
              </p>
            </div>
            
            <div className="bg-white/10 backdrop-blur-md rounded-md p-4 border border-white/15 text-center shrink-0 z-10">
              <p className="text-[10px] font-bold uppercase tracking-wider text-yellow-300">Live Demo Active</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs font-semibold">Events Transmitted Real-Time</span>
              </div>
            </div>
            
            {/* Background design elements */}
            <div className="absolute right-0 top-0 h-40 w-40 bg-blue-500/20 rounded-full blur-2xl transform translate-x-12 -translate-y-12" />
            <div className="absolute left-1/3 bottom-0 h-28 w-28 bg-indigo-500/20 rounded-full blur-2xl transform translate-y-12" />
          </div>
        </div>
      </section>

      {/* Main Grid */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-widest flex items-center gap-2">
            Deals of the Day
            <span className="h-1.5 w-1.5 rounded-full bg-red-600 animate-pulse" />
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {PRODUCTS.map((product) => (
            <ProductCard key={product.id} product={product} onTrack={handleTrack} />
          ))}
        </div>

        {/* Footer */}
        <footer className="mt-16 text-center text-xs text-slate-400 border-t border-slate-200 pt-8 pb-12 space-y-1.5">
          <p className="font-semibold text-slate-500">SmartMail AI+ • Final Year Project Demo</p>
          <p>
            Engineered with a humanized e-commerce flow. Recommended products and email templates are generated dynamically.
          </p>
        </footer>
      </main>

      {/* Toast */}
      <Toast message={toastMsg} visible={toastVisible} />
    </div>
  );
}
