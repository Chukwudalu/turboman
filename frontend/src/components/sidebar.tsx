"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { LayoutDashboard, Phone, Users, BookOpen, LogOut, Zap, Settings2, Moon, PhoneForwarded } from "lucide-react";
import clsx from "clsx";

const NAV = [
  { href: "/dashboard",       label: "Overview",        icon: LayoutDashboard },
  { href: "/calls",           label: "Calls",            icon: Phone },
  { href: "/after-hours",     label: "After Hours",      icon: Moon },
  { href: "/escalations",    label: "Escalations",      icon: PhoneForwarded },
  { href: "/customers",       label: "Customers",        icon: Users },
  { href: "/knowledge-base",  label: "Knowledge Base",   icon: BookOpen },
  { href: "/settings",        label: "Settings",         icon: Settings2 },
];

export default function Sidebar({ onClose }: { onClose?: () => void }) {
  const path = usePathname();
  const { data: session } = useSession();

  async function handleSignOut() {
    const refreshToken = (session as any)?.refreshToken;
    if (refreshToken) {
      await fetch("/api/backend/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {});
    }
    onClose?.();
    signOut({ callbackUrl: "/login" });
  }

  return (
    <aside className="w-64 h-full bg-white flex flex-col shrink-0 border-r border-slate-200">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center shrink-0">
            <Zap size={14} className="text-white" />
          </div>
          <span className="text-slate-900 font-bold text-lg tracking-tight">Turboman</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href || (href !== "/dashboard" && path.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                active
                  ? "bg-slate-900 text-white"
                  : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
              )}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Sign out */}
      <div className="px-3 py-4 border-t border-slate-100">
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-slate-500 hover:text-slate-900 hover:bg-slate-50 transition-all duration-150"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
