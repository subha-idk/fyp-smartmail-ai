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

// ── Elegant Circular Progress Ring (Zoho style) ───────────────────
function CircularProgress({
  value,
  size = 110,
  strokeWidth = 6,
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
    <div className="flex flex-col items-center gap-3">
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
            stroke="var(--color-border)"
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
            className="font-extrabold tracking-tight text-[var(--color-text)]"
            style={{ fontSize: "1.35rem" }}
          >
            {pct !== null ? `${pct}%` : "N/A"}
          </span>
        </div>
      </div>
      <div className="text-center">
        <p className="text-xs font-bold text-[var(--color-text)] uppercase tracking-wider">{label}</p>
        <p className="text-[11px] text-[var(--color-muted)] mt-0.5">{sublabel}</p>
      </div>
    </div>
  );
}

// ── Zoho Stat Item ────────────────────────────────────────────────
function StatItem({
  label,
  value,
  icon: Icon,
  iconColor = "text-[var(--color-muted)]",
}: {
  label: string;
  value: React.ReactNode;
  icon: React.ElementType;
  iconColor?: string;
}) {
  return (
    <div className="space-y-1 p-3 rounded bg-[var(--color-bg)] border border-[var(--color-border)]">
      <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-muted)]">
        {label}
      </p>
      <div className="flex items-center gap-2">
        <Icon className={`h-4 w-4 shrink-0 ${iconColor}`} />
        <span className="text-sm font-bold text-[var(--color-text)]">{value}</span>
      </div>
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
    "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
    "bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20",
    "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back link + title */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b border-[var(--color-border)] pb-4">
        <div className="space-y-1">
          <Link
            href="/users"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--color-primary)] hover:underline transition-colors duration-200 cursor-pointer"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Users List
          </Link>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text)]">
            Customer Profile
          </h1>
          <p className="text-[10px] text-[var(--color-muted)] font-mono">UID: {profile.user_id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* ── Left / Main Column ───────────────────────── */}
        <div className="space-y-6 lg:col-span-2">

          {/* Profile Stats Card */}
          <div className="zoho-card">
            <div className="px-5 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg)] rounded-t-[5px]">
              <h2 className="text-sm font-bold text-[var(--color-text)]">
                Analytical Profile Metrics
              </h2>
              <p className="text-xs text-[var(--color-muted)] mt-0.5">
                Summary of user interactions, spend, and categories.
              </p>
            </div>
            
            <div className="p-5 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <div className="space-y-1 p-3 rounded bg-[var(--color-bg)] border border-[var(--color-border)] flex flex-col justify-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-muted)] mb-1">
                  Engagement Tier
                </p>
                <EngagementBadge score={profile.engagement_score} />
              </div>
              <StatItem
                label="Total Events"
                value={profile.total_events.toLocaleString()}
                icon={Activity}
                iconColor="text-blue-500"
              />
              <StatItem
                label="Total Purchases"
                value={profile.total_purchases.toLocaleString()}
                icon={ShoppingBag}
                iconColor="text-emerald-500"
              />
              <StatItem
                label="Total Spend"
                value={`₹${Math.round(profile.total_spend * 80).toLocaleString("en-IN")}`}
                icon={DollarSign}
                iconColor="text-emerald-500"
              />
              <StatItem
                label="Days Since Purchase"
                value={
                  profile.days_since_last_purchase !== null
                    ? `${profile.days_since_last_purchase}d`
                    : "Never"
                }
                icon={Clock}
                iconColor="text-[var(--color-muted)]"
              />
              <StatItem
                label="Last Active"
                value={
                  <span className="text-xs">{formatDate(profile.last_active_at)}</span>
                }
                icon={Calendar}
                iconColor="text-[var(--color-muted)]"
              />
              <StatItem
                label="RFM Recency"
                value={profile.rfm_recency !== null ? `${profile.rfm_recency}d` : "N/A"}
                icon={Clock}
                iconColor="text-slate-400"
              />
              <StatItem
                label="RFM Frequency"
                value={profile.rfm_frequency !== null ? `${profile.rfm_frequency} orders` : "N/A"}
                icon={Activity}
                iconColor="text-slate-400"
              />
              <StatItem
                label="RFM Monetary"
                value={profile.rfm_monetary !== null ? `₹${Math.round(profile.rfm_monetary * 80).toLocaleString("en-IN")}` : "N/A"}
                icon={DollarSign}
                iconColor="text-slate-400"
              />
              
              {/* Categories */}
              <div className="sm:col-span-2 space-y-2 p-3 rounded bg-[var(--color-bg)] border border-[var(--color-border)]">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-muted)]">
                  Preferred Categories
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {profile.preferred_categories && profile.preferred_categories.length > 0 ? (
                    profile.preferred_categories.map((cat, idx) => (
                      <span
                        key={cat}
                        className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded border ${
                          categoryColors[idx % categoryColors.length]
                        }`}
                      >
                        <Tag className="h-2.5 w-2.5" />
                        {cat}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-[var(--color-muted)]">No categories preferred</span>
                  )}
                </div>
              </div>
              
              <div className="space-y-1 p-3 rounded bg-[var(--color-bg)] border border-[var(--color-border)]">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-muted)]">
                  Profile Refreshed
                </p>
                <p className="text-xs text-[var(--color-text)] font-mono">
                  {formatDate(profile.updated_at)}
                </p>
              </div>
            </div>
          </div>

          {/* ML Predictions Card Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="zoho-card p-6 flex flex-col items-center gap-4">
              <div className="text-center">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text)] flex items-center gap-1.5 justify-center">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  Churn Risk Prediction
                </h3>
                <p className="text-[10px] text-[var(--color-muted)] mt-0.5">
                  Random Forest classification prediction
                </p>
              </div>
              <CircularProgress
                value={profile.churn_risk}
                color="var(--color-danger)"
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
            </div>

            <div className="zoho-card p-6 flex flex-col items-center gap-4">
              <div className="text-center">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text)] flex items-center gap-1.5 justify-center">
                  <TrendingUp className="h-4 w-4 text-emerald-500" />
                  7-Day Purchase Intent
                </h3>
                <p className="text-[10px] text-[var(--color-muted)] mt-0.5">
                  Logistic Regression probability score
                </p>
              </div>
              <CircularProgress
                value={profile.purchase_probability}
                color="var(--color-success)"
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
            </div>
          </div>

          {/* Product Recommendations */}
          <div>
            <h3 className="text-sm font-bold text-[var(--color-text)] uppercase tracking-wider mb-3 flex items-center gap-2">
              <Award className="h-4 w-4 text-[var(--color-primary)]" />
              Personalized Recommendations
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {recommendations && recommendations.length > 0 ? (
                recommendations.map((prod) => (
                  <div key={prod.id} className="zoho-card p-4 hover:border-[var(--color-primary)] transition-all duration-200">
                    <span className="inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[var(--color-primary)]/10 text-[var(--color-primary)] border border-[var(--color-primary)]/20 mb-3">
                      <Tag className="h-2.5 w-2.5" />
                      {prod.category}
                    </span>
                    <h4 className="text-xs font-semibold text-[var(--color-text)] truncate mb-1" title={prod.name}>
                      {prod.name}
                    </h4>
                    <p className="text-base font-extrabold text-[var(--color-text)] mb-2">
                      ₹{Math.round(prod.price * 80).toLocaleString("en-IN")}
                    </p>
                    <div className="flex items-center gap-1.5 text-xs">
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          prod.stock > 0 ? "bg-emerald-500" : "bg-red-500"
                        }`}
                      />
                      <span className="text-[var(--color-muted)] text-[11px]">
                        {prod.stock > 0 ? `${prod.stock} in stock` : "Out of stock"}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="md:col-span-3 flex flex-col items-center justify-center p-8 zoho-card text-[var(--color-muted)] text-center">
                  <Award className="h-8 w-8 text-slate-400 mb-2" />
                  <p className="text-sm font-semibold">No recommendations generated.</p>
                  <p className="text-xs mt-1">
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
          <div className="zoho-card">
            <div className="px-5 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg)] rounded-t-[5px]">
              <h3 className="text-sm font-bold text-[var(--color-text)]">
                Campaign Manager
              </h3>
              <p className="text-xs text-[var(--color-muted)] mt-0.5">
                Manually trigger agentic campaign evaluation.
              </p>
            </div>
            <div className="p-5 space-y-4">
              <div className="text-xs text-[var(--color-muted)] space-y-2 leading-relaxed">
                <p>
                  Clicking the button below executes the Campaign Decision Engine. It analyzes the customer profile metrics to pick the optimum strategy (Upsell, Abandoned Cart, Retention, etc.).
                </p>
                <p>
                  It renders a custom marketing email template, performs currency formatting, and dispatches the email.
                </p>
              </div>
              <SendEmailButton userId={id} />
            </div>
          </div>

          {/* Top Viewed Products */}
          <div className="zoho-card">
            <div className="px-5 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg)] rounded-t-[5px]">
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text)] flex items-center gap-1.5">
                <Eye className="h-3.5 w-3.5 text-blue-500" />
                Top Viewed Products
              </h3>
            </div>
            <div className="p-5 space-y-2.5">
              {profile.top_viewed_products && profile.top_viewed_products.length > 0 ? (
                profile.top_viewed_products.map((pId, idx) => (
                  <div
                    key={pId}
                    className="flex items-center gap-2 text-xs truncate py-1 border-b border-[var(--color-border)] last:border-0 pb-1.5 last:pb-0"
                  >
                    <span className="font-bold text-[var(--color-primary)] w-5 shrink-0">
                      #{idx + 1}
                    </span>
                    <span className="text-[var(--color-muted)] truncate font-mono text-[11px]">{pId}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-[var(--color-muted)] italic">No views registered yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
