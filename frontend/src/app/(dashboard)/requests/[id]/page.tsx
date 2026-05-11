"use client";
import { useState } from "react";
import { useSession } from "next-auth/react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import Link from "next/link";
import { Calendar, ChevronRight, Clock, MapPin, MessageSquare, Phone, User, Radio } from "lucide-react";
import { api, type RequestStatus } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

const NEXT_STATUSES: Partial<Record<RequestStatus, { label: string; value: RequestStatus }[]>> = {
  pending:              [{ label: "Mark Scheduled", value: "scheduled" }, { label: "Cancel", value: "cancelled" }],
  reschedule_requested: [{ label: "Mark Scheduled", value: "scheduled" }, { label: "Cancel", value: "cancelled" }],
  scheduled:            [{ label: "Mark In Progress", value: "in_progress" }],
  in_progress:          [{ label: "Mark Completed", value: "completed" }],
};

function ScheduleModal({
  requestId,
  token,
  onClose,
  onSaved,
}: {
  requestId: string;
  token: string;
  onClose: () => void;
  onSaved: () => void;
}) {
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
          <p className="text-sm text-slate-500 mt-1">
            The customer will receive an SMS confirmation when you save.
          </p>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-600">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600">Time (optional)</label>
            <input
              type="text"
              placeholder='e.g. "9am" or "afternoon"'
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="mt-1 w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            />
          </div>
        </div>
        <div className="flex gap-3 pt-1">
          <button
            onClick={onClose}
            className="flex-1 border border-slate-200 rounded-lg py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving || !date}
            className="flex-1 bg-brand text-white rounded-lg py-2 text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60"
          >
            {saving ? "Saving…" : "Confirm & Send SMS"}
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ icon: Icon, label, value }: { icon: any; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-3.5">
      <div className="w-7 h-7 rounded-md bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0 mt-0.5">
        <Icon size={14} className="text-slate-400" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-0.5">{label}</p>
        <p className="text-sm text-slate-800">{value}</p>
      </div>
    </div>
  );
}

function SummaryCard({ requestId, token }: { requestId: string; token: string }) {
  const { data, isLoading } = useSWR(
    token && requestId ? ["summary", requestId] : null,
    () => api.requestSummary(token, requestId),
    { revalidateOnFocus: false }
  );

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Summary</p>
      {isLoading ? (
        <p className="text-sm text-slate-400 animate-pulse">Generating summary…</p>
      ) : data?.summary ? (
        <p className="text-sm text-slate-700 leading-relaxed">{data.summary}</p>
      ) : (
        <p className="text-sm text-slate-400">No summary available.</p>
      )}
    </div>
  );
}

export default function RequestDetailPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";
  const { id } = useParams<{ id: string }>();
  const [showSchedule, setShowSchedule] = useState(false);
  const [updating, setUpdating] = useState(false);

  const { data: request, isLoading, mutate } = useSWR(
    token && id ? ["request", id] : null,
    () => api.request(token, id)
  );

  async function handleAction(status: RequestStatus) {
    if (status === "scheduled") {
      setShowSchedule(true);
      return;
    }
    setUpdating(true);
    await api.updateRequest(token, id, { status });
    await mutate();
    setUpdating(false);
  }

  if (isLoading) return <p className="text-slate-400 p-8">Loading…</p>;
  if (!request) return <p className="text-slate-400 p-8">Request not found.</p>;

  const actions = NEXT_STATUSES[request.status] ?? [];
  const customerName = request.customers?.name ?? request.customers?.phone ?? "Unknown";

  return (
    <div className="max-w-2xl space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-sm text-slate-400">
        <Link href="/requests" className="hover:text-brand transition-colors">Service Requests</Link>
        <ChevronRight size={14} />
        <span className="text-slate-700 font-medium">{request.service_type}</span>
      </div>

      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl font-bold text-slate-900">{request.service_type}</h1>
              {request.is_emergency && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold bg-red-50 text-red-600 border border-red-200 uppercase tracking-wide">
                  Emergency
                </span>
              )}
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Requested {new Date(request.created_at).toLocaleString()}
            </p>
          </div>
          <StatusBadge status={request.status} />
        </div>

        {actions.length > 0 && (
          <div className="flex gap-2 mt-5 pt-5 border-t border-slate-100">
            {actions.map(({ label, value }) => (
              <button
                key={value}
                onClick={() => handleAction(value)}
                disabled={updating}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-60 ${
                  value === "scheduled"
                    ? "bg-brand text-white hover:bg-brand-dark shadow-sm shadow-brand/20"
                    : value === "cancelled"
                    ? "bg-red-50 text-red-600 hover:bg-red-100 border border-red-200"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {updating ? "Saving…" : label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Details */}
      <div className="bg-white rounded-xl border border-slate-200 px-5 divide-y divide-slate-100">
        <DetailRow icon={User} label="Customer" value={customerName} />
        <DetailRow
          icon={Phone}
          label="Phone"
          value={
            request.customers?.phone ? (
              <a href={`tel:${request.customers.phone}`} className="text-brand hover:underline font-mono text-xs">
                {request.customers.phone}
              </a>
            ) : "—"
          }
        />
        <DetailRow icon={Radio} label="Channel" value={<span className="capitalize">{request.channel}</span>} />
        {request.scheduled_date && (
          <DetailRow
            icon={Calendar}
            label="Scheduled date"
            value={new Date(request.scheduled_date).toLocaleDateString(undefined, { dateStyle: "long" })}
          />
        )}
        {request.scheduled_time && (
          <DetailRow icon={Clock} label="Scheduled time" value={request.scheduled_time} />
        )}
        {request.address && (
          <DetailRow icon={MapPin} label="Address" value={request.address} />
        )}
        {request.notes && (
          <DetailRow icon={MessageSquare} label="Notes" value={request.notes} />
        )}
      </div>

      {/* Linked call */}
      {request.calls && (
        <div className="bg-white rounded-xl border border-slate-200 px-5 py-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Originating call</p>
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-700">
              {request.calls.duration_s != null
                ? `${Math.floor(request.calls.duration_s / 60)}m ${request.calls.duration_s % 60}s`
                : "Duration unknown"}
            </p>
            <p className="text-xs text-slate-400 font-mono">{request.calls.twilio_sid}</p>
          </div>
        </div>
      )}

      {/* AI summary */}
      <SummaryCard requestId={id} token={token} />

      {showSchedule && (
        <ScheduleModal
          requestId={id}
          token={token}
          onClose={() => setShowSchedule(false)}
          onSaved={() => mutate()}
        />
      )}
    </div>
  );
}
