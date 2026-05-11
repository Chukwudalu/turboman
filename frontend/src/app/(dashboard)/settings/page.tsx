"use client";
import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import {
  Clock, Save, UserPlus, Trash2, ChevronUp, ChevronDown,
  Phone, ShieldAlert, MessageSquare, PhoneCall, Radio,
} from "lucide-react";
import { api, type OncallTechnician } from "@/lib/api";

const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "";

const TIMEZONES = [
  { value: "America/New_York",    label: "Eastern (ET)" },
  { value: "America/Chicago",     label: "Central (CT)" },
  { value: "America/Denver",      label: "Mountain (MT)" },
  { value: "America/Los_Angeles", label: "Pacific (PT)" },
  { value: "America/Phoenix",     label: "Arizona (no DST)" },
  { value: "America/Anchorage",   label: "Alaska (AKT)" },
  { value: "Pacific/Honolulu",    label: "Hawaii (HT)" },
  { value: "Europe/London",       label: "London (GMT/BST)" },
  { value: "Europe/Paris",        label: "Central Europe (CET)" },
  { value: "UTC",                 label: "UTC" },
];

const PRIORITY_LABELS: Record<number, string> = { 1: "Primary", 2: "Secondary", 3: "Tertiary" };
function priorityLabel(p: number) { return PRIORITY_LABELS[p] ?? `#${p}`; }

// ── Reusable contact list ──────────────────────────────────────────────────────

