"use client";
import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Zap, Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // Pre-check backend directly to get the real error message before NextAuth swallows it
      const check = await fetch("/api/backend/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!check.ok) {
        const data = await check.json().catch(() => ({}));
        setError(data.detail ?? "Invalid email or password.");
        return;
      }

      const res = await signIn("credentials", { email, password, redirect: false });
      if (res?.ok) {
        router.push("/dashboard");
      } else {
        setError("Invalid email or password.");
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 relative overflow-hidden">
      {/* Subtle ambient glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm px-5 sm:px-4">
        {/* Logo / brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-brand shadow-lg shadow-brand/40 mb-4">
            <Zap size={22} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Turboman</h1>
          <p className="text-slate-400 mt-1.5 text-sm">Sign in to your dashboard</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl shadow-2xl shadow-black/30 p-8 space-y-5 border border-slate-100"
        >
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition"
              placeholder="admin@yourdomain.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3.5 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent transition"
                placeholder="••••••••"
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
          </div>

          {error && (
            <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brand hover:bg-brand-dark text-white font-semibold rounded-lg py-2.5 text-sm transition-colors disabled:opacity-60 shadow-sm shadow-brand/20"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 mt-6">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-brand hover:underline">
            Start free trial
          </Link>
        </p>
      </div>
    </div>
  );
}
