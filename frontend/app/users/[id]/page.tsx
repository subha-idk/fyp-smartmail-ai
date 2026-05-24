import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  Activity,
  ShoppingBag,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Award,
  Clock,
  Tag,
  Eye,
} from "lucide-react";
import { fetchUserProfile, fetchRecommendations } from "@/lib/api";
import SendEmailButton from "@/components/SendEmailButton";
import EngagementBadge from "@/components/EngagementBadge";

interface UserDetailPageProps {
  params: { id: string };
}

// ── Circular Progress Ring ─────────────────────────────────────────
function CircularProgress({
  value,
  size = 120,
  strokeWidth = 10,
  color,
  label,
  sublabel,
}: {
  value: number | null;
  size?: number;
  strokeWidth?: number;
  color: string;
  label: string;
  sublabel: string;
}) {
  const pct = value !== null && value !== undefined ? Math.round(value * 100) : null;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset =
    pct !== null
      ? circumference - (pct / 100) * circumference
      : circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="-rotate-90"
          aria-label={`${label}: ${pct ?? "N/A"}%`}
        >
          {/* Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(30,41,59,0.8)"
            strokeWidth={strokeWidth}
          />
          {/* Fill */}
          {pct !== null && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              style={{ transition: "stroke-dashoffset 0.6s ease" }}
            />
          )}
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className="font-bold tracking-tight text-slate-100"
            style={{ fontSize: size > 100 ? "1.5rem" : "1.125rem" }}
          >
            {pct !== null ? `${pct}%` : "N/A"}
          </span>
        </div>
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-slate-200">{label}</p>
        <p className="text-xs text-slate-500 mt-0.5">{sublabel}</p>
      </div>
    </div>
  );
}

// ── Glass Stat Item ────────────────────────────────────────────────
function StatItem({
  label,
  value,
  icon: Icon,
  iconColor = "text-slate-500",
}: {
  label: string;
  value: React.ReactNode;
  icon: React.ElementType;
  iconColor?: string;
}) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <div className="flex items-center gap-1.5">
        <Icon className={`h-4 w-4 shrink-0 ${iconColor}`} />
        <span className="text-base font-semibold text-slate-100">{value}</span>
      </div>
    </div>
  );
}

