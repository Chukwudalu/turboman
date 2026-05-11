const BASE = "/api/backend";

async function req<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Page<T> {
  data: T[];
  next_cursor: string | null;
}

export type CallStatus = "active" | "completed" | "escalated" | "failed";
export type RequestStatus =
  | "pending"
  | "reschedule_requested"
  | "scheduled"
  | "in_progress"
  | "completed"
  | "cancelled";

export interface Summary {
  calls_today: number;
  bookings_today: number;
  escalations_today: number;
  open_requests: number;
}

export interface Call {
  id: string;
  status: CallStatus;
  duration_s: number | null;
  started_at: string;
  ended_at: string | null;
  customers: { name: string | null; phone: string } | null;
}

export interface CallDetail extends Call {
  transcript: string | null;
  call_actions: { id: string; type: string; payload: any; result: any; success: boolean; created_at: string }[];
}

export interface TenantSettings {
  id: string;
  name: string;
  business_hours_start: string | null;
  business_hours_end: string | null;
  business_timezone: string | null;
  oncall_escalation_timeout_minutes: number | null;
  oncall_notification_method: "voice" | "sms" | "both" | null;
  oncall_fallback_delay_minutes: number | null;
  escalation_phone: string | null;
  escalation_phone_after_hours: string | null;
}

export interface OncallTechnician {
  id: string;
  tenant_id: string;
  name: string;
  phone: string;
  email: string | null;
  priority: number;
  role: "tech" | "manager";
  active: boolean;
  created_at: string;
}

export interface OncallDispatch {
  status: "dispatching" | "acknowledged" | "rejected" | "failed";
  created_at: string;
}

export interface ServiceRequest {
  id: string;
  service_type: string;
  status: RequestStatus;
  is_emergency: boolean;
  is_after_hours: boolean;
  next_morning_priority: boolean;
  scheduled_date: string | null;
  scheduled_time: string | null;
  address: string | null;
  notes: string | null;
  channel: string;
  created_at: string;
  customers: { name: string | null; phone: string; email: string | null } | null;
  oncall_dispatches: OncallDispatch[] | null;
}

export interface Customer {
  id: string;
  name: string | null;
  phone: string;
  created_at: string;
  last_call_at: string | null;
}

export interface CustomerDetail extends Customer {
  calls: { id: string; status: CallStatus; duration_s: number | null; started_at: string }[];
  service_requests: { id: string; service_type: string; status: RequestStatus; created_at: string }[];
}

export interface ServiceRequestDetail extends ServiceRequest {
  calls: { twilio_sid: string; duration_s: number | null } | null;
}

export interface KBChunk {
  id: string;
  content: string;
  metadata: Record<string, string>;
  created_at: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const api = {
  summary: (token: string, tenantId: string) =>
    req<Summary>(`/dashboard/summary?tenant_id=${tenantId}`, token),

  calls: (token: string, tenantId: string, cursor?: string) =>
    req<Page<Call>>(`/dashboard/calls?tenant_id=${tenantId}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`, token),

  call: (token: string, id: string) =>
    req<CallDetail>(`/dashboard/calls/${id}`, token),

  requests: (token: string, tenantId: string, status?: string, cursor?: string) =>
    req<Page<ServiceRequest>>(
      `/dashboard/service-requests?tenant_id=${tenantId}${status ? `&status=${status}` : ""}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
      token
    ),

  afterHoursRequests: (token: string, tenantId: string, cursor?: string) =>
    req<Page<ServiceRequest>>(
      `/dashboard/service-requests?tenant_id=${tenantId}&is_after_hours=true${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
      token
    ),

  request: (token: string, id: string) =>
    req<ServiceRequestDetail>(`/dashboard/service-requests/${id}`, token),

  requestSummary: (token: string, id: string) =>
    req<{ summary: string }>(`/dashboard/service-requests/${id}/summary`, token),

  updateRequest: (
    token: string,
    id: string,
    body: { status?: RequestStatus; scheduled_date?: string; scheduled_time?: string; next_morning_priority?: boolean }
  ) =>
    req<ServiceRequest>(`/dashboard/service-requests/${id}`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  customers: (token: string, tenantId: string, cursor?: string) =>
    req<Page<Customer>>(`/dashboard/customers?tenant_id=${tenantId}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`, token),

  customer: (token: string, id: string) =>
    req<CustomerDetail>(`/dashboard/customers/${id}`, token),

  kbChunks: (token: string, tenantId: string, cursor?: string) =>
    req<Page<KBChunk>>(`/dashboard/kb?tenant_id=${tenantId}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`, token),

  deleteKbChunk: (token: string, chunkId: string) =>
    req<{ deleted: boolean }>(`/dashboard/kb/${chunkId}`, token, { method: "DELETE" }),

  tenantSettings: (token: string, tenantId: string) =>
    req<TenantSettings>(`/dashboard/settings?tenant_id=${tenantId}`, token),

  updateTenantSettings: (
    token: string,
    tenantId: string,
    body: {
      business_hours_start?: string;
      business_hours_end?: string;
      business_timezone?: string;
      oncall_escalation_timeout_minutes?: number;
      oncall_notification_method?: "voice" | "sms" | "both";
      oncall_fallback_delay_minutes?: number;
      escalation_phone?: string;
      escalation_phone_after_hours?: string;
    }
  ) =>
    req<TenantSettings>(`/dashboard/settings?tenant_id=${tenantId}`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  oncallTechnicians: (token: string, tenantId: string, role: "tech" | "manager" = "tech") =>
    req<OncallTechnician[]>(`/dashboard/oncall-technicians?tenant_id=${tenantId}&role=${role}`, token),

  addOncallTechnician: (
    token: string,
    tenantId: string,
    body: { name: string; phone: string; email?: string; priority: number; role: "tech" | "manager" }
  ) =>
    req<OncallTechnician>(`/dashboard/oncall-technicians?tenant_id=${tenantId}`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateOncallTechnician: (
    token: string,
    techId: string,
    body: { name?: string; phone?: string; email?: string; priority?: number; active?: boolean }
  ) =>
    req<OncallTechnician>(`/dashboard/oncall-technicians/${techId}`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteOncallTechnician: (token: string, techId: string) =>
    req<{ deleted: boolean }>(`/dashboard/oncall-technicians/${techId}`, token, {
      method: "DELETE",
    }),

  uploadKbFile: async (token: string, tenantId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/dashboard/kb/upload?tenant_id=${tenantId}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json() as Promise<{ filename: string; chunks_added: number }>;
  },
};
