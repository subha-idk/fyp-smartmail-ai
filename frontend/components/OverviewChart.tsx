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
      <div className="rounded-lg border border-[rgba(99,102,241,0.25)] bg-[rgba(10,15,30,0.95)] p-3 shadow-glass text-xs">
        <p className="font-semibold text-slate-200 mb-1">{label}</p>
        <p className="text-indigo-400">
          Events:{" "}
          <span className="font-bold text-slate-100">{payload[0].value}</span>
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
      <div className="flex h-72 items-center justify-center text-sm text-slate-500">
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
            <linearGradient id="indigoGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            vertical={false}
            stroke="#1e293b"
          />
          <XAxis
            dataKey="formattedDate"
            tickLine={false}
            axisLine={false}
            stroke="#475569"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            stroke="#475569"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#6366f1"
            strokeWidth={2}
            fill="url(#indigoGradient)"
            dot={{ r: 4, stroke: "#6366f1", strokeWidth: 2, fill: "#0f1729" }}
            activeDot={{
              r: 6,
              stroke: "#6366f1",
              strokeWidth: 2,
              fill: "#6366f1",
            }}
            name="Daily Events"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
