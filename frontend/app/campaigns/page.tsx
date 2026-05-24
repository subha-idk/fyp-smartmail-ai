"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, Mail } from "lucide-react";
import { fetchEmailLogs, type EmailLog } from "@/lib/api";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

// ── Relative time helper ─────────────────────────────────────────
function relativeTime(tsStr: string | null): string {
  if (!tsStr) return "—";
  try {
    const diff = Date.now() - new Date(tsStr).getTime();
    const secs = Math.floor(diff / 1000);
    if (secs < 60) return `${secs}s ago`;
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    return new Date(tsStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  } catch {
    return "—";
  }
}

// ── Status badge ─────────────────────────────────────────────────
function StatusPill({ status }: { status: string }) {
  const norm = status.toLowerCase();
  const styles: Record<string, string> = {
    opened:
      "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    clicked:
      "bg-violet-500/15 text-violet-400 border-violet-500/30",
    failed:
      "bg-red-500/15 text-red-400 border-red-500/30",
    bounced:
      "bg-red-500/15 text-red-400 border-red-500/30",
  };
  const cls =
    styles[norm] ?? "bg-indigo-500/15 text-indigo-400 border-indigo-500/30";

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border uppercase tracking-wide ${cls}`}
    >
      {status}
    </span>
  );
}

// ── Email type badge ─────────────────────────────────────────────
function TypeBadge({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-700/50 text-slate-300 border border-slate-600/40 capitalize">
      {type.replace(/_/g, " ")}
    </span>
  );
}

export default function CampaignsPage() {
  const [logs, setLogs] = React.useState<EmailLog[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);
  const limit = 20;

  React.useEffect(() => {
    let active = true;
    const loadLogs = async () => {
      setLoading(true);
      try {
        const res = await fetchEmailLogs(page, limit);
        if (active) {
          setLogs(res.logs);
          setTotal(res.total);
        }
      } catch (err) {
        console.error("Failed to load email logs:", err);
      } finally {
        if (active) setLoading(false);
      }
    };
    loadLogs();
    return () => { active = false; };
  }, [page]);

  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Title */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">
          Campaign Dispatches
        </h1>
        <p className="text-sm text-slate-500">
          Review automatic and manual customer email dispatches including
          tracking stats.
        </p>
      </div>

      {/* Table Card */}
      <div
        className="rounded-xl overflow-hidden"
        style={{
          background: "rgba(15,23,41,0.8)",
          border: "1px solid rgba(99,102,241,0.15)",
          backdropFilter: "blur(12px)",
          boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
        }}
      >
        {loading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-8 w-full" />
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 px-4">
            <Mail className="h-10 w-10 text-slate-700 mb-3" />
            <p className="text-sm font-medium text-slate-400">
              No campaigns sent yet
            </p>
            <p className="text-xs text-slate-600 mt-1">
              Trigger a campaign from the user detail page.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Sent</TableHead>
                <TableHead>Opened</TableHead>
                <TableHead>Clicked</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="text-slate-100 font-semibold text-sm">
                        {log.user_name || "N/A"}
                      </span>
                      <span className="text-xs text-slate-500">
                        {log.user_email}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <TypeBadge type={log.email_type} />
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    <span
                      title={log.subject ?? ""}
                      className="block truncate text-slate-300 text-sm italic"
                    >
                      {log.subject || "—"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <StatusPill status={log.status} />
                  </TableCell>
                  <TableCell className="text-slate-500 text-xs whitespace-nowrap">
                    {relativeTime(log.sent_at)}
                  </TableCell>
                  <TableCell className="text-slate-500 text-xs whitespace-nowrap">
                    {relativeTime(log.opened_at)}
                  </TableCell>
                  <TableCell className="text-slate-500 text-xs whitespace-nowrap">
                    {relativeTime(log.clicked_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Pagination */}
      {!loading && logs.length > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-500">
            Page {page} of {totalPages} &mdash; {total} total logs
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => page > 1 && setPage(page - 1)}
              disabled={page === 1}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer transition-all duration-200
                border border-[rgba(99,102,241,0.2)] text-slate-400
                hover:bg-[rgba(99,102,241,0.08)] hover:text-slate-200 hover:border-[rgba(99,102,241,0.4)]
                disabled:opacity-30 disabled:pointer-events-none"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Previous
            </button>
            <button
              onClick={() => page < totalPages && setPage(page + 1)}
              disabled={page === totalPages}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer transition-all duration-200
                border border-[rgba(99,102,241,0.2)] text-slate-400
                hover:bg-[rgba(99,102,241,0.08)] hover:text-slate-200 hover:border-[rgba(99,102,241,0.4)]
                disabled:opacity-30 disabled:pointer-events-none"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
