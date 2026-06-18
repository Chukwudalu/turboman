"use client";
import { useState } from "react";
import Link from "next/link";
import { Zap, Eye, EyeOff } from "lucide-react";

const PASSWORD_RULES = [
  { label: "At least 8 characters",      test: (p: string) => p.length >= 8 },
  { label: "One uppercase letter (A–Z)",  test: (p: string) => /[A-Z]/.test(p) },
  { label: "One lowercase letter (a–z)",  test: (p: string) => /[a-z]/.test(p) },
  { label: "One number (0–9)",            test: (p: string) => /\d/.test(p) },
  { label: "One special character (!@#…)", test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

function PasswordChecklist({ password }: { password: string }) {
  if (!password) return null;
  return (
    <ul className="mt-2 space-y-1">
      {PASSWORD_RULES.map(({ label, test }) => {
        const met = test(password);
        return (
          <li key={label} className={`flex items-center gap-1.5 text-xs ${met ? "text-emerald-600" : "text-slate-400"}`}>
            <span className={`text-[10px] font-bold ${met ? "text-emerald-500" : "text-slate-300"}`}>
              {met ? "✓" : "○"}
            </span>
            {label}
          </li>
        );
      })}
    </ul>
  );
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TRADE_TYPES = [
  { value: "hvac",         label: "HVAC" },
  { value: "plumbing",     label: "Plumbing" },
  { value: "electrical",   label: "Electrical" },
  { value: "roofing",      label: "Roofing" },
  { value: "pest_control", label: "Pest Control" },
  { value: "landscaping",  label: "Landscaping" },
  { value: "other",        label: "Other trades" },
];

export default function RegisterPage() {
  const [companyName, setCompanyName] = useState("");
  const [tradeType, setTradeType]     = useState("");
  const [name, setName]               = useState("");
  const [email, setEmail]             = useState("");
  const [password, setPassword]         = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState<string | null>(null);
  const [registered, setRegistered]     = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: companyName,
          trade_type: tradeType,
          name,
          email,
          password,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? "Registration failed. Please try again.");
        return;
      }

      setRegistered(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (registered) {
    return (
      <div className="min-h-screen bg-[#fafafa] flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-md text-center space-y-4">
          <div className="w-14 h-14 rounded-xl bg-slate-800 flex items-center justify-center mx-auto">
            <Zap size={22} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Check your email</h1>
          <p className="text-slate-600 text-sm leading-relaxed">
            We sent a verification link to <span className="font-medium text-slate-900">{email}</span>.
            Click the link to activate your account.
          </p>
          <p className="text-xs text-slate-500">Didn&apos;t get it? Check your spam folder.</p>
          <Link href="/login" className="block text-sm font-medium text-slate-900 hover:underline mt-4">
            Back to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#fafafa] flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2.5 mb-6">
            <div className="w-9 h-9 rounded-lg bg-slate-800 flex items-center justify-center">
              <Zap size={15} className="text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900">Turboman</span>
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Create your account</h1>
          <p className="text-sm text-slate-500 mt-1.5">Set up your company in under a minute. Free for 30 days.</p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1.5">Company name *</label>
              <input
                type="text"
                required
                placeholder="Smith Plumbing"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1.5">Trade type *</label>
              <select
                required
                value={tradeType}
                onChange={(e) => setTradeType(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent bg-white text-slate-700"
              >
                <option value="" disabled>Select your trade…</option>
                {TRADE_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1.5">Your name *</label>
              <input
                type="text"
                required
                placeholder="John Smith"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1.5">Work email *</label>
              <input
                type="email"
                required
                placeholder="john@smithplumbing.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1.5">Password *</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  placeholder="Min 8 chars, upper, lower, number, symbol"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <PasswordChecklist password={password} />
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-full py-3 transition-colors disabled:opacity-60 text-sm"
            >
              {loading ? "Creating your account…" : "Start free trial"}
            </button>

            <p className="text-xs text-slate-500 text-center leading-relaxed">
              By signing up you agree to our{" "}
              <a href="#" className="underline">Terms of Service</a> and{" "}
              <a href="#" className="underline">Privacy Policy</a>.
            </p>
          </form>
        </div>

        <p className="text-center text-sm text-slate-500 mt-6">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-slate-900 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
