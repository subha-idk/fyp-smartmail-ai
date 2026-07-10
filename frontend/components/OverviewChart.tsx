"use client";

import * as React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

interface OverviewChartProps {
  data: Array<{ date: string; count: number }>;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div 
        className="zoho-card p-3 shadow-md text-xs border"
        style={{ backgroundColor: "var(--color-surface)", borderColor: "var(--color-border)" }}
      >
        <p className="font-bold mb-1" style={{ color: "var(--color-text)" }}>{label}</p>
        <p style={{ color: "var(--color-primary)" }} className="font-medium">
          Events:{" "}
          <span className="font-bold" style={{ color: "var(--color-text)" }}>{payload[0].value}</span>
        </p>
      </div>
    );
  }
  return null;
};

export default function OverviewChart({ data }: OverviewChartProps) {
  const formattedData = React.useMemo(() => {
    return data.map((d) => {
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
    });
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center text-sm text-[var(--color-muted)]">
        No daily event data available.
      </div>
    );
  }

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={formattedData}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id="primaryGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.2} />
              <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            vertical={false}
            stroke="var(--color-border)"
          />
          <XAxis
            dataKey="formattedDate"
            tickLine={false}
            axisLine={false}
            stroke="var(--color-muted)"
            tick={{ fill: "var(--color-muted)", fontSize: 10 }}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            stroke="var(--color-muted)"
            tick={{ fill: "var(--color-muted)", fontSize: 10 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="count"
            stroke="var(--color-primary)"
            strokeWidth={2}
            fill="url(#primaryGradient)"
            dot={{ r: 3, stroke: "var(--color-primary)", strokeWidth: 1.5, fill: "var(--color-surface)" }}
            activeDot={{
              r: 5,
              stroke: "var(--color-primary)",
              strokeWidth: 2,
              fill: "var(--color-primary)",
            }}
            name="Daily Events"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
