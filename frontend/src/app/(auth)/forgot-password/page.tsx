"use client";
import { useState } from "react";
import Link from "next/link";
import { Zap } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/backend/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? "Something went wrong. Please try again.");
        return;
      }
      setSubmitted(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm px-5 sm:px-4">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-brand shadow-lg shadow-brand/40 mb-4">
            <Zap size={22} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Turboman</h1>
          <p className="text-slate-400 mt-1.5 text-sm">Reset your password</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl shadow-black/30 p-8 border border-slate-100">
          {submitted ? (
            <div className="text-center space-y-3">
              <p className="text-slate-700 text-sm leading-relaxed">
                If that email is registered, you&apos;ll receive a reset link shortly. Check your inbox.
              </p>
              <Link href="/login" className="block text-sm font-medium text-brand hover:underline mt-4">
                Back to login
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition"
                  placeholder="admin@yourdomain.com"
                />
              </div>

              {error && (
                <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-brand hover:bg-brand-dark text-white font-semibold rounded-lg py-2.5 text-sm transition-colors disabled:opacity-60 shadow-sm shadow-brand/20"
              >
                {loading ? "Sending…" : "Send reset link"}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-sm text-slate-500 mt-6">
          <Link href="/login" className="hover:underline">Back to login</Link>
        </p>
      </div>
    </div>
  );
}
