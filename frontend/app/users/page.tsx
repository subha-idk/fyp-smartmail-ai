"use client";

import * as React from "react";
import Link from "next/link";
import { Search, ChevronLeft, ChevronRight, Users as UsersIcon } from "lucide-react";
import { fetchUsers, type User } from "@/lib/api";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import EngagementBadge from "@/components/EngagementBadge";
import ChurnRiskBar from "@/components/ChurnRiskBar";

export default function UsersPage() {
  const [users, setUsers] = React.useState<User[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [search, setSearch] = React.useState("");
  const [debouncedSearch, setDebouncedSearch] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const limit = 20;

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [search]);

  React.useEffect(() => {
    let active = true;
    const loadUsers = async () => {
      setLoading(true);
      try {
        const res = await fetchUsers(page, limit, debouncedSearch);
        if (active) {
          setUsers(res.users);
          setTotal(res.total);
        }
      } catch (err) {
        console.error("Failed to load users:", err);
      } finally {
        if (active) setLoading(false);
      }
    };
    loadUsers();
    return () => { active = false; };
  }, [page, debouncedSearch]);

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const formatLastActive = (dateStr: string | null | undefined) => {
    if (!dateStr) return "Never";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return "—";
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Title */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">
          Users Directory
        </h1>
        <p className="text-sm text-slate-500">
          Search and view customer engagement profiles, churn risks, and
          purchase intents.
        </p>
      </div>

      {/* Search Input */}
      <div
        className="flex items-center gap-2 max-w-md px-3 py-2.5 rounded-lg transition-all duration-200"
        style={{
          background: "rgba(15,23,41,0.8)",
          border: "1px solid rgba(99,102,241,0.15)",
          backdropFilter: "blur(12px)",
        }}
        onFocusCapture={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor =
            "rgba(99,102,241,0.5)";
          (e.currentTarget as HTMLDivElement).style.boxShadow =
            "0 0 0 2px rgba(99,102,241,0.15)";
        }}
        onBlurCapture={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor =
            "rgba(99,102,241,0.15)";
          (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
        }}
      >
        <Search className="h-4 w-4 text-slate-500 shrink-0" />
        <input
          id="user-search"
          type="text"
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full text-sm outline-none border-none bg-transparent text-slate-200 placeholder-slate-600"
        />
      </div>

      {/* Users Table */}
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
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 px-4">
            <UsersIcon className="h-10 w-10 text-slate-700 mb-3" />
            <p className="text-sm font-medium text-slate-400">No users found</p>
            <p className="text-xs text-slate-600 mt-1">
              Try adjusting your search filters.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Engagement</TableHead>
                <TableHead>Churn Risk</TableHead>
                <TableHead>Purchase Prob</TableHead>
                <TableHead>Last Active</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => {
                const profile = user.profile;
                const churnRisk = (profile as any)?.churn_risk;
                const purchaseProb = (profile as any)?.purchase_probability;
                return (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium text-slate-100">
                      {user.name || "N/A"}
                    </TableCell>
                    <TableCell className="text-slate-400">{user.email}</TableCell>
                    <TableCell>
                      <EngagementBadge score={profile?.engagement_score} />
                    </TableCell>
                    <TableCell>
                      <ChurnRiskBar risk={churnRisk} />
                    </TableCell>
                    <TableCell className="font-semibold text-slate-300">
                      {purchaseProb !== null && purchaseProb !== undefined
                        ? `${Math.round(purchaseProb * 100)}%`
                        : "N/A"}
                    </TableCell>
                    <TableCell className="text-slate-500 text-xs">
                      {formatLastActive(profile?.last_active_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/users/${user.id}`}>
                        <button
                          className="px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer transition-all duration-200
                            border border-[rgba(99,102,241,0.3)] text-indigo-400
                            hover:bg-[rgba(99,102,241,0.1)] hover:border-[rgba(99,102,241,0.5)] hover:text-indigo-300"
                        >
                          View
                        </button>
                      </Link>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Pagination */}
      {!loading && users.length > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-500">
            Page {page} of {totalPages} &mdash; {total} total users
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

            {/* Page numbers */}
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const pageNum =
                totalPages <= 5
                  ? i + 1
                  : page <= 3
                  ? i + 1
                  : page >= totalPages - 2
                  ? totalPages - 4 + i
                  : page - 2 + i;
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`h-7 w-7 flex items-center justify-center text-xs font-medium rounded-md cursor-pointer transition-all duration-200 ${
                    page === pageNum
                      ? "bg-indigo-600 text-white border border-indigo-500"
                      : "text-slate-400 hover:text-slate-200 hover:bg-[rgba(99,102,241,0.08)]"
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}

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
