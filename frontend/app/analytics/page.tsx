import { fetchSummary, fetchEventSeries } from "@/lib/api";
import AnalyticsCharts from "@/components/AnalyticsCharts";
import { AlertTriangle } from "lucide-react";

export const revalidate = 60;

export default async function AnalyticsPage() {
  let summary, views, carts, purchases;
  try {
    const res = await Promise.all([
      fetchSummary(),
      fetchEventSeries(30, "product_view"),
      fetchEventSeries(30, "cart_add"),
      fetchEventSeries(30, "purchase"),
    ]);
    summary = res[0];
    views = res[1];
    carts = res[2];
    purchases = res[3];
  } catch {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text)]">
            Analytics &amp; Performance
          </h1>
          <p className="text-xs text-[var(--color-muted)]">
            Analyze customer funnel conversions and monitor campaign dispatch statuses.
          </p>
        </div>
        <div className="zoho-card p-5 flex items-center gap-4 border-l-4 border-l-amber-500 bg-amber-500/5">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
          <div>
            <h3 className="font-bold text-[var(--color-text)] text-sm">
              Backend Server Offline
            </h3>
            <p className="text-xs text-[var(--color-muted)] mt-0.5">
              The analytics dashboard could not connect to the API server. Please ensure the backend is running.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col gap-1 border-b border-[var(--color-border)] pb-4">
        <h1 className="text-xl font-bold tracking-tight text-[var(--color-text)]">
          Analytics &amp; Performance
        </h1>
        <p className="text-xs text-[var(--color-muted)]">
          Analyze customer funnel conversions and monitor campaign dispatch statuses.
        </p>
      </div>
      <AnalyticsCharts
        summary={summary}
        eventSeries={{ views, carts, purchases }}
      />
    </div>
  );
}
