"use client";
import { useState } from "react";
import { useSession } from "next-auth/react";
import useSWRInfinite from "swr/infinite";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { api, type RequestStatus, type ServiceRequest, type Page } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { DateSelector } from "@/components/date-selector";
import { filterByDate, todayStr } from "@/lib/date-groups";
import { decodeTenantId } from "@/lib/jwt";

const NEXT_STATUSES: Partial<Record<RequestStatus, { label: string; value: RequestStatus }[]>> = {
  pending:              [{ label: "Mark Scheduled", value: "scheduled" }, { label: "Cancel", value: "cancelled" }],
  reschedule_requested: [{ label: "Mark Scheduled", value: "scheduled" }, { label: "Cancel", value: "cancelled" }],
  scheduled:            [{ label: "Mark In Progress", value: "in_progress" }],
  in_progress:          [{ label: "Mark Completed", value: "completed" }],
};

function ScheduleModal({
  requestId, token, onClose, onSaved,
}: { requestId: string; token: string; onClose: () => void; onSaved: () => void }) {
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    await api.updateRequest(token, requestId, {
      status: "scheduled",
      scheduled_date: date || undefined,
      scheduled_time: time || undefined,
    });
    onSaved();
    onClose();
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm px-4">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm space-y-4 border border-slate-200">
        <div>
          <h2 className="font-semibold text-slate-800">Confirm schedule &amp; send SMS</h2>
          <p className="text-sm text-slate-500 mt-1">The customer will receive an SMS confirmation when you save.</p>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-600">Date</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
              className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600">Time (optional)</label>
            <input type="text" placeholder='e.g. "9am" or "afternoon"' value={time} onChange={(e) => setTime(e.target.value)}
              className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent" />
          </div>
        </div>
        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="flex-1 border border-slate-200 rounded-lg py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">Cancel</button>
          <button onClick={save} disabled={saving || !date} className="flex-1 bg-brand text-white rounded-lg py-2 text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
            {saving ? "Saving…" : "Confirm & Send SMS"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function RequestsPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";
  const tenantId = decodeTenantId(token);
  const [selectedDate, setSelectedDate] = useState(todayStr());
  const [schedulingId, setSchedulingId] = useState<string | null>(null);

  const { data: pages, isLoading, size, setSize, mutate } = useSWRInfinite<Page<ServiceRequest>>(
    (_, prev: Page<ServiceRequest> | null) => {
      if (!token) return null;
      if (prev && !prev.next_cursor) return null;
      return { key: "requests", tenantId, cursor: prev?.next_cursor ?? null };
    },
    ({ cursor }: { key: string; tenantId: string; cursor: string | null }) =>
      api.requests(token, tenantId, undefined, cursor ?? undefined),
    { refreshInterval: 20_000, revalidateOnFocus: false }
  );

  const requests = pages?.flatMap((p) => p.data) ?? [];
  const hasMore = !!pages?.[pages.length - 1]?.next_cursor;
  const isLoadingMore = size > 1 && pages && typeof pages[size - 1] === "undefined";
  const visible = filterByDate(requests, (r) => r.created_at, selectedDate);

  async function handleAction(id: string, status: RequestStatus) {
    if (status === "scheduled") { setSchedulingId(id); return; }
    await api.updateRequest(token, id, { status });
    mutate();
  }

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Service Requests</h1>
          <p className="text-slate-500 text-sm mt-1">Mark as scheduled to send the customer an SMS confirmation.</p>
        </div>
        <DateSelector value={selectedDate} onChange={setSelectedDate} count={visible.length} noun="request" />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Customer</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Service</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">Channel</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Time</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">Actions</th>
                <th className="px-5 py-3.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr><td colSpan={7} className="px-5 py-10 text-center text-slate-400">Loading…</td></tr>
              )}
              {!isLoading && !visible.length && (
                <tr><td colSpan={7} className="px-5 py-10 text-center text-slate-400">No requests on this date</td></tr>
              )}
              {visible.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-5 py-3.5 font-medium text-slate-800">{r.customers?.name ?? r.customers?.phone ?? "—"}</td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-slate-700">{r.service_type}</span>
                      {r.is_emergency && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-semibold bg-red-50 text-red-600 border border-red-200 whitespace-nowrap">Emergency</span>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-3.5"><StatusBadge status={r.status} /></td>
                  <td className="px-5 py-3.5 text-slate-500 capitalize hidden sm:table-cell">{r.channel}</td>
                  <td className="px-5 py-3.5 text-slate-500 hidden md:table-cell" suppressHydrationWarning>
                    {new Date(r.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="px-5 py-3.5 hidden sm:table-cell">
                    <div className="flex flex-wrap gap-2">
                      {(NEXT_STATUSES[r.status] ?? []).map(({ label, value }) => (
                        <button key={value} onClick={() => handleAction(r.id, value)}
                          className={`text-xs px-2.5 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap ${
                            value === "scheduled" ? "bg-brand text-white hover:bg-brand-dark"
                            : value === "cancelled" ? "bg-red-50 text-red-600 hover:bg-red-100 border border-red-200"
                            : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                          }`}
                        >{label}</button>
                      ))}
                    </div>
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

      {schedulingId && (
        <ScheduleModal requestId={schedulingId} token={token} onClose={() => setSchedulingId(null)} onSaved={() => mutate()} />
      )}
    </div>
  );
}
