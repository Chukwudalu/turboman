"use client";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Zap, CheckCircle, XCircle, Loader } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function VerifyEmailPage() {
  const params = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");
  const called = useRef(false);

  useEffect(() => {
    // Guard against React StrictMode double-invocation
    if (called.current) return;
    called.current = true;

    if (!token) {
      setStatus("error");
      setMessage("No verification token found. Please use the link from your email.");
      return;
    }

    fetch(`${API_URL}/auth/verify-email?token=${token}`)
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          setStatus("success");
          setMessage(data.message ?? "Email verified successfully.");
        } else {
          setStatus("error");
          setMessage(data.detail ?? "This link is invalid or has already been used.");
        }
      })
      .catch(() => {
        setStatus("error");
        setMessage("Something went wrong. Please try again.");
      });
  }, [token]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm text-center space-y-4">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-brand shadow-lg shadow-brand/30 mb-2">
          <Zap size={20} className="text-white" />
        </div>

        {status === "loading" && (
          <>
            <Loader size={32} className="animate-spin text-brand mx-auto" />
            <p className="text-slate-500 text-sm">Verifying your email…</p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle size={40} className="text-emerald-500 mx-auto" />
            <h1 className="text-xl font-bold text-slate-900">Email verified!</h1>
            <p className="text-slate-500 text-sm">{message}</p>
            <Link
              href="/login"
              className="inline-block mt-2 bg-brand text-white font-semibold text-sm px-6 py-2.5 rounded-lg hover:bg-brand-dark transition-colors"
            >
              Log in to your account
            </Link>
          </>
        )}

        {status === "error" && (
          <>
            <XCircle size={40} className="text-red-500 mx-auto" />
            <h1 className="text-xl font-bold text-slate-900">Verification failed</h1>
            <p className="text-slate-500 text-sm">{message}</p>
            <Link href="/login" className="block text-sm font-medium text-brand hover:underline mt-2">
              Back to login
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
