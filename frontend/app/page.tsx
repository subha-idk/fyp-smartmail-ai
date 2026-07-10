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

const DELTAS: Record<string, { value: number; positive: boolean }> = {
  users:      { value: 12.4, positive: true },
  engagement: { value: 3.1,  positive: true },
  emails:     { value: 8.7,  positive: true },
  conversion: { value: 1.2,  positive: false },
};

function KpiCard({
  title,
  value,
  subtext,
  icon: Icon,
  iconBg,
  iconColor,
  deltaKey,
  accentColor,
}: {
  title: string;
  value: string;
  subtext: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  deltaKey: string;
  accentColor: string;
}) {
  const delta = DELTAS[deltaKey];
  return (
    <div 
      className="zoho-card p-5 flex flex-col justify-between min-h-[140px] border-l-4"
      style={{ borderLeftColor: accentColor }}
    >
      <div>
        <div className="flex items-start justify-between mb-2">
          <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)]">
            {title}
          </p>
          <span
            className="flex h-7 w-7 items-center justify-center rounded"
            style={{ background: iconBg }}
          >
            <Icon className={`h-4 w-4 ${iconColor}`} />
          </span>
        </div>
        
        <p className="text-2xl font-extrabold tracking-tight text-[var(--color-text)]">
          {value}
        </p>
        <p className="text-xs text-[var(--color-muted)] mt-1">{subtext}</p>
      </div>

      {delta && (
        <div className="flex items-center gap-1 mt-3 pt-2 border-t border-[var(--color-border)]">
          {delta.positive ? (
            <ArrowUpRight className="h-3.5 w-3.5 text-emerald-500" />
          ) : (
            <ArrowDownRight className="h-3.5 w-3.5 text-red-500" />
          )}
          <span
            className={`text-xs font-bold ${
              delta.positive ? "text-emerald-500" : "text-red-500"
            }`}
          >
            {delta.value}%
          </span>
          <span className="text-[11px] text-[var(--color-muted)]">vs last period</span>
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
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text)]">
            Dashboard Overview
          </h1>
          <p className="text-xs text-[var(--color-muted)] mt-1">
            Monitor your customer engagement, predictions, and campaigns.
          </p>
        </div>
        <div className="zoho-card p-5 flex items-center gap-4 border-l-4 border-l-amber-500 bg-amber-500/5">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
          <div>
            <h3 className="font-bold text-[var(--color-text)] text-sm">Backend Server Offline</h3>
            <p className="text-xs text-[var(--color-muted)] mt-0.5">
              The dashboard could not connect to the API server. Please ensure the backend is running.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-[var(--color-text)]">
          Dashboard Overview
        </h1>
        <p className="text-xs text-[var(--color-muted)] mt-1">
          Monitor your customer engagement, predictions, and campaigns in real-time.
        </p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Users"
          value={summary.total_users.toLocaleString()}
          subtext="Active customers in database"
          icon={Users}
          iconBg="rgba(0, 96, 255, 0.1)"
          iconColor="text-[#0060ff]"
          deltaKey="users"
          accentColor="#0060ff"
        />
        <KpiCard
          title="Avg Engagement"
          value={`${summary.avg_engagement_score}%`}
          subtext="Scale of 0–100 across profiles"
          icon={BarChart3}
          iconBg="rgba(16, 185, 129, 0.1)"
          iconColor="text-emerald-500"
          deltaKey="engagement"
          accentColor="#10b981"
        />
        <KpiCard
          title="Emails Sent"
          value={summary.total_emails.toLocaleString()}
          subtext="Campaign deliveries total"
          icon={Mail}
          iconBg="rgba(139, 92, 246, 0.1)"
          iconColor="text-violet-500"
          deltaKey="emails"
          accentColor="#8b5cf6"
        />
        <KpiCard
          title="Conversion Rate"
          value={`${(summary.conversion_rate * 100).toFixed(1)}%`}
          subtext="Purchase events / total users"
          icon={TrendingUp}
          iconBg="rgba(245, 158, 11, 0.1)"
          iconColor="text-amber-500"
          deltaKey="conversion"
          accentColor="#f59e0b"
        />
      </div>

      {/* Area Chart Card */}
      <div className="zoho-card p-5">
        <div className="mb-4 border-b border-[var(--color-border)] pb-3">
          <h2 className="text-sm font-bold text-[var(--color-text)]">
            Daily Event Volume
          </h2>
          <p className="text-xs text-[var(--color-muted)] mt-0.5">
            Total event ingestion counts over the last 30 days.
          </p>
        </div>
        <div className="w-full overflow-hidden">
          <OverviewChart data={series} />
        </div>
      </div>
    </div>
  );
}