function ContactSection({
  title,
  description,
  icon: Icon,
  iconClass,
  contacts,
  loading,
  onAdd,
  onDelete,
  onMove,
}: {
  title: string;
  description: string;
  icon: React.ElementType;
  iconClass: string;
  contacts: OncallTechnician[];
  loading: boolean;
  onAdd: (name: string, phone: string, email: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onMove: (index: number, direction: "up" | "down") => Promise<void>;
}) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  async function handleAdd() {
    if (!name.trim() || !phone.trim()) { setError("Name and phone are required."); return; }
    setAdding(true); setError(null);
    try {
      await onAdd(name.trim(), phone.trim(), email.trim());
      setName(""); setPhone(""); setEmail(""); setShowForm(false);
    } catch { setError("Failed to add. Please try again."); }
    finally { setAdding(false); }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={15} className={iconClass} />
          <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
        </div>
        <button
          onClick={() => { setShowForm((v) => !v); setError(null); }}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-brand hover:text-brand-dark transition-colors"
        >
          <UserPlus size={13} /> Add contact
        </button>
      </div>

      <div className="px-6 py-4 space-y-3">
        <p className="text-sm text-slate-500">{description}</p>

        {showForm && (
          <div className="border border-slate-200 rounded-lg p-4 space-y-3 bg-slate-50">
            <p className="text-xs font-semibold text-slate-600">New contact</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Name *</label>
                <input type="text" placeholder="John Smith" value={name} onChange={(e) => setName(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent bg-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Phone * (E.164 e.g. +14155551234)</label>
                <input type="tel" placeholder="+14155551234" value={phone} onChange={(e) => setPhone(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent bg-white" />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs text-slate-500 block mb-1">Email (optional)</label>
                <input type="email" placeholder="john@company.com" value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent bg-white" />
              </div>
            </div>
            {error && <p className="text-xs text-red-600">{error}</p>}
            <div className="flex gap-2">
              <button onClick={handleAdd} disabled={adding}
                className="inline-flex items-center gap-1.5 bg-brand text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
                {adding ? "Adding…" : "Add"}
              </button>
              <button onClick={() => { setShowForm(false); setError(null); }}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors">
                Cancel
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-400 py-2">Loading…</p>
        ) : contacts.length === 0 ? (
          <p className="text-sm text-slate-400 py-2">No contacts added yet.</p>
        ) : (
          <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
            {contacts.map((c, i) => (
              <div key={c.id} className="flex items-center gap-3 px-4 py-3 bg-white">
                <div className="flex flex-col gap-0.5 shrink-0">
                  <button onClick={() => onMove(i, "up")} disabled={i === 0}
                    className="text-slate-300 hover:text-slate-500 disabled:opacity-0 transition-colors" aria-label="Move up">
                    <ChevronUp size={14} />
                  </button>
                  <button onClick={() => onMove(i, "down")} disabled={i === contacts.length - 1}
                    className="text-slate-300 hover:text-slate-500 disabled:opacity-0 transition-colors" aria-label="Move down">
                    <ChevronDown size={14} />
                  </button>
                </div>
                <div className="min-w-[80px]">
                  <span className="text-xs font-medium text-brand bg-brand/8 border border-brand/20 px-2 py-0.5 rounded-full">
                    {priorityLabel(c.priority)}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{c.name}</p>
                  <p className="text-xs text-slate-500 truncate">{c.phone}{c.email ? ` · ${c.email}` : ""}</p>
                </div>
                <button onClick={() => onDelete(c.id)}
                  className="text-slate-300 hover:text-red-500 transition-colors shrink-0" aria-label="Remove">
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";

  // Business hours
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("17:00");
  const [tz, setTz] = useState("America/New_York");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // On-call settings
  const [timeout, setTimeout_] = useState(10);
  const [notifMethod, setNotifMethod] = useState<"voice" | "sms" | "both">("both");
  const [fallbackDelay, setFallbackDelay] = useState(5);

  // Escalation phone numbers
  const [escalationPhone, setEscalationPhone] = useState("");
  const [escalationPhoneAfterHours, setEscalationPhoneAfterHours] = useState("");

  // Technicians (role=tech)
  const [techs, setTechs] = useState<OncallTechnician[]>([]);
  const [techsLoading, setTechsLoading] = useState(true);

  // Managers (role=manager)
  const [managers, setManagers] = useState<OncallTechnician[]>([]);
  const [managersLoading, setManagersLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    api.tenantSettings(token, TENANT_ID).then((s) => {
      setStart(s.business_hours_start || "09:00");
      setEnd(s.business_hours_end || "17:00");
      setTz(s.business_timezone || "America/New_York");
      setTimeout_(s.oncall_escalation_timeout_minutes ?? 10);
      setNotifMethod(s.oncall_notification_method ?? "both");
      setFallbackDelay(s.oncall_fallback_delay_minutes ?? 5);
      setEscalationPhone(s.escalation_phone ?? "");
      setEscalationPhoneAfterHours(s.escalation_phone_after_hours ?? "");
      setLoading(false);
    }).catch(() => setLoading(false));

    api.oncallTechnicians(token, TENANT_ID, "tech").then((list) => {
      setTechs(list); setTechsLoading(false);
    }).catch(() => setTechsLoading(false));

    api.oncallTechnicians(token, TENANT_ID, "manager").then((list) => {
      setManagers(list); setManagersLoading(false);
    }).catch(() => setManagersLoading(false));
  }, [token]);

  async function handleSave() {
    setSaving(true); setSaved(false); setSaveError(null);
    try {
      await api.updateTenantSettings(token, TENANT_ID, {
        business_hours_start: start,
        business_hours_end: end,
        business_timezone: tz,
        oncall_escalation_timeout_minutes: timeout,
        oncall_notification_method: notifMethod,
        oncall_fallback_delay_minutes: fallbackDelay,
        escalation_phone: escalationPhone,
        escalation_phone_after_hours: escalationPhoneAfterHours,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch { setSaveError("Failed to save. Please try again."); }
    finally { setSaving(false); }
  }

  function makeHandlers(role: "tech" | "manager", list: OncallTechnician[], setList: React.Dispatch<React.SetStateAction<OncallTechnician[]>>) {
    async function handleAdd(name: string, phone: string, email: string) {
      const nextPriority = list.length > 0 ? Math.max(...list.map((t) => t.priority)) + 1 : 1;
      const contact = await api.addOncallTechnician(token, TENANT_ID, { name, phone, email: email || undefined, priority: nextPriority, role });
      setList((prev) => [...prev, contact]);
    }

    async function handleDelete(id: string) {
      await api.deleteOncallTechnician(token, id);
      const remaining = list.filter((t) => t.id !== id);
      const reordered = await Promise.all(remaining.map((t, i) => api.updateOncallTechnician(token, t.id, { priority: i + 1 })));
      setList(reordered);
    }

    async function handleMove(index: number, direction: "up" | "down") {
      const newList = [...list];
      const swap = direction === "up" ? index - 1 : index + 1;
      if (swap < 0 || swap >= newList.length) return;
      [newList[index], newList[swap]] = [newList[swap], newList[index]];
      const reordered = await Promise.all(newList.map((t, i) => api.updateOncallTechnician(token, t.id, { priority: i + 1 })));
      setList(reordered);
    }

    return { handleAdd, handleDelete, handleMove };
  }

  const techHandlers = makeHandlers("tech", techs, setTechs);
  const managerHandlers = makeHandlers("manager", managers, setManagers);

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 text-sm mt-1">Business hours, on-call contacts, and notification preferences.</p>
      </div>

      {/* Business hours */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <Clock size={15} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">Business hours</h2>
        </div>
        <div className="px-6 py-5 space-y-5">
          <p className="text-sm text-slate-500">
            Requests received outside these hours are flagged as after-hours. Weekends are always after-hours.
          </p>
          {loading ? <p className="text-sm text-slate-400">Loading…</p> : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1.5">Opens</label>
                <input type="time" value={start} onChange={(e) => setStart(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1.5">Closes</label>
                <input type="time" value={end} onChange={(e) => setEnd(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1.5">Timezone</label>
                <select value={tz} onChange={(e) => setTz(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent bg-white">
                  {TIMEZONES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
            </div>
          )}
          <p className="text-xs text-slate-400">Monday – Friday only. Weekends are always after-hours.</p>
        </div>
        <div className="px-6 py-4 border-t border-slate-100 flex items-center gap-3">
          <button onClick={handleSave} disabled={saving || loading}
            className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
            <Save size={14} />{saving ? "Saving…" : "Save changes"}
          </button>
          {saved && <p className="text-sm text-green-600 font-medium">Saved!</p>}
          {saveError && <p className="text-sm text-red-600">{saveError}</p>}
        </div>
      </div>

      {/* Notification method + timeout */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <Radio size={15} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">On-call notification method</h2>
        </div>
        <div className="px-6 py-5 space-y-5">
          <p className="text-sm text-slate-500">
            Choose how the system contacts on-call technicians and escalation managers when an after-hours request is booked.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {([
              { value: "both",  label: "Call + SMS",  Icon: PhoneCall,     desc: "Outbound call and SMS simultaneously" },
              { value: "voice", label: "Call only",   Icon: Phone,         desc: "Outbound voice call only" },
              { value: "sms",   label: "SMS only",    Icon: MessageSquare, desc: "Text message only" },
            ] as const).map(({ value, label, Icon, desc }) => (
              <button
                key={value}
                onClick={() => setNotifMethod(value)}
                className={`flex flex-col items-start gap-1 p-3.5 rounded-lg border text-left transition-all ${
                  notifMethod === value
                    ? "border-brand bg-brand/5 ring-1 ring-brand"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon size={14} className={notifMethod === value ? "text-brand" : "text-slate-400"} />
                  <span className={`text-sm font-medium ${notifMethod === value ? "text-brand" : "text-slate-700"}`}>{label}</span>
                </div>
                <p className="text-xs text-slate-400">{desc}</p>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3 pt-1">
            <label className="text-xs font-medium text-slate-600 whitespace-nowrap">Response timeout</label>
            <input type="number" min={1} max={60} value={timeout} onChange={(e) => setTimeout_(Number(e.target.value))}
              className="w-20 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent" />
            <span className="text-xs text-slate-500">minutes before escalating to next contact</span>
          </div>

          <div className="flex items-center gap-3 pt-1">
            <label className="text-xs font-medium text-slate-600 whitespace-nowrap">Callback grace period</label>
            <input type="number" min={0} max={30} value={fallbackDelay} onChange={(e) => setFallbackDelay(Number(e.target.value))}
              className="w-20 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent" />
            <span className="text-xs text-slate-500">minutes to wait after missed dispatch before notifying customer — gives techs time to call back</span>
          </div>
        </div>
        <div className="px-6 py-4 border-t border-slate-100 flex items-center gap-3">
          <button onClick={handleSave} disabled={saving || loading}
            className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
            <Save size={14} />{saving ? "Saving…" : "Save changes"}
          </button>
          {saved && <p className="text-sm text-green-600 font-medium">Saved!</p>}
        </div>
      </div>

      {/* Human escalation phones */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <PhoneCall size={15} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">Human escalation</h2>
        </div>
        <div className="px-6 py-5 space-y-5">
          <p className="text-sm text-slate-500">
            When a caller asks to speak to a person or the AI cannot help, the call is warm-transferred
            to this number. Set a separate after-hours number if your on-call manager handles
            escalations differently at night.
          </p>
          {loading ? <p className="text-sm text-slate-400">Loading…</p> : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1.5">Business hours number</label>
                <input
                  type="tel"
                  placeholder="+14155551234"
                  value={escalationPhone}
                  onChange={(e) => setEscalationPhone(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                />
                <p className="text-xs text-slate-400 mt-1">Used during business hours. E.164 format.</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1.5">After-hours number <span className="font-normal text-slate-400">(optional)</span></label>
                <input
                  type="tel"
                  placeholder="+14155559876"
                  value={escalationPhoneAfterHours}
                  onChange={(e) => setEscalationPhoneAfterHours(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                />
                <p className="text-xs text-slate-400 mt-1">If blank, falls back to the business hours number.</p>
              </div>
            </div>
          )}
        </div>
        <div className="px-6 py-4 border-t border-slate-100 flex items-center gap-3">
          <button onClick={handleSave} disabled={saving || loading}
            className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
            <Save size={14} />{saving ? "Saving…" : "Save changes"}
          </button>
          {saved && <p className="text-sm text-green-600 font-medium">Saved!</p>}
          {saveError && <p className="text-sm text-red-600">{saveError}</p>}
        </div>
      </div>

      {/* On-call technicians */}
      <ContactSection
        title="On-call technicians"
        description="Contacted when an after-hours request comes in. The system works through the list in priority order."
        icon={Phone}
        iconClass="text-slate-400"
        contacts={techs}
        loading={techsLoading}
        onAdd={techHandlers.handleAdd}
        onDelete={techHandlers.handleDelete}
        onMove={techHandlers.handleMove}
      />

      {/* Escalation contacts */}
      <ContactSection
        title="Escalation contacts"
        description="Contacted only after all on-call technicians are unreachable. Typically managers or supervisors who can coordinate a response."
        icon={ShieldAlert}
        iconClass="text-amber-500"
        contacts={managers}
        loading={managersLoading}
        onAdd={managerHandlers.handleAdd}
        onDelete={managerHandlers.handleDelete}
        onMove={managerHandlers.handleMove}
      />
    </div>
  );
}