// ── Glass Card wrapper ────────────────────────────────────────────
function GlassCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl ${className}`}
      style={{
        background: "rgba(15,23,41,0.8)",
        border: "1px solid rgba(99,102,241,0.15)",
        backdropFilter: "blur(12px)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
      }}
    >
      {children}
    </div>
  );
}

export default async function UserDetailPage({ params }: UserDetailPageProps) {
  const { id } = params;

  const [profile, recommendations] = await Promise.all([
    fetchUserProfile(id),
    fetchRecommendations(id, 3),
  ]);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    try {
      return new Date(dateStr).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "—";
    }
  };

  const categoryColors = [
    "bg-indigo-500/15 text-indigo-400 border-indigo-500/30",
    "bg-violet-500/15 text-violet-400 border-violet-500/30",
    "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    "bg-amber-500/15 text-amber-400 border-amber-500/30",
    "bg-red-500/15 text-red-400 border-red-500/30",
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Back link + title */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <Link
            href="/users"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-indigo-400 transition-colors duration-200 cursor-pointer"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Users
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Customer Profile
          </h1>
          <p className="text-xs text-slate-600 font-mono">uid: {profile.user_id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* ── Left / Main Column ───────────────────────── */}
        <div className="space-y-8 lg:col-span-2">

          {/* Profile Stats Card */}
          <GlassCard>
            <div className="px-6 py-4 border-b border-[rgba(99,102,241,0.1)]">
              <h2 className="text-lg font-semibold text-slate-200">
                Analytical Profile Metrics
              </h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Summary of user interactions, spends, and categories.
              </p>
            </div>
            <div className="p-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
              <div className="space-y-1.5">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Engagement Score
                </p>
                <EngagementBadge score={profile.engagement_score} />
              </div>
              <StatItem
                label="Total Events"
                value={profile.total_events.toLocaleString()}
                icon={Activity}
                iconColor="text-indigo-400"
              />
              <StatItem
                label="Total Purchases"
                value={profile.total_purchases.toLocaleString()}
                icon={ShoppingBag}
                iconColor="text-emerald-400"
              />
              <StatItem
                label="Total Spend"
                value={`$${profile.total_spend.toFixed(2)}`}
                icon={DollarSign}
                iconColor="text-emerald-400"
              />
              <StatItem
                label="Days Since Purchase"
                value={
                  profile.days_since_last_purchase !== null
                    ? `${profile.days_since_last_purchase}d`
                    : "Never"
                }
                icon={Clock}
                iconColor="text-slate-500"
              />
              <StatItem
                label="Last Active"
                value={
                  <span className="text-sm">{formatDate(profile.last_active_at)}</span>
                }
                icon={Calendar}
                iconColor="text-slate-500"
              />
              <StatItem
                label="RFM Recency"
                value={profile.rfm_recency !== null ? `${profile.rfm_recency}d` : "N/A"}
                icon={Clock}
                iconColor="text-slate-600"
              />
              <StatItem
                label="RFM Frequency"
                value={profile.rfm_frequency !== null ? `${profile.rfm_frequency} orders` : "N/A"}
                icon={Activity}
                iconColor="text-slate-600"
              />
              <StatItem
                label="RFM Monetary"
                value={profile.rfm_monetary !== null ? `$${profile.rfm_monetary.toFixed(2)}` : "N/A"}
                icon={DollarSign}
                iconColor="text-slate-600"
              />
              {/* Categories */}
              <div className="sm:col-span-2 space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Preferred Categories
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {profile.preferred_categories && profile.preferred_categories.length > 0 ? (
                    profile.preferred_categories.map((cat, idx) => (
                      <span
                        key={cat}
                        className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-0.5 rounded-full border ${
                          categoryColors[idx % categoryColors.length]
                        }`}
                      >
                        <Tag className="h-2.5 w-2.5" />
                        {cat}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-600">No categories preferred</span>
                  )}
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Profile Refreshed
                </p>
                <p className="text-xs text-slate-600 font-mono">
                  {formatDate(profile.updated_at)}
                </p>
              </div>
            </div>
          </GlassCard>

          {/* ML Scores: Two circular progress rings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <GlassCard className="p-6 flex flex-col items-center gap-4">
              <div className="text-center">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 justify-center">
                  <AlertTriangle className="h-4 w-4 text-red-400" />
                  Churn Risk Score
                </h3>
                <p className="text-xs text-slate-600 mt-0.5">
                  Random Forest model prediction
                </p>
              </div>
              <CircularProgress
                value={profile.churn_risk}
                color="#ef4444"
                label={
                  profile.churn_risk === null
                    ? "Incomplete data"
                    : profile.churn_risk >= 0.7
                    ? "CRITICAL RISK"
                    : profile.churn_risk >= 0.4
                    ? "MODERATE RISK"
                    : "LOW RISK"
                }
                sublabel="Churn probability"
              />
            </GlassCard>

            <GlassCard className="p-6 flex flex-col items-center gap-4">
              <div className="text-center">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 justify-center">
                  <TrendingUp className="h-4 w-4 text-emerald-400" />
                  Purchase Probability
                </h3>
                <p className="text-xs text-slate-600 mt-0.5">
                  Logistic Regression (7-day intent)
                </p>
              </div>
              <CircularProgress
                value={profile.purchase_probability}
                color="#10b981"
                label={
                  profile.purchase_probability === null
                    ? "Incomplete data"
                    : profile.purchase_probability >= 0.6
                    ? "HIGH INTENT"
                    : profile.purchase_probability >= 0.3
                    ? "MODERATE INTENT"
                    : "LOW INTENT"
                }
                sublabel="Purchase likelihood"
              />
            </GlassCard>
          </div>

          {/* Product Recommendations */}
          <div>
            <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
              <Award className="h-5 w-5 text-indigo-400" />
              Personalized Recommendations
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {recommendations && recommendations.length > 0 ? (
                recommendations.map((prod) => (
                  <GlassCard key={prod.id} className="p-4 hover:border-[rgba(99,102,241,0.35)] cursor-pointer transition-all duration-200">
                    {/* Category badge */}
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-3">
                      <Tag className="h-2.5 w-2.5" />
                      {prod.category}
                    </span>
                    <h4 className="text-sm font-semibold text-slate-100 truncate mb-1">
                      {prod.name}
                    </h4>
                    <p className="text-lg font-bold text-slate-100 mb-1">
                      ${prod.price.toFixed(2)}
                    </p>
                    <div className="flex items-center gap-1.5 text-xs">
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          prod.stock > 0 ? "bg-emerald-400" : "bg-red-400"
                        }`}
                      />
                      <span className="text-slate-500">
                        {prod.stock > 0 ? `${prod.stock} in stock` : "Out of stock"}
                      </span>
                    </div>
                  </GlassCard>
                ))
              ) : (
                <div className="md:col-span-3 flex flex-col items-center justify-center p-10 rounded-xl border border-[rgba(99,102,241,0.1)] text-slate-500 bg-[rgba(15,23,41,0.4)]">
                  <Award className="h-8 w-8 text-slate-700 mb-2" />
                  <p className="text-sm">No recommendations generated.</p>
                  <p className="text-xs text-slate-700 mt-1">
                    Ensure active events and seed inventory are loaded.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Right Column ────────────────────────────────── */}
        <div className="space-y-6">
          {/* Campaign Manager */}
          <GlassCard>
            <div className="px-5 py-4 border-b border-[rgba(99,102,241,0.1)]">
              <h3 className="text-sm font-semibold text-slate-200">
                Campaign Manager
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Manually trigger agentic campaign evaluation.
              </p>
            </div>
            <div className="p-5 space-y-4">
              <div className="text-xs text-slate-500 space-y-2 leading-relaxed">
                <p>
                  Clicking the button will run the Decision Engine to choose the
                  best email strategy (retention, abandoned cart, recommendation,
                  upsell, or review request).
                </p>
                <p>
                  It evaluates recommendations, calls the Gemini model to write
                  personalized copy, injects tracking pixels, and dispatches the email.
                </p>
              </div>
              <SendEmailButton userId={id} />
            </div>
          </GlassCard>

          {/* Top Viewed Products */}
          <GlassCard>
            <div className="px-5 py-3 border-b border-[rgba(99,102,241,0.1)]">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Eye className="h-3.5 w-3.5" />
                Top Viewed Products
              </h3>
            </div>
            <div className="p-5 space-y-2">
              {profile.top_viewed_products && profile.top_viewed_products.length > 0 ? (
                profile.top_viewed_products.map((pId, idx) => (
                  <div
                    key={pId}
                    className="flex items-center gap-2 text-xs truncate py-1"
                  >
                    <span className="font-semibold text-indigo-500 w-5">
                      #{idx + 1}
                    </span>
                    <span className="text-slate-400 truncate font-mono">{pId}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-600">No views registered yet.</p>
              )}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
