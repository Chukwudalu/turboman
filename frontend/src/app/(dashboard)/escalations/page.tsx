"use client";
import { useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import useSWR from "swr";
import { api, type Escalation, type EscalationStatus } from "@/lib/api";
import { PhoneForwarded, FileText } from "lucide-react";

function StatusBadge({ status }: { status: EscalationStatus }) {
  const styles: Record<EscalationStatus, string> = {
    pending: "bg-amber-50 text-amber-700 border-amber-200",
    bridged: "bg-blue-50 text-blue-700 border-blue-200",
    handled: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  const labels: Record<EscalationStatus, string> = {
    pending: "Pending",
    bridged: "Bridged",
    handled: "Handled",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}

export default function EscalationsPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken as string ?? "";
  const [marking, setMarking] = useState<string | null>(null);

  const { data: escalations, isLoading, mutate } = useSWR<Escalation[]>(
    token ? ["escalations", token] : null,
    ([, t]) => api.escalations(t as string),
    { refreshInterval: 20_000, revalidateOnFocus: false }
  );

  async function markHandled(id: string) {
    setMarking(id);
    try {
      await api.updateEscalation(token, id, "handled");
      mutate();
    } finally {
      setMarking(null);
    }
  }

  const pending = escalations?.filter((e) => e.status === "pending") ?? [];
  const rest = escalations?.filter((e) => e.status !== "pending") ?? [];

  return (
    <div className="max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Escalations</h1>
        <p className="text-slate-500 text-sm mt-1">
          Calls the AI transferred to your team. Mark pending ones as handled after calling the customer back.
        </p>
      </div>

      {/* Pending — needs action */}
      {pending.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-amber-200">
            <h2 className="text-sm font-semibold text-amber-800">
              Needs callback ({pending.length})
            </h2>
          </div>
          <div className="divide-y divide-amber-100">
            {pending.map((e) => (
              <EscalationRow key={e.id} escalation={e} marking={marking} onMarkHandled={markHandled} />
            ))}
          </div>
        </div>
      )}

      {/* All escalations table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200">
          <h2 className="text-sm font-semibold text-slate-700">All escalations</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Customer</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Summary</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Time</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-400">Loading…</td></tr>
              )}
              {!isLoading && !escalations?.length && (
                <tr>
                  <td colSpan={5} className="px-5 py-10 text-center">
                    <div className="flex flex-col items-center gap-2 text-slate-400">
                      <PhoneForwarded size={24} className="opacity-40" />
                      <span className="text-sm">No escalations yet</span>
                    </div>
                  </td>
                </tr>
              )}
              {[...pending, ...rest].map((e) => (
                <tr key={e.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-5 py-3.5 font-medium text-slate-800 whitespace-nowrap">
                    {e.customers?.name ?? e.customers?.phone ?? "Unknown"}
                  </td>
                  <td className="px-5 py-3.5 text-slate-600 max-w-sm">
                    <p className="text-sm whitespace-pre-wrap">{e.summary ?? "—"}</p>
                    {e.call_id && (
                      <Link
                        href={`/calls/${e.call_id}`}
                        className="mt-1 inline-flex items-center gap-1 text-xs text-brand hover:underline"
                      >
                        <FileText size={12} />
                        View transcript
                      </Link>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={e.status} />
                  </td>
                  <td className="px-5 py-3.5 text-slate-500 hidden md:table-cell whitespace-nowrap" suppressHydrationWarning>
                    {new Date(e.created_at).toLocaleString([], {
                      month: "short", day: "numeric",
                      hour: "2-digit", minute: "2-digit",
                    })}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    {e.status === "pending" && (
                      <button
                        onClick={() => markHandled(e.id)}
                        disabled={marking === e.id}
                        className="text-xs px-2.5 py-1.5 rounded-lg font-medium bg-brand text-white hover:bg-brand-dark transition-colors disabled:opacity-60 whitespace-nowrap"
                      >
                        {marking === e.id ? "Saving…" : "Mark Handled"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function EscalationRow({
  escalation: e,
  marking,
  onMarkHandled,
}: {
  escalation: Escalation;
  marking: string | null;
  onMarkHandled: (id: string) => void;
}) {
  return (
    <div className="px-5 py-4 flex items-start justify-between gap-4">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-slate-800 text-sm">
            {e.customers?.name ?? e.customers?.phone ?? "Unknown caller"}
          </span>
          {e.customers?.phone && e.customers?.name && (
            <span className="text-xs text-slate-500">{e.customers.phone}</span>
          )}
          <span className="text-xs text-slate-400" suppressHydrationWarning>
            {new Date(e.created_at).toLocaleString([], {
              month: "short", day: "numeric",
              hour: "2-digit", minute: "2-digit",
            })}
          </span>
        </div>
        {e.summary && (
          <p className="mt-1 text-sm text-slate-600 whitespace-pre-wrap">{e.summary}</p>
        )}
        {e.call_id && (
          <Link
            href={`/calls/${e.call_id}`}
            className="mt-2 inline-flex items-center gap-1 text-xs text-brand hover:underline"
          >
            <FileText size={12} />
            View full transcript
          </Link>
        )}
      </div>
      <button
        onClick={() => onMarkHandled(e.id)}
        disabled={marking === e.id}
        className="shrink-0 text-xs px-3 py-1.5 rounded-lg font-medium bg-brand text-white hover:bg-brand-dark transition-colors disabled:opacity-60"
      >
        {marking === e.id ? "Saving…" : "Mark Handled"}
      </button>
    </div>
  );
}
