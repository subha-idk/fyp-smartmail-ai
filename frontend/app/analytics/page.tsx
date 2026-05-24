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
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Analytics &amp; Performance
          </h1>
          <p className="text-sm text-slate-500">
            Analyze customer funnel conversions and monitor campaign dispatch
            statuses.
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
            <h3 className="font-semibold text-slate-100">
              Backend Server Offline
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              The analytics dashboard could not connect to the API server.
              Please ensure the backend is running.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">
          Analytics &amp; Performance
        </h1>
        <p className="text-sm text-slate-500">
          Analyze customer funnel conversions and monitor campaign dispatch
          statuses.
        </p>
      </div>
      <AnalyticsCharts
        summary={summary}
        eventSeries={{ views, carts, purchases }}
      />
    </div>
  );
}
