"use client";
import { useEffect, useRef, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Zap, CheckCircle, XCircle, Loader } from "lucide-react";

function VerifyEmailContent() {
  const params = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    if (!token) {
      setStatus("error");
      setMessage("No verification token found. Please use the link from your email.");
      return;
    }

    fetch(`/api/backend/auth/verify-email?token=${token}`)
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
    <div className="min-h-screen bg-[#fafafa] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm text-center space-y-4">
        <Link href="/" className="inline-flex items-center gap-2.5 mb-4">
          <div className="w-9 h-9 rounded-lg bg-slate-800 flex items-center justify-center">
            <Zap size={15} className="text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900">Turboman</span>
        </Link>

        {status === "loading" && (
          <>
            <Loader size={28} className="animate-spin text-slate-400 mx-auto" />
            <p className="text-slate-500 text-sm">Verifying your email…</p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle size={36} className="text-emerald-500 mx-auto" />
            <h1 className="text-xl font-bold text-slate-900">Email verified</h1>
            <p className="text-slate-600 text-sm">{message}</p>
            <Link
              href="/login"
              className="inline-block mt-2 bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm px-6 py-2.5 rounded-full transition-colors"
            >
              Log in to your account
            </Link>
          </>
        )}

        {status === "error" && (
          <>
            <XCircle size={36} className="text-red-500 mx-auto" />
            <h1 className="text-xl font-bold text-slate-900">Verification failed</h1>
            <p className="text-slate-600 text-sm">{message}</p>
            <Link href="/login" className="block text-sm font-medium text-slate-900 hover:underline mt-2">
              Back to login
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmailContent />
    </Suspense>
  );
}
