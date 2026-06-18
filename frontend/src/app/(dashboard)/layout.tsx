"use client";
import { useEffect, useState } from "react";
import { Menu, Zap, AlertTriangle } from "lucide-react";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import useSWR from "swr";
import Sidebar from "@/components/sidebar";
import { api } from "@/lib/api";
import { decodeTenantId } from "@/lib/jwt";

function TrialBanner({ token }: { token: string }) {
  const tenantId = decodeTenantId(token);
  const { data: settings } = useSWR(
    token ? ["settings-trial", token] : null,
    ([, t]) => api.tenantSettings(t, tenantId),
    { revalidateOnFocus: false }
  );

  if (!settings || settings.plan !== "trial" || !settings.trial_ends_at) return null;

  const msLeft = new Date(settings.trial_ends_at).getTime() - Date.now();
  const daysLeft = Math.ceil(msLeft / (1000 * 60 * 60 * 24));

  if (daysLeft > 7) return null;

  const expired = daysLeft <= 0;

  return (
    <div className={`shrink-0 flex items-center justify-between gap-4 px-5 py-2.5 text-sm ${expired ? "bg-red-600 text-white" : "bg-amber-50 border-b border-amber-200 text-amber-800"}`}>
      <div className="flex items-center gap-2">
        <AlertTriangle size={14} className="shrink-0" />
        {expired
          ? "Your free trial has ended. Upgrade to continue using Turboman."
          : `Your free trial ends in ${daysLeft} day${daysLeft === 1 ? "" : "s"}.`}
      </div>
      <Link
        href="/upgrade"
        className={`shrink-0 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${expired ? "bg-white text-red-600 hover:bg-red-50" : "bg-amber-600 text-white hover:bg-amber-700"}`}
      >
        Upgrade now
      </Link>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { data: session } = useSession();
  const token = (session as any)?.accessToken ?? "";

  useEffect(() => {
    if ((session as any)?.error === "RefreshAccessTokenError") {
      signOut({ callbackUrl: "/login" });
    }
  }, [session]);

  return (
    <div className="flex h-screen overflow-hidden bg-[#fafafa]">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — slide-in drawer on mobile, static column on desktop */}
      <div
        className={`
          fixed inset-y-0 left-0 z-30 transition-transform duration-200 ease-in-out
          lg:static lg:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile top bar */}
        <header className="lg:hidden flex items-center gap-3 px-4 py-3.5 bg-white border-b border-slate-200 shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors"
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center">
              <Zap size={12} className="text-white" />
            </div>
            <span className="font-bold text-slate-900 text-base">Turboman</span>
          </div>
        </header>

        <TrialBanner token={token} />
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
