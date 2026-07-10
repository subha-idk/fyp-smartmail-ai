"use client";

import * as React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

interface AnalyticsChartsProps {
  summary: {
    emails_sent: number;
    emails_opened: number;
    emails_clicked: number;
    emails_failed: number;
    total_emails: number;
  };
  eventSeries: {
    views: Array<{ date: string; count: number }>;
    carts: Array<{ date: string; count: number }>;
    purchases: Array<{ date: string; count: number }>;
  };
}

const TOOLTIP_STYLE = {
  backgroundColor: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "4px",
  boxShadow: "var(--card-shadow)",
  color: "var(--color-text)",
  fontSize: "11px",
};

const LABEL_STYLE = { color: "var(--color-text)", fontWeight: 700 };

const CHART_COLORS = {
  views: "#0060ff",      // Zoho Blue
  carts: "#fb641b",      // Flipkart Orange / Warm Accent
  purchases: "#10b981",  // Success Emerald
  sent: "#3b82f6",
  opened: "#10b981",
  clicked: "#8b5cf6",
  failed: "#ef4444",
};

export default function AnalyticsCharts({
  summary,
  eventSeries,
}: AnalyticsChartsProps) {
  const mergedLineData = React.useMemo(() => {
    const datesMap: Record<
      string,
      { date: string; views: number; carts: number; purchases: number }
    > = {};

    const initializeDate = (dStr: string) => {
      if (!datesMap[dStr]) {
        datesMap[dStr] = { date: dStr, views: 0, carts: 0, purchases: 0 };
      }
    };

    eventSeries.views.forEach((p) => {
      initializeDate(p.date);
      datesMap[p.date].views = p.count;
    });

    eventSeries.carts.forEach((p) => {
      initializeDate(p.date);
      datesMap[p.date].carts = p.count;
    });

    eventSeries.purchases.forEach((p) => {
      initializeDate(p.date);
      datesMap[p.date].purchases = p.count;
    });

    return Object.values(datesMap)
      .map((d) => {
        try {
          const dateObj = new Date(d.date);
          return {
            ...d,
            formattedDate: dateObj.toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            }),
          };
        } catch (e) {
          return { ...d, formattedDate: d.date };
        }
      })
      .sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
      );
  }, [eventSeries]);

  const barChartData = React.useMemo(
    () => [
      { name: "Sent", count: summary.emails_sent, color: CHART_COLORS.sent },
      {
        name: "Opened",
        count: summary.emails_opened,
        color: CHART_COLORS.opened,
      },
      {
        name: "Clicked",
        count: summary.emails_clicked,
        color: CHART_COLORS.clicked,
      },
      {
        name: "Failed",
        count: summary.emails_failed,
        color: CHART_COLORS.failed,
      },
    ],
    [summary]
  );

  const renderCustomLegend = (props: any) => {
    const { payload } = props;
    return (
      <div className="flex flex-wrap gap-4 justify-center mb-2">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-1.5 text-xs font-semibold">
            <span
              className="inline-block h-2 w-3 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-[var(--color-muted)]">{entry.value}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      {/* Event Volume Line Chart */}
      <div className="zoho-card">
        <div className="px-5 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg)] rounded-t-[5px]">
          <h3 className="text-sm font-bold text-[var(--color-text)]">
            Funnel Event Volumes
          </h3>
          <p className="text-xs text-[var(--color-muted)] mt-0.5">
            Daily breakdown of product views, cart additions, and purchases.
          </p>
        </div>
        
        <div className="p-5">
          <div className="h-80 w-full">
            {mergedLineData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-xs text-[var(--color-muted)]">
                No event history available.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={mergedLineData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke="var(--color-border)"
                  />
                  <XAxis
                    dataKey="formattedDate"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "var(--color-muted)", fontSize: 10 }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "var(--color-muted)", fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    labelStyle={LABEL_STYLE}
                    cursor={{ stroke: "var(--color-primary)", strokeOpacity: 0.15, strokeWidth: 1 }}
                  />
                  <Legend content={renderCustomLegend} />
                  <Line
                    type="monotone"
                    dataKey="views"
                    stroke={CHART_COLORS.views}
                    strokeWidth={2}
                    dot={{ r: 3, stroke: CHART_COLORS.views, strokeWidth: 1.5, fill: "var(--color-surface)" }}
                    name="Product Views"
                  />
                  <Line
                    type="monotone"
                    dataKey="carts"
                    stroke={CHART_COLORS.carts}
                    strokeWidth={2}
                    dot={{ r: 3, stroke: CHART_COLORS.carts, strokeWidth: 1.5, fill: "var(--color-surface)" }}
                    name="Cart Adds"
                  />
                  <Line
                    type="monotone"
                    dataKey="purchases"
                    stroke={CHART_COLORS.purchases}
                    strokeWidth={2}
                    dot={{ r: 3, stroke: CHART_COLORS.purchases, strokeWidth: 1.5, fill: "var(--color-surface)" }}
                    name="Purchases"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Email Delivery Bar Chart */}
      <div className="zoho-card">
        <div className="px-5 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg)] rounded-t-[5px]">
          <h3 className="text-sm font-bold text-[var(--color-text)]">
            Email Delivery Outcomes
          </h3>
          <p className="text-xs text-[var(--color-muted)] mt-0.5">
            Distribution of campaign outcomes across all generated emails.
          </p>
        </div>
        
        <div className="p-5">
          <div className="h-80 w-full">
            {summary.total_emails === 0 ? (
              <div className="flex h-full items-center justify-center text-xs text-[var(--color-muted)]">
                No emails dispatched yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={barChartData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke="var(--color-border)"
                  />
                  <XAxis
                    dataKey="name"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "var(--color-muted)", fontSize: 10 }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "var(--color-muted)", fontSize: 10 }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={{ fill: "var(--color-primary)", fillOpacity: 0.04 }}
                    contentStyle={TOOLTIP_STYLE}
                    labelStyle={LABEL_STYLE}
                  />
                  <Bar dataKey="count" radius={[2, 2, 0, 0]} barSize={36}>
                    {barChartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.color}
                        fillOpacity={0.85}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
      
    </div>
  );
}
