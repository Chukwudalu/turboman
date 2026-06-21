"use client";
import { useState, useEffect } from "react";
import { useSession, signOut } from "next-auth/react";
import useSWR from "swr";
import {
  Clock, Save, UserPlus, Trash2, ChevronUp, ChevronDown,
  Phone, ShieldAlert, MessageSquare, PhoneCall, Radio, Users, PhoneForwarded, AlertTriangle, Lock, Eye, EyeOff,
} from "lucide-react";
import { api, type OncallTechnician, type TeamMember } from "@/lib/api";
import { decodeTenantId, decodeRole } from "@/lib/jwt";

function normalizePhone(raw: string): string {
  const digits = raw.replace(/[\s\-\(\)\.]/g, "");
  if (digits.startsWith("+")) return digits;
  if (digits.length === 10) return `+1${digits}`;
  if (digits.length === 11 && digits.startsWith("1")) return `+${digits}`;
  return digits;
}

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
      await onAdd(name.trim(), normalizePhone(phone.trim()), email.trim());
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
                <label className="text-xs text-slate-500 block mb-1">Phone *</label>
                <input type="tel" placeholder="6045551234" value={phone} onChange={(e) => setPhone(e.target.value)}
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

// ── Team section ──────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<string, string> = { owner: "Owner", admin: "Admin", member: "Member" };

