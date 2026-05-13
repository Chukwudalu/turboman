"use client";
import { useState } from "react";
import { useSession } from "next-auth/react";
import useSWRInfinite from "swr/infinite";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { api, type Call, type Page } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { DateSelector } from "@/components/date-selector";
import { filterByDate, todayStr } from "@/lib/date-groups";
import { decodeTenantId } from "@/lib/jwt";

function dur(s: number | null) {
  if (!s) return "—";
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
}

export default function CallsPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";
  const tenantId = decodeTenantId(token);
  const [date, setDate] = useState(todayStr());

  const { data: pages, isLoading, size, setSize } = useSWRInfinite<Page<Call>>(
    (_, prev: Page<Call> | null) => {
      if (!token) return null;
      if (prev && !prev.next_cursor) return null;
      return { key: "calls", tenantId, cursor: prev?.next_cursor ?? null };
    },
    ({ cursor }: { key: string; tenantId: string; cursor: string | null }) =>
      api.calls(token, tenantId, cursor ?? undefined),
    { refreshInterval: 15_000, revalidateOnFocus: false }
  );

  const calls = pages?.flatMap((p) => p.data) ?? [];
  const hasMore = !!pages?.[pages.length - 1]?.next_cursor;
  const isLoadingMore = size > 1 && pages && typeof pages[size - 1] === "undefined";
  const visible = filterByDate(calls, (c) => c.started_at, date);

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Calls</h1>
          <p className="text-slate-500 text-sm mt-1">Complete history of all inbound calls</p>
        </div>
        <DateSelector value={date} onChange={setDate} count={visible.length} noun="call" />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Customer</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">Phone</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Duration</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Time</th>
                <th className="px-5 py-3.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-400">Loading…</td></tr>
              )}
              {!isLoading && !visible.length && (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-400">No calls on this date</td></tr>
              )}
              {visible.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-5 py-3.5 font-medium text-slate-800">{c.customers?.name ?? "—"}</td>
                  <td className="px-5 py-3.5 text-slate-500 font-mono text-xs hidden sm:table-cell">{c.customers?.phone ?? "—"}</td>
                  <td className="px-5 py-3.5"><StatusBadge status={c.status} /></td>
                  <td className="px-5 py-3.5 text-slate-500 hidden md:table-cell">{dur(c.duration_s)}</td>
                  <td className="px-5 py-3.5 text-slate-500 hidden md:table-cell" suppressHydrationWarning>
                    {new Date(c.started_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <Link href={`/calls/${c.id}`} className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-brand transition-colors">
                      View <ArrowUpRight size={12} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {hasMore && (
          <div className="px-5 py-4 border-t border-slate-100 text-center">
            <button
              onClick={() => setSize(size + 1)}
              disabled={!!isLoadingMore}
              className="text-xs font-medium text-slate-500 hover:text-brand transition-colors disabled:opacity-50"
            >
              {isLoadingMore ? "Loading…" : "Load more"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
