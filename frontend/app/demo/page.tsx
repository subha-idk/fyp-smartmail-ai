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
} from "lucide-react";

// ── Demo user UUID (hardcoded for demo purposes) ─────────────────
const DEMO_USER_UUID = "demo-user-zypheron-001";

// ── Hardcoded product catalogue ──────────────────────────────────
const PRODUCTS = [
  {
    id: "prod-001",
    name: "Aerosphere Pro Headphones",
    category: "Electronics",
    price: 249.99,
    stock: 18,
    rating: 4.8,
    badge: "Best Seller",
    gradient: "from-indigo-500/20 to-violet-500/20",
    accent: "#6366f1",
  },
  {
    id: "prod-002",
    name: "LuminaDesk Wireless Charger",
    category: "Electronics",
    price: 89.99,
    stock: 45,
    rating: 4.6,
    badge: null,
    gradient: "from-sky-500/20 to-indigo-500/20",
    accent: "#0ea5e9",
  },
  {
    id: "prod-003",
    name: "VertexRun X2 Smart Sneakers",
    category: "Footwear",
    price: 179.99,
    stock: 12,
    rating: 4.9,
    badge: "New Arrival",
    gradient: "from-emerald-500/20 to-teal-500/20",
    accent: "#10b981",
  },
  {
    id: "prod-004",
    name: "ZenFlow Yoga Mat Pro",
    category: "Sports",
    price: 64.99,
    stock: 30,
    rating: 4.7,
    badge: null,
    gradient: "from-amber-500/20 to-orange-500/20",
    accent: "#f59e0b",
  },
  {
    id: "prod-005",
    name: "NovaSkin Hydra Serum Kit",
    category: "Beauty",
    price: 119.99,
    stock: 8,
    rating: 4.5,
    badge: "Limited",
    gradient: "from-rose-500/20 to-pink-500/20",
    accent: "#f43f5e",
  },
  {
    id: "prod-006",
    name: "ClearSight Smart Reading Glasses",
    category: "Accessories",
    price: 199.99,
    stock: 22,
    rating: 4.4,
    badge: null,
    gradient: "from-violet-500/20 to-purple-500/20",
    accent: "#8b5cf6",
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
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg bg-slate-900 text-white text-sm font-medium shadow-xl border border-slate-700 transition-all duration-300 ${
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
  const categoryColors: Record<string, string> = {
    Electronics: "bg-indigo-50 text-indigo-700 border-indigo-200",
    Footwear:    "bg-emerald-50 text-emerald-700 border-emerald-200",
    Sports:      "bg-amber-50 text-amber-700 border-amber-200",
    Beauty:      "bg-rose-50 text-rose-700 border-rose-200",
    Accessories: "bg-violet-50 text-violet-700 border-violet-200",
  };

  const catClass =
    categoryColors[product.category] ??
    "bg-slate-100 text-slate-600 border-slate-200";

  return (
    <div className="group bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md hover:border-indigo-200 transition-all duration-200">
      {/* Product image placeholder */}
      <div
        className={`h-44 bg-gradient-to-br ${product.gradient} flex items-center justify-center relative`}
      >
        <div
          className="h-20 w-20 rounded-2xl flex items-center justify-center shadow-lg"
          style={{ background: `${product.accent}20`, border: `2px solid ${product.accent}30` }}
        >
          <ShoppingCart
            className="h-9 w-9"
            style={{ color: product.accent }}
          />
        </div>
        {product.badge && (
          <span className="absolute top-3 left-3 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full bg-white/90 text-slate-800 border border-slate-200 shadow-sm">
            {product.badge}
          </span>
        )}
        {product.stock <= 10 && (
          <span className="absolute top-3 right-3 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full bg-red-500/90 text-white">
            Low Stock
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-5">
        <div className="flex items-start justify-between mb-2">
          <span
            className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${catClass}`}
          >
            <Tag className="h-2.5 w-2.5" />
            {product.category}
          </span>
          <div className="flex items-center gap-0.5 text-xs text-amber-500 font-semibold">
            <Star className="h-3 w-3 fill-amber-400 stroke-amber-400" />
            {product.rating}
          </div>
        </div>

        <h3 className="text-sm font-semibold text-slate-800 mb-1 line-clamp-2">
          {product.name}
        </h3>

        <div className="flex items-center justify-between mb-4">
          <span className="text-xl font-bold text-slate-900">
            ${product.price.toFixed(2)}
          </span>
          <span className="text-xs text-slate-400">
            {product.stock} left
          </span>
        </div>

        {/* CTA Buttons */}
        <div className="flex gap-2">
          <button
            id={`view-${product.id}`}
            onClick={() => onTrack(product.id, "product_view")}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-slate-200 text-slate-600 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50 transition-all duration-200 cursor-pointer"
          >
            <Eye className="h-3.5 w-3.5" />
            View Product
          </button>
          <button
            id={`cart-${product.id}`}
            onClick={() => onTrack(product.id, "cart_add")}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-all duration-200 cursor-pointer shadow-sm"
          >
            <ShoppingCart className="h-3.5 w-3.5" />
            Add to Cart
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

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setToastVisible(true);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToastVisible(false), 3000);
  };

  const handleTrack = async (productId: string, eventType: string) => {
    // Silently POST tracking event
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      await fetch(`${base}/api/track`, {
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
    } catch {
      // silently ignore tracking errors in demo
    }
    showToast(`Event tracked ✓`);
  };

  return (
    // Light mode override — white background isolated to this page
    <div className="min-h-full bg-white text-slate-800 -m-6 md:-m-8 overflow-y-auto">
      {/* Store Top Bar */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-sm border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <ShoppingCart className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-900">Zypheron Store</h1>
            <p className="text-[10px] text-slate-400">Demo Storefront</p>
          </div>
        </div>
        <Link
          href="/"
          className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-indigo-600 transition-colors duration-150 cursor-pointer"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Dashboard
        </Link>
      </header>

      {/* Hero strip */}
      <div className="bg-gradient-to-r from-indigo-50 to-violet-50 border-b border-indigo-100 px-6 py-8">
        <div className="max-w-6xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold mb-3">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-pulse" />
            SmartMail AI+ Demo — Events are tracked live
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-1">
            Discover Our Collection
          </h2>
          <p className="text-sm text-slate-500 max-w-lg">
            Browse products below. Clicking &ldquo;View Product&rdquo; or &ldquo;Add to Cart&rdquo;
            fires a real behavioural event tracked by the AI recommendation engine.
          </p>
        </div>
      </div>

      {/* Products Grid */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wider">
            All Products ({PRODUCTS.length})
          </h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {PRODUCTS.map((product) => (
            <ProductCard key={product.id} product={product} onTrack={handleTrack} />
          ))}
        </div>

        {/* Footer note */}
        <div className="mt-12 text-center text-xs text-slate-400 pb-6">
          <p>
            This is a demo storefront for{" "}
            <span className="font-semibold text-indigo-600">SmartMail AI+</span>.
            All interactions are tracked for the recommendation engine.
          </p>
        </div>
      </main>

      {/* Toast */}
      <Toast message={toastMsg} visible={toastVisible} />
    </div>
  );
}
