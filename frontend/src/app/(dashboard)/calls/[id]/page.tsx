"use client";
import { useSession } from "next-auth/react";
import useSWR from "swr";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronRight, Bot, User } from "lucide-react";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

export default function CallDetailPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";
  const { id } = useParams<{ id: string }>();

  const { data: call, isLoading } = useSWR(
    token && id ? ["call", id] : null,
    () => api.call(token, id)
  );

  if (isLoading) return <p className="text-slate-400 p-8">Loading…</p>;
  if (!call) return <p className="text-slate-400 p-8">Call not found.</p>;

  const customer = call.customers;
  const duration = call.duration_s
    ? `${Math.floor(call.duration_s / 60)}m ${call.duration_s % 60}s`
    : "—";

  return (
    <div className="max-w-3xl space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-sm text-slate-400">
        <Link href="/calls" className="hover:text-brand transition-colors">Calls</Link>
        <ChevronRight size={14} />
        <span className="text-slate-700 font-medium">Call detail</span>
      </div>

      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              {customer?.name ?? customer?.phone ?? "Unknown caller"}
            </h1>
            {customer?.name && (
              <p className="text-slate-500 text-sm mt-0.5">{customer.phone}</p>
            )}
          </div>
          <StatusBadge status={call.status} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-100 text-sm">
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide font-medium mb-1">Started</p>
            <p className="text-slate-700 font-medium">{new Date(call.started_at).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide font-medium mb-1">Duration</p>
            <p className="text-slate-700 font-medium">{duration}</p>
          </div>
          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide font-medium mb-1">Actions taken</p>
            <p className="text-slate-700 font-medium">{call.call_actions?.length ?? 0}</p>
          </div>
        </div>
      </div>

      {/* Transcript — chat bubble layout */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="font-semibold text-slate-800 mb-5">Transcript</h2>
        {call.transcript ? (
          <div className="space-y-3">
            {call.transcript.split("\n").filter(Boolean).map((line, i) => {
              const isCaller = line.startsWith("caller:");
              const isAgent  = line.startsWith("agent:");
              const text = line.replace(/^(caller|agent):\s*/, "");

              if (!isCaller && !isAgent) {
                return (
                  <p key={i} className="text-xs text-slate-400 text-center py-1">{line}</p>
                );
              }

              return (
                <div
                  key={i}
                  className={`flex items-end gap-2 ${isAgent ? "flex-row-reverse" : ""}`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mb-0.5 ${
                      isCaller ? "bg-slate-200" : "bg-brand"
                    }`}
                  >
                    {isCaller
                      ? <User size={12} className="text-slate-600" />
                      : <Bot size={12} className="text-white" />
                    }
                  </div>

                  {/* Bubble */}
                  <div
                    className={`max-w-[78%] px-3.5 py-2.5 text-sm leading-relaxed ${
                      isCaller
                        ? "bg-slate-100 text-slate-700 rounded-2xl rounded-bl-sm"
                        : "bg-brand text-white rounded-2xl rounded-br-sm"
                    }`}
                  >
                    {text}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-slate-400 text-sm">No transcript available.</p>
        )}
      </div>
    </div>
  );
}