function TeamSection({ token, callerRole }: { token: string; callerRole: string }) {
  const canManage = callerRole === "owner" || callerRole === "admin";

  const { data: members, isLoading, mutate } = useSWR<TeamMember[]>(
    token ? ["team", token] : null,
    ([, t]: [string, string]) => api.teamMembers(t, decodeTenantId(t))
  );

  const [showForm, setShowForm] = useState(false);
  const [invEmail, setInvEmail]   = useState("");
  const [invName, setInvName]     = useState("");
  const [invRole, setInvRole]     = useState("member");
  const [inviting, setInviting]   = useState(false);
  const [inviteResult, setInviteResult] = useState<{ email: string; temp_password: string } | null>(null);
  const [invError, setInvError]   = useState<string | null>(null);
  const [removing, setRemoving]   = useState<string | null>(null);

  async function handleInvite() {
    if (!invEmail.trim() || !invName.trim()) { setInvError("Name and email are required."); return; }
    setInviting(true); setInvError(null); setInviteResult(null);
    try {
      const res = await api.inviteTeamMember(token, { email: invEmail.trim(), name: invName.trim(), role: invRole });
      setInviteResult({ email: res.email, temp_password: res.temp_password });
      setInvEmail(""); setInvName(""); setInvRole("member"); setShowForm(false);
      mutate();
    } catch (e: any) {
      setInvError(e.message ?? "Failed to invite. Please try again.");
    } finally {
      setInviting(false);
    }
  }

  async function handleRemove(id: string) {
    if (!confirm("Remove this team member?")) return;
    setRemoving(id);
    try {
      await api.removeTeamMember(token, id);
      mutate();
    } finally {
      setRemoving(null);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users size={15} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">Team</h2>
        </div>
        {canManage && (
          <button
            onClick={() => { setShowForm((v) => !v); setInvError(null); setInviteResult(null); }}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-brand hover:text-brand-dark transition-colors"
          >
            <UserPlus size={13} /> Invite teammate
          </button>
        )}
      </div>

      <div className="px-6 py-4 space-y-4">
        <p className="text-sm text-slate-500">People who can log in to this dashboard.</p>

        {showForm && canManage && (
          <div className="border border-slate-200 rounded-lg p-4 space-y-3 bg-slate-50">
            <p className="text-xs font-semibold text-slate-600">Invite teammate</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Name *</label>
                <input type="text" placeholder="Jane Smith" value={invName} onChange={(e) => setInvName(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent bg-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Email *</label>
                <input type="email" placeholder="jane@company.com" value={invEmail} onChange={(e) => setInvEmail(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent bg-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Role</label>
                <select value={invRole} onChange={(e) => setInvRole(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent bg-white">
                  <option value="member">Member</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            {invError && <p className="text-xs text-red-600">{invError}</p>}
            <div className="flex gap-2">
              <button onClick={handleInvite} disabled={inviting}
                className="inline-flex items-center gap-1.5 bg-brand text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
                {inviting ? "Inviting…" : "Send invite"}
              </button>
              <button onClick={() => setShowForm(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors">
                Cancel
              </button>
            </div>
          </div>
        )}

        {inviteResult && (
          <div className="border border-green-200 bg-green-50 rounded-lg p-4 space-y-1">
            <p className="text-xs font-semibold text-green-800">Invite created for {inviteResult.email}</p>
            <p className="text-xs text-green-700">Share this temporary password with them — they can change it after logging in:</p>
            <code className="block text-sm font-mono font-bold text-green-900 bg-green-100 rounded px-2 py-1 mt-1">
              {inviteResult.temp_password}
            </code>
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-slate-400 py-2">Loading…</p>
        ) : !members?.length ? (
          <p className="text-sm text-slate-400 py-2">No team members yet.</p>
        ) : (
          <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
            {members.map((m) => (
              <div key={m.id} className="flex items-center gap-3 px-4 py-3 bg-white">
                <div className="w-7 h-7 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand shrink-0">
                  {(m.name ?? m.email)[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{m.name ?? "—"}</p>
                  <p className="text-xs text-slate-500 truncate">{m.email}</p>
                </div>
                <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                  {ROLE_LABELS[m.role] ?? m.role}
                </span>
                {canManage && m.role !== "owner" && (
                  <button onClick={() => handleRemove(m.id)} disabled={removing === m.id}
                    className="text-slate-300 hover:text-red-500 transition-colors shrink-0 disabled:opacity-40" aria-label="Remove">
                    <Trash2 size={15} />
                  </button>
                )}
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
  const tenantId = decodeTenantId(token);
  const callerRole = token ? decodeRole(token) : "member";

  // Business hours
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("17:00");
  const [tz, setTz] = useState("America/New_York");
  const [loading, setLoading] = useState(true);
  const [savingHours, setSavingHours] = useState(false);
  const [savedHours, setSavedHours] = useState(false);
  const [saveErrorHours, setSaveErrorHours] = useState<string | null>(null);

  // On-call settings
  const [voiceTimeout, setVoiceTimeout] = useState(5);
  const [smsTimeout, setSmsTimeout] = useState(10);
  const [notifMethod, setNotifMethod] = useState<"voice" | "sms" | "both">("both");
  const [fallbackDelay, setFallbackDelay] = useState(5);
  const [savingNotif, setSavingNotif] = useState(false);
  const [savedNotif, setSavedNotif] = useState(false);

  // Call confirmation settings
  const [confirmName, setConfirmName] = useState(true);
  const [confirmAddress, setConfirmAddress] = useState(true);
  const [savingConfirm, setSavingConfirm] = useState(false);
  const [savedConfirm, setSavedConfirm] = useState(false);

  // Customer fallback message
  const [fallbackMessage, setFallbackMessage] = useState("");
  const [savingFallback, setSavingFallback] = useState(false);
  const [savedFallback, setSavedFallback] = useState(false);

  // Forwarding number (read-only, provisioned by Turboman)
  const [forwardingPhone, setForwardingPhone] = useState<string | null>(null);

  // AI voice
  const [voiceId, setVoiceId] = useState<string>("");
  const [voiceSaving, setVoiceSaving] = useState(false);
  const [voiceSaved, setVoiceSaved] = useState(false);
  const { data: voices } = useSWR(token ? ["voices", token] : null, ([, t]) => api.voices(t));

  // Escalation phone numbers
  const [escalationPhone, setEscalationPhone] = useState("");
  const [escalationPhoneAfterHours, setEscalationPhoneAfterHours] = useState("");
  const [savingEscalation, setSavingEscalation] = useState(false);
  const [savedEscalation, setSavedEscalation] = useState(false);
  const [saveErrorEscalation, setSaveErrorEscalation] = useState<string | null>(null);

  // Technicians (role=tech)
  const [techs, setTechs] = useState<OncallTechnician[]>([]);
  const [techsLoading, setTechsLoading] = useState(true);

  // Managers (role=manager)
  const [managers, setManagers] = useState<OncallTechnician[]>([]);
  const [managersLoading, setManagersLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    api.tenantSettings(token, tenantId).then((s) => {
      setStart(s.business_hours_start || "09:00");
      setEnd(s.business_hours_end || "17:00");
      setTz(s.business_timezone || "America/New_York");
      setVoiceTimeout(s.oncall_voice_timeout_minutes ?? 5);
      setSmsTimeout(s.oncall_sms_timeout_minutes ?? 10);
      setNotifMethod(s.oncall_notification_method ?? "both");
      setFallbackDelay(s.oncall_fallback_delay_minutes ?? 5);
      setEscalationPhone(s.escalation_phone ?? "");
      setEscalationPhoneAfterHours(s.escalation_phone_after_hours ?? "");
      setConfirmName(s.confirm_name_spelling ?? true);
      setConfirmAddress(s.confirm_address_spelling ?? true);
      setFallbackMessage(s.customer_fallback_message ?? "");
      setForwardingPhone(s.phone ?? null);
      setVoiceId(s.cartesia_voice_id ?? "");
      setLoading(false);
    }).catch(() => setLoading(false));

    api.oncallTechnicians(token, tenantId, "tech").then((list) => {
      setTechs(list); setTechsLoading(false);
    }).catch(() => setTechsLoading(false));

    api.oncallTechnicians(token, tenantId, "manager").then((list) => {
      setManagers(list); setManagersLoading(false);
    }).catch(() => setManagersLoading(false));
  }, [token]);

  async function handleSaveHours() {
    setSavingHours(true); setSavedHours(false); setSaveErrorHours(null);
    try {
      await api.updateTenantSettings(token, tenantId, {
        business_hours_start: start,
        business_hours_end: end,
        business_timezone: tz,
      });
      setSavedHours(true);
      setTimeout(() => setSavedHours(false), 3000);
    } catch { setSaveErrorHours("Failed to save. Please try again."); }
    finally { setSavingHours(false); }
  }

  async function handleSaveNotif() {
    setSavingNotif(true); setSavedNotif(false);
    try {
      await api.updateTenantSettings(token, tenantId, {
        oncall_voice_timeout_minutes: voiceTimeout,
        oncall_sms_timeout_minutes: smsTimeout,
        oncall_notification_method: notifMethod,
        oncall_fallback_delay_minutes: fallbackDelay,
      });
      setSavedNotif(true);
      setTimeout(() => setSavedNotif(false), 3000);
    } finally { setSavingNotif(false); }
  }

  async function handleSaveEscalation() {
    setSavingEscalation(true); setSavedEscalation(false); setSaveErrorEscalation(null);
    try {
      await api.updateTenantSettings(token, tenantId, {
        escalation_phone: escalationPhone ? normalizePhone(escalationPhone) : undefined,
        escalation_phone_after_hours: escalationPhoneAfterHours ? normalizePhone(escalationPhoneAfterHours) : undefined,
      });
      setSavedEscalation(true);
      setTimeout(() => setSavedEscalation(false), 3000);
    } catch { setSaveErrorEscalation("Failed to save. Please try again."); }
    finally { setSavingEscalation(false); }
  }

  function makeHandlers(role: "tech" | "manager", list: OncallTechnician[], setList: React.Dispatch<React.SetStateAction<OncallTechnician[]>>) {
    async function handleAdd(name: string, phone: string, email: string) {
      const nextPriority = list.length > 0 ? Math.max(...list.map((t) => t.priority)) + 1 : 1;
      const contact = await api.addOncallTechnician(token, tenantId, { name, phone, email: email || undefined, priority: nextPriority, role });
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

  async function handleVoiceSave() {
    if (!voiceId) return;
    setVoiceSaving(true); setVoiceSaved(false);
    try {
      await api.updateTenantSettings(token, tenantId, { cartesia_voice_id: voiceId });
      setVoiceSaved(true);
      setTimeout(() => setVoiceSaved(false), 3000);
    } finally {
      setVoiceSaving(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 text-sm mt-1">Business hours, on-call contacts, and notification preferences.</p>
      </div>

      {/* Forwarding number */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <PhoneForwarded size={15} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">AI customer service number</h2>
        </div>
        <div className="px-6 py-5 space-y-3">
          <p className="text-sm text-slate-500">
            Forward your business line to this number to activate your AI receptionist.
            Customers keep calling your existing number — calls are routed to the AI automatically.
          </p>
          {forwardingPhone ? (
            <div className="flex items-center gap-3">
              <span className="font-mono text-lg font-semibold text-slate-800 tracking-wide">{forwardingPhone}</span>
              <button
                onClick={() => navigator.clipboard.writeText(forwardingPhone)}
                className="text-xs text-brand hover:text-brand-dark transition-colors font-medium"
              >
                Copy
              </button>
            </div>
          ) : (
            <p className="text-sm text-slate-400 italic">
              No number assigned yet — contact support to provision one.
            </p>
          )}
          <details className="text-xs text-slate-500">
            <summary className="cursor-pointer font-medium text-slate-600 hover:text-slate-800 transition-colors">
              How to set up forwarding on your carrier
            </summary>
            <ul className="mt-2 space-y-1.5 pl-3 border-l border-slate-200">
              <li><span className="font-medium">Bell / Rogers / Telus landline:</span> Dial <code className="bg-slate-100 px-1 rounded">*72</code> then your Turboman number, press Call</li>
              <li><span className="font-medium">Mobile (iOS):</span> Settings → Phone → Call Forwarding → enter the number above</li>
              <li><span className="font-medium">Mobile (Android):</span> Phone app → Settings → Calls → Call Forwarding → Always Forward</li>
              <li><span className="font-medium">VoIP (RingCentral, 8x8, etc.):</span> Your provider's web portal → Call Handling → Forward calls to the number above</li>
            </ul>
          </details>
        </div>
      </div>

      {/* AI voice */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <MessageSquare size={15} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">AI voice</h2>
        </div>
        <div className="px-6 py-5 space-y-3">
          <p className="text-sm text-slate-500">Choose the voice your AI customer service agent uses on calls.</p>
          {!voices ? (
            <p className="text-sm text-slate-400">Loading voices…</p>
          ) : (
            <select
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent bg-white"
            >
              <option value="">— Select a voice —</option>
              {voices.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          )}
        </div>
        <div className="px-6 py-4 border-t border-slate-100 flex items-center gap-3">
          <button
            onClick={handleVoiceSave}
            disabled={voiceSaving || !voiceId}
            className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60"
          >
            <Save size={14} />{voiceSaving ? "Saving…" : "Save voice"}
          </button>
          {voiceSaved && <p className="text-sm text-green-600 font-medium">Saved!</p>}
        </div>
      </div>

      {/* Spelling confirmation */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <Phone size={15} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">Call confirmation</h2>
        </div>
        <div className="px-6 py-5 space-y-4">
          <p className="text-sm text-slate-500">
            When enabled, the AI will spell back the customer&apos;s name or address to confirm accuracy during the call.
          </p>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={confirmName} onChange={(e) => setConfirmName(e.target.checked)}
              className="w-4 h-4 rounded border-slate-300 text-brand focus:ring-brand" />
            <div>
              <span className="text-sm font-medium text-slate-700">Spell back name</span>
              <p className="text-xs text-slate-400">AI spells the customer&apos;s name back to confirm it was heard correctly</p>
            </div>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={confirmAddress} onChange={(e) => setConfirmAddress(e.target.checked)}
              className="w-4 h-4 rounded border-slate-300 text-brand focus:ring-brand" />
            <div>
              <span className="text-sm font-medium text-slate-700">Spell back address</span>
              <p className="text-xs text-slate-400">AI asks for street, city, and postal code separately and spells each back</p>
            </div>
          </label>
        </div>
        <div className="px-6 py-4 border-t border-slate-100 flex items-center gap-3">
          <button onClick={async () => {
            setSavingConfirm(true); setSavedConfirm(false);
            try {
              await api.updateTenantSettings(token, tenantId, {
                confirm_name_spelling: confirmName,
                confirm_address_spelling: confirmAddress,
              });
              setSavedConfirm(true);
              setTimeout(() => setSavedConfirm(false), 3000);
            } finally { setSavingConfirm(false); }
          }} disabled={savingConfirm || loading}
            className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
            <Save size={14} />{savingConfirm ? "Saving…" : "Save changes"}
          </button>
          {savedConfirm && <p className="text-sm text-green-600 font-medium">Saved!</p>}
        </div>
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
          <button onClick={handleSaveHours} disabled={savingHours || loading}
            className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
            <Save size={14} />{savingHours ? "Saving…" : "Save changes"}
          </button>
          {savedHours && <p className="text-sm text-green-600 font-medium">Saved!</p>}
          {saveErrorHours && <p className="text-sm text-red-600">{saveErrorHours}</p>}
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

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
            <div className="flex items-center gap-3">
              <label className="text-xs font-medium text-slate-600 whitespace-nowrap">Voice timeout</label>
              <input type="number" min={1} max={60} value={voiceTimeout} onChange={(e) => setVoiceTimeout(Number(e.target.value))}
                className="w-20 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent" />
              <span className="text-xs text-slate-500">min to call back before next tech</span>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-xs font-medium text-slate-600 whitespace-nowrap">SMS timeout</label>
              <input type="number" min={1} max={60} value={smsTimeout} onChange={(e) => setSmsTimeout(Number(e.target.value))}
                className="w-20 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent" />
              <span className="text-xs text-slate-500">min to reply before next tech</span>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-1">
            <label className="text-xs font-medium text-slate-600 whitespace-nowrap">Customer fallback delay</label>
            <input type="number" min={0} max={30} value={fallbackDelay} onChange={(e) => setFallbackDelay(Number(e.target.value))}
              className="w-20 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent" />
            <span className="text-xs text-slate-500">min after all contacts exhausted before notifying customer</span>
          </div>
        </div>
        <div className="px-6 py-4 border-t border-slate-100 flex items-center gap-3">
          <button onClick={handleSaveNotif} disabled={savingNotif || loading}
            className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
            <Save size={14} />{savingNotif ? "Saving…" : "Save changes"}
          </button>
          {savedNotif && <p className="text-sm text-green-600 font-medium">Saved!</p>}
        </div>
      </div>

      {/* Customer fallback message */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <MessageSquare size={15} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700">Customer fallback message</h2>
        </div>
        <div className="px-6 py-5 space-y-3">
          <p className="text-sm text-slate-500">
            If no on-call technician or manager accepts the job, this message is sent to the customer via SMS.
            Leave blank to use the default.
          </p>
          <textarea
            rows={3}
            placeholder="We were unable to reach our on-call team tonight. Your request has been logged and our team will contact you first thing next business day."
            value={fallbackMessage}
            onChange={(e) => setFallbackMessage(e.target.value)}
            className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent resize-none"
          />
        </div>
        <div className="px-6 py-4 border-t border-slate-100 flex items-center gap-3">
          <button onClick={async () => {
            setSavingFallback(true); setSavedFallback(false);
            try {
              await api.updateTenantSettings(token, tenantId, {
                customer_fallback_message: fallbackMessage || null,
              });
              setSavedFallback(true);
              setTimeout(() => setSavedFallback(false), 3000);
            } finally { setSavingFallback(false); }
          }} disabled={savingFallback || loading}
            className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
            <Save size={14} />{savingFallback ? "Saving…" : "Save message"}
          </button>
          {savedFallback && <p className="text-sm text-green-600 font-medium">Saved!</p>}
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
                  placeholder="6045551234"
                  value={escalationPhone}
                  onChange={(e) => setEscalationPhone(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
                />
                <p className="text-xs text-slate-400 mt-1">Used during business hours.</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1.5">After-hours number <span className="font-normal text-slate-400">(optional)</span></label>
                <input
                  type="tel"
                  placeholder="6045559876"
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
          <button onClick={handleSaveEscalation} disabled={savingEscalation || loading}
            className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60">
            <Save size={14} />{savingEscalation ? "Saving…" : "Save changes"}
          </button>
          {savedEscalation && <p className="text-sm text-green-600 font-medium">Saved!</p>}
          {saveErrorEscalation && <p className="text-sm text-red-600">{saveErrorEscalation}</p>}
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

      {/* On-call supervisors */}
      <ContactSection
        title="On-call supervisors"
        description="Contacted only after all on-call technicians are unreachable. Typically managers or supervisors who can coordinate a response."
        icon={ShieldAlert}
        iconClass="text-amber-500"
        contacts={managers}
        loading={managersLoading}
        onAdd={managerHandlers.handleAdd}
        onDelete={managerHandlers.handleDelete}
        onMove={managerHandlers.handleMove}
      />

      <TeamSection token={token} callerRole={callerRole} />

      <ChangePasswordSection token={token} />

      {/* Danger zone — owner only */}
      {callerRole === "owner" && (
        <DangerZone token={token} />
      )}
    </div>
  );
}

const PASSWORD_RULES = [
  { label: "At least 8 characters",        test: (p: string) => p.length >= 8 },
  { label: "One uppercase letter (A–Z)",    test: (p: string) => /[A-Z]/.test(p) },
  { label: "One lowercase letter (a–z)",    test: (p: string) => /[a-z]/.test(p) },
  { label: "One number (0–9)",              test: (p: string) => /\d/.test(p) },
  { label: "One special character (!@#…)",  test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

function ChangePasswordSection({ token }: { token: string }) {
  const [current, setCurrent]         = useState("");
  const [next, setNext]               = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNext, setShowNext]       = useState(false);
  const [saving, setSaving]           = useState(false);
  const [success, setSuccess]         = useState(false);
  const [error, setError]             = useState<string | null>(null);

  const allMet = PASSWORD_RULES.every(({ test }) => test(next));

  async function handleSave() {
    setSaving(true); setError(null); setSuccess(false);
    try {
      await api.changePassword(token, { current_password: current, new_password: next });
      setSuccess(true);
      setCurrent(""); setNext("");
      setTimeout(() => setSuccess(false), 3000);
    } catch (e: any) {
      const msg = await e?.message ?? "";
      setError(msg.includes("401") ? "Current password is incorrect" : msg || "Failed to update password.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
        <Lock size={15} className="text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-700">Change password</h2>
      </div>
      <div className="px-6 py-5 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1.5">Current password</label>
            <div className="relative">
              <input
                type={showCurrent ? "text" : "password"}
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              />
              <button type="button" onClick={() => setShowCurrent((v) => !v)} tabIndex={-1}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors">
                {showCurrent ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1.5">New password</label>
            <div className="relative">
              <input
                type={showNext ? "text" : "password"}
                value={next}
                onChange={(e) => setNext(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              />
              <button type="button" onClick={() => setShowNext((v) => !v)} tabIndex={-1}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors">
                {showNext ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
            {next && (
              <ul className="mt-2 space-y-1">
                {PASSWORD_RULES.map(({ label, test }) => {
                  const met = test(next);
                  return (
                    <li key={label} className={`flex items-center gap-1.5 text-xs ${met ? "text-emerald-600" : "text-slate-400"}`}>
                      <span className={`text-[10px] font-bold ${met ? "text-emerald-500" : "text-slate-300"}`}>{met ? "✓" : "○"}</span>
                      {label}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
        {error   && <p className="text-sm text-red-600">{error}</p>}
        {success && <p className="text-sm text-emerald-600 font-medium">Password updated!</p>}
      </div>
      <div className="px-6 py-4 border-t border-slate-100">
        <button
          onClick={handleSave}
          disabled={saving || !current || !allMet}
          className="inline-flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-dark transition-colors disabled:opacity-60"
        >
          <Save size={14} />{saving ? "Saving…" : "Update password"}
        </button>
      </div>
    </div>
  );
}

function DangerZone({ token }: { token: string }) {
  const [confirm, setConfirm] = useState("");
  const [closing, setClosing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClose() {
    if (confirm !== "CLOSE") return;
    setClosing(true); setError(null);
    try {
      await api.closeAccount(token);
      signOut({ callbackUrl: "/login" });
    } catch {
      setError("Failed to close account. Please try again or contact support.");
      setClosing(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-red-200 shadow-sm">
      <div className="px-6 py-4 border-b border-red-100 flex items-center gap-2">
        <AlertTriangle size={15} className="text-red-500" />
        <h2 className="text-sm font-semibold text-red-700">Danger zone</h2>
      </div>
      <div className="px-6 py-5 space-y-4">
        <p className="text-sm text-slate-600">
          Closing your account will immediately release your phone number, deactivate all team members,
          and suspend AI service. This cannot be undone.
        </p>
        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-600 block">
            Type <span className="font-mono font-bold text-red-600">CLOSE</span> to confirm
          </label>
          <input
            type="text"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="CLOSE"
            className="w-full sm:w-64 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent"
          />
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
        <button
          onClick={handleClose}
          disabled={confirm !== "CLOSE" || closing}
          className="inline-flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-40"
        >
          {closing ? "Closing account…" : "Close my account"}
        </button>
      </div>
    </div>
  );
}
