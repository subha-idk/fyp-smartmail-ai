import { fetchSummary, fetchEventSeries } from "@/lib/api";
import OverviewChart from "@/components/OverviewChart";
import {
  Users,
  BarChart3,
  Mail,
  TrendingUp,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

export const revalidate = 60;

// Hardcoded delta values for demonstration (in production, compare time periods)
const DELTAS: Record<string, { value: number; positive: boolean }> = {
  users:      { value: 12.4, positive: true },
  engagement: { value: 3.1,  positive: true },
  emails:     { value: 8.7,  positive: true },
  conversion: { value: 1.2,  positive: false },
};

// Each KPI card is a Server Component — using pure CSS hover via Tailwind
function KpiCard({
  title,
  value,
  subtext,
  icon: Icon,
  iconBg,
  iconColor,
  deltaKey,
}: {
  title: string;
  value: string;
  subtext: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  deltaKey: string;
}) {
  const delta = DELTAS[deltaKey];
  return (
    <div className="kpi-glass-card rounded-xl p-6 flex flex-col gap-4 transition-all duration-200">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </p>
        <span
          className="flex h-9 w-9 items-center justify-center rounded-lg"
          style={{ background: iconBg }}
        >
          <Icon className={`h-4 w-4 ${iconColor}`} />
        </span>
      </div>
      <div>
        <p
          className="font-bold tracking-tight text-slate-100"
          style={{ fontSize: "2.5rem", lineHeight: 1.1 }}
        >
          {value}
        </p>
        <p className="text-xs text-slate-500 mt-1">{subtext}</p>
      </div>
      {delta && (
        <div className="flex items-center gap-1">
          {delta.positive ? (
            <ArrowUpRight className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <ArrowDownRight className="h-3.5 w-3.5 text-red-400" />
          )}
          <span
            className={`text-xs font-semibold ${
              delta.positive ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {delta.value}%
          </span>
          <span className="text-xs text-slate-600">&nbsp;vs last period</span>
        </div>
      )}
    </div>
  );
}

export default async function DashboardPage() {
  let summary, series;
  try {
    summary = await fetchSummary();
    series = await fetchEventSeries(30);
  } catch {
    return (
      <div className="space-y-6 animate-fade-in">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Dashboard Overview
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Monitor your customer engagement, predictions, and campaigns.
          </p>
        </div>
        <div
          className="rounded-xl p-6 flex items-center gap-4"
          style={{
            background: "rgba(245,158,11,0.08)",
            border: "1px solid rgba(245,158,11,0.25)",
            backdropFilter: "blur(12px)",
          }}
        >
          <AlertTriangle className="h-6 w-6 text-amber-400 shrink-0" />
          <div>
            <h3 className="font-semibold text-slate-100">Backend Server Offline</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              The dashboard could not connect to the API server. Please ensure
              the backend is running.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">
          Dashboard Overview
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Monitor your customer engagement, predictions, and campaigns in
          real-time.
        </p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Users"
          value={summary.total_users.toLocaleString()}
          subtext="Active customers in database"
          icon={Users}
          iconBg="rgba(99,102,241,0.15)"
          iconColor="text-indigo-400"
          deltaKey="users"
        />
        <KpiCard
          title="Avg Engagement"
          value={`${summary.avg_engagement_score}%`}
          subtext="Scale of 0–100 across profiles"
          icon={BarChart3}
          iconBg="rgba(16,185,129,0.15)"
          iconColor="text-emerald-400"
          deltaKey="engagement"
        />
        <KpiCard
          title="Emails Sent"
          value={summary.total_emails.toLocaleString()}
          subtext="Campaign deliveries total"
          icon={Mail}
          iconBg="rgba(139,92,246,0.15)"
          iconColor="text-violet-400"
          deltaKey="emails"
        />
        <KpiCard
          title="Conversion Rate"
          value={`${(summary.conversion_rate * 100).toFixed(1)}%`}
          subtext="Purchase events / total users"
          icon={TrendingUp}
          iconBg="rgba(245,158,11,0.15)"
          iconColor="text-amber-400"
          deltaKey="conversion"
        />
      </div>

      {/* Area Chart Card */}
      <div className="chart-glass-card rounded-xl p-6 transition-all duration-200">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-200">
            Daily Event Volume
          </h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Total event ingestion counts over the last 30 days.
          </p>
        </div>
        <OverviewChart data={series} />
      </div>
    </div>
  );
}
