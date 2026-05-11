"use client";
import { useState } from "react";
import { useSession } from "next-auth/react";
import useSWRInfinite from "swr/infinite";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { api, type Customer, type Page } from "@/lib/api";
import { DateSelector } from "@/components/date-selector";
import { filterByDate, todayStr } from "@/lib/date-groups";

const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "";

export default function CustomersPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";
  const [date, setDate] = useState(todayStr());

  const { data: pages, isLoading, size, setSize } = useSWRInfinite<Page<Customer>>(
    (_, prev: Page<Customer> | null) => {
      if (!token) return null;
      if (prev && !prev.next_cursor) return null;
      return { key: "customers", tenantId: TENANT_ID, cursor: prev?.next_cursor ?? null };
    },
    ({ cursor }: { key: string; tenantId: string; cursor: string | null }) =>
      api.customers(token, TENANT_ID, cursor ?? undefined),
    { revalidateOnFocus: false }
  );

  const customers = pages?.flatMap((p) => p.data) ?? [];
  const hasMore = !!pages?.[pages.length - 1]?.next_cursor;
  const isLoadingMore = size > 1 && pages && typeof pages[size - 1] === "undefined";
  const visible = filterByDate(customers, (c) => c.last_call_at ?? c.created_at, date);

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Customers</h1>
          <p className="text-slate-500 text-sm mt-1">All customers who have called in</p>
        </div>
        <DateSelector value={date} onChange={setDate} count={visible.length} noun="customer" />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Phone</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">Time</th>
                <th className="px-5 py-3.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr><td colSpan={4} className="px-5 py-10 text-center text-slate-400">Loading…</td></tr>
              )}
              {!isLoading && !visible.length && (
                <tr><td colSpan={4} className="px-5 py-10 text-center text-slate-400">No new customers on this date</td></tr>
              )}
              {visible.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-5 py-3.5 font-medium text-slate-800">{c.name ?? "—"}</td>
                  <td className="px-5 py-3.5 text-slate-500 font-mono text-xs">{c.phone}</td>
                  <td className="px-5 py-3.5 text-slate-500 hidden sm:table-cell" suppressHydrationWarning>
                    {new Date(c.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <Link href={`/customers/${c.id}`} className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-brand transition-colors">
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
