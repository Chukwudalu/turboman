"use client";
import { useSession } from "next-auth/react";
import useSWR from "swr";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronRight, ArrowUpRight } from "lucide-react";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

export default function CustomerDetailPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";
  const { id } = useParams<{ id: string }>();

  const { data: customer, isLoading } = useSWR(
    token && id ? ["customer", id] : null,
    () => api.customer(token, id)
  );

  if (isLoading) return <p className="text-slate-400 p-8">Loading…</p>;
  if (!customer) return <p className="text-slate-400 p-8">Customer not found.</p>;

  return (
    <div className="max-w-3xl space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-sm text-slate-400">
        <Link href="/customers" className="hover:text-brand transition-colors">Customers</Link>
        <ChevronRight size={14} />
        <span className="text-slate-700 font-medium">{customer.name ?? customer.phone}</span>
      </div>

      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h1 className="text-xl font-bold text-slate-900">{customer.name ?? "Unknown"}</h1>
        <p className="text-slate-500 text-sm mt-1 font-mono">{customer.phone}</p>
        <p className="text-slate-400 text-xs mt-2">
          Customer since {new Date(customer.created_at).toLocaleDateString(undefined, { dateStyle: "long" })}
        </p>
      </div>

      {/* Call history */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-semibold text-slate-800">Call History</h2>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
            {customer.calls?.length ?? 0}
          </span>
        </div>
        {customer.calls?.length ? (
          <ul className="divide-y divide-slate-100">
            {customer.calls.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/calls/${c.id}`}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50/70 transition-colors group"
                >
                  <div>
                    <p className="text-sm text-slate-700 group-hover:text-brand transition-colors font-medium">
                      {new Date(c.started_at).toLocaleString()}
                    </p>
                    {c.duration_s && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        {Math.floor(c.duration_s / 60)}m {c.duration_s % 60}s
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={c.status} />
                    <ArrowUpRight size={14} className="text-slate-300 group-hover:text-brand transition-colors" />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-5 py-8 text-sm text-slate-400 text-center">No calls on record.</p>
        )}
      </div>

      {/* Service requests */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-semibold text-slate-800">Service Requests</h2>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
            {customer.service_requests?.length ?? 0}
          </span>
        </div>
        {customer.service_requests?.length ? (
          <ul className="divide-y divide-slate-100">
            {customer.service_requests.map((r) => (
              <li key={r.id} className="flex items-center justify-between px-5 py-3.5">
                <div>
                  <p className="text-sm font-medium text-slate-800">{r.service_type}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {new Date(r.created_at).toLocaleDateString()}
                  </p>
                </div>
                <StatusBadge status={r.status} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-5 py-8 text-sm text-slate-400 text-center">No service requests on record.</p>
        )}
      </div>
    </div>
  );
}
