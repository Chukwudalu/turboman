import clsx from "clsx";
import type { RequestStatus, CallStatus } from "@/lib/api";

const DOT: Record<string, string> = {
  pending:              "bg-yellow-400",
  reschedule_requested: "bg-orange-400",
  scheduled:            "bg-blue-400",
  in_progress:          "bg-purple-400",
  completed:            "bg-green-400",
  cancelled:            "bg-slate-400",
  active:               "bg-blue-400 animate-pulse",
  escalated:            "bg-orange-400",
  failed:               "bg-red-400",
};

const REQUEST_COLORS: Record<RequestStatus, string> = {
  pending:               "bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200/80",
  reschedule_requested:  "bg-orange-50 text-orange-700 ring-1 ring-orange-200/80",
  scheduled:             "bg-blue-50 text-blue-700 ring-1 ring-blue-200/80",
  in_progress:           "bg-purple-50 text-purple-700 ring-1 ring-purple-200/80",
  completed:             "bg-green-50 text-green-700 ring-1 ring-green-200/80",
  cancelled:             "bg-slate-100 text-slate-500 ring-1 ring-slate-200/80",
};

const CALL_COLORS: Record<CallStatus, string> = {
  active:     "bg-blue-50 text-blue-700 ring-1 ring-blue-200/80",
  completed:  "bg-green-50 text-green-700 ring-1 ring-green-200/80",
  escalated:  "bg-orange-50 text-orange-700 ring-1 ring-orange-200/80",
  failed:     "bg-red-50 text-red-700 ring-1 ring-red-200/80",
};

const LABELS: Record<string, string> = {
  pending:              "Pending",
  reschedule_requested: "Reschedule Req.",
  scheduled:            "Scheduled",
  in_progress:          "In Progress",
  completed:            "Completed",
  cancelled:            "Cancelled",
  active:               "Active",
  escalated:            "Escalated",
  failed:               "Failed",
};

export function StatusBadge({ status }: { status: string }) {
  const color =
    (REQUEST_COLORS as any)[status] ??
    (CALL_COLORS as any)[status] ??
    "bg-slate-100 text-slate-500 ring-1 ring-slate-200/80";
  const dot = DOT[status] ?? "bg-slate-400";

  return (
    <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap", color)}>
      <span className={clsx("w-1.5 h-1.5 rounded-full shrink-0", dot)} />
      {LABELS[status] ?? status}
    </span>
  );
}
