"use client";
import { useState, useRef } from "react";
import { useSession } from "next-auth/react";
import useSWRInfinite from "swr/infinite";
import Link from "next/link";
import { ArrowUpRight, Moon, CheckCircle2, XCircle, PhoneOff } from "lucide-react";
import { api, type ServiceRequest, type OncallDispatch, type Page } from "@/lib/api";
import { DateSelector } from "@/components/date-selector";
import { filterByDate, todayStr } from "@/lib/date-groups";
import { decodeTenantId } from "@/lib/jwt";

function latestDispatch(dispatches: OncallDispatch[] | null): OncallDispatch | null {
  if (!dispatches?.length) return null;
  return [...dispatches].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
}

function DispatchBadge({ dispatches }: { dispatches: OncallDispatch[] | null }) {
  const d = latestDispatch(dispatches);
  if (!d || d.status === "dispatching") return <span className="text-xs text-slate-400">Pending</span>;

  if (d.status === "acknowledged") return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-green-50 text-green-700 border border-green-200">
      <CheckCircle2 size={11} /> Accepted{d.oncall_technicians?.name ? ` · ${d.oncall_technicians.name}` : ""}
    </span>
  );
  if (d.status === "rejected") return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
      <XCircle size={11} /> Rejected
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium bg-red-50 text-red-600 border border-red-200">
      <PhoneOff size={11} /> No response
    </span>
  );
}

export default function AfterHoursPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";
  const tenantId = decodeTenantId(token);
  const [date, setDate] = useState(todayStr());

  const { data: pages, isLoading, size, setSize } = useSWRInfinite<Page<ServiceRequest>>(
    (_, prev: Page<ServiceRequest> | null) => {
      if (!token) return null;
      if (prev && !prev.next_cursor) return null;
      return { key: "after-hours", tenantId, cursor: prev?.next_cursor ?? null };
    },
    ({ cursor }: { key: string; tenantId: string; cursor: string | null }) =>
      api.afterHoursRequests(token, tenantId, cursor ?? undefined),
    { refreshInterval: 60_000, revalidateOnFocus: false }
  );

  const everLoaded = useRef(false);
  if (pages !== undefined) everLoaded.current = true;
  const tableLoading = isLoading && !everLoaded.current;

  const all = pages?.flatMap((p) => p.data) ?? [];
  const hasMore = !!pages?.[pages.length - 1]?.next_cursor;
  const isLoadingMore = size > 1 && pages && typeof pages[size - 1] === "undefined";

  const visible = filterByDate(all, (r) => r.created_at, date);

  return (
    <div className="max-w-6xl space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">After Hours</h1>
          <p className="text-slate-500 text-sm mt-1">Service requests received outside of regular business hours.</p>
        </div>
        <DateSelector value={date} onChange={setDate} count={visible.length} noun="request" />
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center">
            <Moon size={14} className="text-indigo-500" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-800">Tonight&apos;s requests</h2>
            <p className="text-xs text-slate-400">
              Requests where the customer asked for same-night service. On-call team notified automatically. {visible.length} on selected date.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Customer</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Service</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">Address</th>
                  <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Time</th>
                  <th className="px-5 py-3.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tableLoading && (
                  <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-400">Loading…</td></tr>
                )}
                {!tableLoading && !visible.length && (
                  <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-400">No after-hours requests on this date</td></tr>
                )}
                {visible.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-slate-800 leading-tight">
                        {r.customers?.name ?? "Unknown"}
                      </p>
                      {r.customers?.phone && (
                        <p className="text-xs text-slate-500 font-mono mt-0.5">{r.customers.phone}</p>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-slate-700">{r.service_type}</td>
                    <td className="px-5 py-3.5">
                      <DispatchBadge dispatches={r.oncall_dispatches} />
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 text-xs hidden sm:table-cell">{r.address ?? "—"}</td>
                    <td className="px-5 py-3.5 text-slate-500 hidden md:table-cell" suppressHydrationWarning>
                      {new Date(r.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link href={`/requests/${r.id}`} className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-brand transition-colors">
                        View <ArrowUpRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {hasMore && (
        <div className="text-center">
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
  );
}
