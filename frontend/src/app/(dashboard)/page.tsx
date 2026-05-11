"use client";
import { useState } from "react";
import { useSession } from "next-auth/react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { DateSelector } from "@/components/date-selector";
import { filterByDate, todayStr } from "@/lib/date-groups";
import Link from "next/link";
import { Phone, ClipboardList, FolderOpen, AlertTriangle, ArrowUpRight } from "lucide-react";

const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "";

function StatCard({ label, value, icon: Icon, iconBg }: { label: string; value: number | undefined; icon: React.ElementType; iconBg: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-slate-500 font-medium">{label}</p>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${iconBg}`}>
          <Icon size={15} className="text-white" />
        </div>
      </div>
      <p className="text-3xl font-bold text-slate-900">{value ?? "—"}</p>
    </div>
  );
}

export default function OverviewPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";
  const [date, setDate] = useState(todayStr());

  const { data: summary } = useSWR(
    token ? ["summary", TENANT_ID] : null,
    () => api.summary(token, TENANT_ID),
    { refreshInterval: 30_000, revalidateOnFocus: false }
  );

  const { data: calls } = useSWR(
    token ? ["calls", TENANT_ID] : null,
    () => api.calls(token, TENANT_ID),
    { revalidateOnFocus: false }
  );

  const { data: requests } = useSWR(
    token ? ["requests", TENANT_ID] : null,
    () => api.requests(token, TENANT_ID),
    { revalidateOnFocus: false }
  );

  const visibleCalls = filterByDate(calls?.data ?? [], (c) => c.started_at, date).slice(0, 8);
  const visibleRequests = filterByDate(requests?.data ?? [], (r) => r.created_at, date).slice(0, 8);

  return (
    <div className="space-y-6 lg:space-y-8 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Overview</h1>
        <p className="text-slate-500 text-sm mt-1">Today's activity across all calls and requests</p>
      </div>

      {/* Stat cards — always today */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Calls today"       value={summary?.calls_today}       icon={Phone}         iconBg="bg-blue-500" />
        <StatCard label="New requests"      value={summary?.bookings_today}    icon={ClipboardList} iconBg="bg-violet-500" />
        <StatCard label="Open requests"     value={summary?.open_requests}     icon={FolderOpen}    iconBg="bg-orange-500" />
        <StatCard label="Escalations today" value={summary?.escalations_today} icon={AlertTriangle} iconBg="bg-red-500" />
      </div>

      {/* Date selector for activity lists */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <p className="text-sm font-medium text-slate-700">Activity</p>
        <DateSelector value={date} onChange={setDate} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Calls list */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">
              Calls
              {visibleCalls.length > 0 && (
                <span className="ml-2 text-xs font-normal text-slate-400">{visibleCalls.length}</span>
              )}
            </h2>
            <Link href="/calls" className="flex items-center gap-1 text-xs font-medium text-brand hover:text-brand-dark transition-colors">
              View all <ArrowUpRight size={12} />
            </Link>
          </div>
          <ul className="divide-y divide-slate-50">
            {visibleCalls.map((c) => (
              <li key={c.id}>
                <Link href={`/calls/${c.id}`} className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 transition-colors group">
                  <div>
                    <p className="text-sm font-medium text-slate-800 group-hover:text-brand transition-colors">
                      {c.customers?.name ?? c.customers?.phone ?? "Unknown"}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5" suppressHydrationWarning>
                      {new Date(c.started_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  <StatusBadge status={c.status} />
                </Link>
              </li>
            ))}
            {!visibleCalls.length && (
              <li className="px-5 py-8 text-sm text-slate-400 text-center">No calls on this date</li>
            )}
          </ul>
        </div>

        {/* Requests list */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">
              Requests
              {visibleRequests.length > 0 && (
                <span className="ml-2 text-xs font-normal text-slate-400">{visibleRequests.length}</span>
              )}
            </h2>
            <Link href="/requests" className="flex items-center gap-1 text-xs font-medium text-brand hover:text-brand-dark transition-colors">
              View all <ArrowUpRight size={12} />
            </Link>
          </div>
          <ul className="divide-y divide-slate-50">
            {visibleRequests.map((r) => (
              <li key={r.id}>
                <Link href={`/requests/${r.id}`} className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 transition-colors group">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-slate-800 group-hover:text-brand transition-colors">{r.service_type}</p>
                      {r.is_emergency && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-semibold bg-red-50 text-red-600 border border-red-200">Emergency</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5" suppressHydrationWarning>
                      {r.customers?.name ?? r.customers?.phone ?? "Unknown"}
                      {" · "}
                      {new Date(r.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  <StatusBadge status={r.status} />
                </Link>
              </li>
            ))}
            {!visibleRequests.length && (
              <li className="px-5 py-8 text-sm text-slate-400 text-center">No requests on this date</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
