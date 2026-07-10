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
    opened: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    clicked: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
    failed: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
    bounced: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
  };
  
  const cls = styles[norm] ?? "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20";

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider ${cls}`}>
      {status}
    </span>
  );
}

// ── Email type badge ─────────────────────────────────────────────
function TypeBadge({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-[var(--color-bg)] text-[var(--color-text)] border border-[var(--color-border)] capitalize">
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
      <div className="flex flex-col gap-1 border-b border-[var(--color-border)] pb-4">
        <h1 className="text-xl font-bold tracking-tight text-[var(--color-text)]">
          Campaign Dispatches
        </h1>
        <p className="text-xs text-[var(--color-muted)]">
          Review automatic and manual customer email dispatches including tracking stats.
        </p>
      </div>

      {/* Table Card */}
      <div className="zoho-card overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-8 w-full bg-[var(--color-bg)]" />
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full bg-[var(--color-bg)]" />
            ))}
          </div>
        ) : logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 px-4">
            <Mail className="h-10 w-10 text-[var(--color-muted)] mb-3" />
            <p className="text-sm font-semibold text-[var(--color-text)]">
              No campaigns sent yet
            </p>
            <p className="text-xs text-[var(--color-muted)] mt-1">
              Trigger a campaign from the user detail page.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table className="zoho-table">
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
                  <TableRow key={log.id} className="hover:bg-[var(--color-accent)]">
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="text-[var(--color-text)] font-semibold text-sm">
                          {log.user_name || "N/A"}
                        </span>
                        <span className="text-[11px] text-[var(--color-muted)]">
                          {log.user_email}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <TypeBadge type={log.email_type} />
                    </TableCell>
                    <TableCell className="max-w-[240px]">
                      <span
                        title={log.subject ?? ""}
                        className="block truncate text-[var(--color-text)] text-xs font-medium italic"
                      >
                        {log.subject || "—"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StatusPill status={log.status} />
                    </TableCell>
                    <TableCell className="text-[var(--color-muted)] text-xs whitespace-nowrap">
                      {relativeTime(log.sent_at)}
                    </TableCell>
                    <TableCell className="text-[var(--color-muted)] text-xs whitespace-nowrap">
                      {relativeTime(log.opened_at)}
                    </TableCell>
                    <TableCell className="text-[var(--color-muted)] text-xs whitespace-nowrap">
                      {relativeTime(log.clicked_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {!loading && logs.length > 0 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs font-medium text-[var(--color-muted)]">
            Page {page} of {totalPages} &mdash; {total} total logs
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => page > 1 && setPage(page - 1)}
              disabled={page === 1}
              className="zoho-btn-secondary py-1 px-2.5 text-xs flex items-center gap-1 disabled:opacity-30 disabled:pointer-events-none"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Previous
            </button>
            <button
              onClick={() => page < totalPages && setPage(page + 1)}
              disabled={page === totalPages}
              className="zoho-btn-secondary py-1 px-2.5 text-xs flex items-center gap-1 disabled:opacity-30 disabled:pointer-events-none"
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
