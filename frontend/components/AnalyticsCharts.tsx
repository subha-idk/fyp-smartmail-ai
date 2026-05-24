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
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

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

const DARK_TOOLTIP_STYLE = {
  backgroundColor: "rgba(10,15,30,0.95)",
  border: "1px solid rgba(99,102,241,0.25)",
  borderRadius: "0.5rem",
  boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
  color: "#f1f5f9",
  fontSize: "12px",
};

const LABEL_STYLE = { color: "#94a3b8", fontWeight: 600 };

const CHART_COLORS = {
  views: "#6366f1",
  carts: "#f59e0b",
  purchases: "#10b981",
  sent: "#6366f1",
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
      <div className="flex flex-wrap gap-3 justify-center mb-2">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-1.5 text-xs">
            <span
              className="inline-block h-2 w-4 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-slate-400">{entry.value}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Event Volume Line Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-slate-200">
            Funnel Event Volumes
          </CardTitle>
          <CardDescription>
            Daily breakdown of product views, cart additions, and purchases.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80 w-full">
            {mergedLineData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">
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
                    stroke="#1e293b"
                  />
                  <XAxis
                    dataKey="formattedDate"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                  />
                  <Tooltip
                    contentStyle={DARK_TOOLTIP_STYLE}
                    labelStyle={LABEL_STYLE}
                    cursor={{ stroke: "rgba(99,102,241,0.2)", strokeWidth: 1 }}
                  />
                  <Legend content={renderCustomLegend} />
                  <Line
                    type="monotone"
                    dataKey="views"
                    stroke={CHART_COLORS.views}
                    strokeWidth={2}
                    dot={{ r: 3, stroke: CHART_COLORS.views, strokeWidth: 1, fill: "#0f1729" }}
                    name="Product Views"
                  />
                  <Line
                    type="monotone"
                    dataKey="carts"
                    stroke={CHART_COLORS.carts}
                    strokeWidth={2}
                    dot={{ r: 3, stroke: CHART_COLORS.carts, strokeWidth: 1, fill: "#0f1729" }}
                    name="Cart Adds"
                  />
                  <Line
                    type="monotone"
                    dataKey="purchases"
                    stroke={CHART_COLORS.purchases}
                    strokeWidth={2}
                    dot={{ r: 3, stroke: CHART_COLORS.purchases, strokeWidth: 1, fill: "#0f1729" }}
                    name="Purchases"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Email Delivery Bar Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-slate-200">
            Email Delivery Outcomes
          </CardTitle>
          <CardDescription>
            Distribution of campaign outcomes across all generated emails.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80 w-full">
            {summary.total_emails === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">
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
                    stroke="#1e293b"
                  />
                  <XAxis
                    dataKey="name"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={{ fill: "rgba(99,102,241,0.06)" }}
                    contentStyle={DARK_TOOLTIP_STYLE}
                    labelStyle={LABEL_STYLE}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={40}>
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
        </CardContent>
      </Card>
    </div>
  );
}
