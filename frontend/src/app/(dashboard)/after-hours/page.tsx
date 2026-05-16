"use client";
import { useState, useRef } from "react";
import { useSession } from "next-auth/react";
import useSWRInfinite from "swr/infinite";
import Link from "next/link";
import { ArrowUpRight, Siren, Clock, Sunrise, CheckCircle2, XCircle } from "lucide-react";
import { api, type ServiceRequest, type OncallDispatch, type Page } from "@/lib/api";
import { DateSelector } from "@/components/date-selector";
import { filterByDate, todayStr } from "@/lib/date-groups";
import { decodeTenantId } from "@/lib/jwt";

// ── Dispatch status badge ─────────────────────────────────────────────────────

function latestDispatch(dispatches: OncallDispatch[] | null): OncallDispatch | null {
  if (!dispatches?.length) return null;
  return [...dispatches].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
}

function DispatchBadge({ dispatches }: { dispatches: OncallDispatch[] | null }) {
  const d = latestDispatch(dispatches);
  if (!d || d.status === "dispatching") return <span className="text-xs text-slate-400">—</span>;

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
      <XCircle size={11} /> Could not reach
    </span>
  );
}

// ── Emergency table ───────────────────────────────────────────────────────────

function EmergencyTable({
  requests,
  isLoading,
  date,
}: {
  requests: ServiceRequest[];
  isLoading: boolean;
  date: string;
}) {
  const visible = filterByDate(requests, (r) => r.created_at, date);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Customer</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Service</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Dispatch</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">Address</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Time</th>
              <th className="px-5 py-3.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading && (
              <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-400">Loading…</td></tr>
            )}
            {!isLoading && !visible.length && (
              <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-400">No emergency requests on this date</td></tr>
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
                  {r.customers?.email && (
                    <p className="text-xs text-slate-400 mt-0.5">{r.customers.email}</p>
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
  );
}

// ── Non-emergency after-hours table ──────────────────────────────────────────

function NonEmergencyTable({
  requests,
  isLoading,
  date,
  token,
  onMutate,
}: {
  requests: ServiceRequest[];
  isLoading: boolean;
  date: string;
  token: string;
  onMutate: () => void;
}) {
  const visible = filterByDate(requests, (r) => r.created_at, date);
  const [toggling, setToggling] = useState<string | null>(null);

  async function togglePriority(r: ServiceRequest) {
    setToggling(r.id);
    try {
      await api.updateRequest(token, r.id, { next_morning_priority: !r.next_morning_priority });
      onMutate();
    } finally {
      setToggling(null);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Customer</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Service</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Dispatch</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">Address</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Time</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Priority</th>
              <th className="px-5 py-3.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading && (
              <tr><td colSpan={7} className="px-5 py-10 text-center text-slate-400">Loading…</td></tr>
            )}
            {!isLoading && !visible.length && (
              <tr><td colSpan={7} className="px-5 py-10 text-center text-slate-400">No non-emergency after-hours requests on this date</td></tr>
            )}
            {visible.map((r) => (
              <tr key={r.id} className={`hover:bg-slate-50/70 transition-colors ${r.next_morning_priority ? "bg-amber-50/40" : ""}`}>
                <td className="px-5 py-3.5">
                  <p className="font-medium text-slate-800 leading-tight">
                    {r.customers?.name ?? "Unknown"}
                  </p>
                  {r.customers?.phone && (
                    <p className="text-xs text-slate-500 font-mono mt-0.5">{r.customers.phone}</p>
                  )}
                  {r.customers?.email && (
                    <p className="text-xs text-slate-400 mt-0.5">{r.customers.email}</p>
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
                <td className="px-5 py-3.5">
                  <button
                    onClick={() => togglePriority(r)}
                    disabled={toggling === r.id}
                    title={r.next_morning_priority ? "Remove AM priority" : "Flag as first-thing AM"}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all ${
                      r.next_morning_priority
                        ? "bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100"
                        : "bg-slate-50 text-slate-400 border-slate-200 hover:text-amber-600 hover:border-amber-300 hover:bg-amber-50"
                    }`}
                  >
                    <Sunrise size={12} />
                    {r.next_morning_priority ? "AM priority" : "Set AM"}
                  </button>
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
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AfterHoursPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";
  const tenantId = decodeTenantId(token);
  const [date, setDate] = useState(todayStr());

  const { data: pages, isLoading, size, setSize, mutate } = useSWRInfinite<Page<ServiceRequest>>(
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

  const emergencies = all.filter((r) => r.is_emergency);
  const needsScheduling = all.filter((r) => !r.is_emergency);

  const emergenciesOnDate = filterByDate(emergencies, (r) => r.created_at, date).length;
  const schedulingOnDate = filterByDate(needsScheduling, (r) => r.created_at, date).length;

  return (
    <div className="max-w-6xl space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">After Hours</h1>
          <p className="text-slate-500 text-sm mt-1">Service requests received outside of regular business hours.</p>
        </div>
        <DateSelector value={date} onChange={setDate} count={emergenciesOnDate + schedulingOnDate} noun="request" />
      </div>

      {/* Emergency section */}
      <div className="space-y-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center">
            <Siren size={14} className="text-red-500" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-800">Emergency requests</h2>
            <p className="text-xs text-slate-400">
              Urgent — after-hours rates apply. On-call team notified automatically. {emergenciesOnDate} on selected date.
            </p>
          </div>
        </div>
        <EmergencyTable requests={emergencies} isLoading={tableLoading} date={date} />
      </div>

      {/* Non-emergency after-hours section */}
      <div className="space-y-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center">
            <Clock size={14} className="text-blue-500" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-800">After-hours (non-emergency)</h2>
            <p className="text-xs text-slate-400">
              Non-urgent after-hours requests — on-call team notified. Flag as <span className="font-medium text-amber-600">AM priority</span> to ensure dispatchers attend to it first thing next business day. {schedulingOnDate} on selected date.
            </p>
          </div>
        </div>
        <NonEmergencyTable
          requests={needsScheduling}
          isLoading={tableLoading}
          date={date}
          token={token}
          onMutate={mutate}
        />
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
