"use client";
import Link from "next/link";
import { useSession, signOut } from "next-auth/react";
import {
  PhoneCall, CalendarCheck, Bell, CheckCircle, Zap, Clock, Shield,
  ArrowRight, Star,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <Nav />
      <Hero />
      <LogoBar />
      <HowItWorks />
      <Features />
      <Pricing />
      <Footer />
    </div>
  );
}

// ── Nav ───────────────────────────────────────────────────────────────────────

function Nav() {
  const { data: session } = useSession();
  const loggedIn = !!session;

  return (
    <header className="fixed top-0 inset-x-0 z-50 bg-white/80 backdrop-blur border-b border-slate-100">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-brand flex items-center justify-center shadow shadow-brand/40">
            <Zap size={13} className="text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900">Turboman</span>
        </div>
        <nav className="hidden sm:flex items-center gap-8 text-sm text-slate-600">
          <a href="#how-it-works" className="hover:text-slate-900 transition-colors">How it works</a>
          <a href="#features" className="hover:text-slate-900 transition-colors">Features</a>
          <a href="#pricing" className="hover:text-slate-900 transition-colors">Pricing</a>
        </nav>
        <div className="flex items-center gap-3">
          {loggedIn ? (
            <>
              <Link href="/dashboard" className="text-sm text-slate-600 hover:text-slate-900 transition-colors hidden sm:block">
                Dashboard
              </Link>
              <button
                onClick={() => signOut({ callbackUrl: "/" })}
                className="inline-flex items-center gap-1.5 bg-slate-100 text-slate-700 text-sm font-medium px-4 py-2 rounded-lg hover:bg-slate-200 transition-colors"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-sm text-slate-600 hover:text-slate-900 transition-colors hidden sm:block">
                Log in
              </Link>
              <Link
                href="/register"
                className="inline-flex items-center gap-1.5 bg-brand text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-brand-dark transition-colors shadow-sm shadow-brand/30"
              >
                Start free trial <ArrowRight size={14} />
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <section className="relative pt-32 pb-24 px-6 text-center overflow-hidden">
      {/* Background gradient blobs */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-b from-blue-100/60 via-violet-50/40 to-transparent rounded-full blur-3xl" />
        <div className="absolute top-20 left-1/4 w-64 h-64 bg-cyan-200/20 rounded-full blur-3xl" />
        <div className="absolute top-20 right-1/4 w-64 h-64 bg-violet-200/20 rounded-full blur-3xl" />
      </div>

      <div className="relative max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2 bg-gradient-to-r from-brand/10 to-violet-500/10 text-brand border border-brand/20 rounded-full px-3.5 py-1.5 text-xs font-semibold mb-8">
          <Zap size={12} className="text-brand" /> Free 60-day trial — no credit card required
        </div>
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight leading-tight mb-6">
          Your AI Customer Service<br />
          <span className="bg-gradient-to-r from-brand to-violet-500 bg-clip-text text-transparent">
            never misses a call
          </span>
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed mb-10 max-w-2xl mx-auto">
          Turboman answers every inbound call, books service requests, handles after-hours emergencies,
          and notifies your on-call team — so you can focus on the work, not the phone.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/register"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-gradient-to-r from-brand to-violet-600 text-white font-semibold px-7 py-3.5 rounded-xl hover:opacity-90 transition-opacity text-base shadow-lg shadow-brand/25"
          >
            Start your free trial <ArrowRight size={16} />
          </Link>
          <a
            href="#how-it-works"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 text-slate-600 font-medium px-7 py-3.5 rounded-xl border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-colors text-base"
          >
            See how it works
          </a>
        </div>
        <p className="mt-6 text-xs text-slate-400">
          Free for 60 days. No setup fees. Cancel any time.
        </p>
      </div>

      {/* Dashboard preview */}
      <div className="relative mt-20 max-w-5xl mx-auto rounded-2xl border border-slate-200 shadow-2xl shadow-slate-300/40 overflow-hidden bg-slate-50">
        {/* Browser chrome */}
        <div className="bg-slate-100 border-b border-slate-200 px-4 py-3 flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-400" />
          <span className="w-3 h-3 rounded-full bg-amber-400" />
          <span className="w-3 h-3 rounded-full bg-green-400" />
          <span className="ml-4 flex-1 bg-white rounded text-xs text-slate-400 px-3 py-1 max-w-xs text-center border border-slate-200">
            app.turboman.io/dashboard
          </span>
        </div>
        {/* Stats row */}
        <div className="grid grid-cols-4 divide-x divide-slate-200 bg-white">
          {[
            { label: "Calls today",   value: "12", color: "text-brand" },
            { label: "Open requests", value: "4",  color: "text-violet-600" },
            { label: "Emergencies",   value: "1",  color: "text-red-500" },
            { label: "Resolved",      value: "7",  color: "text-emerald-600" },
          ].map((s) => (
            <div key={s.label} className="px-6 py-5">
              <p className="text-xs text-slate-400 mb-1">{s.label}</p>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
        {/* Request list */}
        <div className="px-6 py-4 space-y-2.5 bg-white border-t border-slate-100">
          {[
            { name: "Sarah M.", service: "AC not cooling",    time: "2 min ago",  badge: "Emergency", color: "bg-red-100 text-red-700" },
            { name: "David K.", service: "Furnace inspection", time: "18 min ago", badge: "Scheduled", color: "bg-violet-100 text-violet-700" },
            { name: "Linda P.", service: "Duct cleaning",     time: "1 hr ago",   badge: "Pending",   color: "bg-amber-100 text-amber-700" },
          ].map((r) => (
            <div key={r.name} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-slate-50">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                  {r.name[0]}
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-800">{r.name}</p>
                  <p className="text-xs text-slate-400">{r.service}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${r.color}`}>{r.badge}</span>
                <span className="text-xs text-slate-400">{r.time}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Logo bar ──────────────────────────────────────────────────────────────────

function LogoBar() {
  const trades = [
    { label: "HVAC",         color: "text-brand bg-blue-50 border-blue-100" },
    { label: "Plumbing",     color: "text-cyan-700 bg-cyan-50 border-cyan-100" },
    { label: "Electrical",   color: "text-amber-700 bg-amber-50 border-amber-100" },
    { label: "Roofing",      color: "text-slate-700 bg-slate-50 border-slate-200" },
    { label: "Pest Control", color: "text-emerald-700 bg-emerald-50 border-emerald-100" },
    { label: "Landscaping",  color: "text-green-700 bg-green-50 border-green-100" },
  ];
  return (
    <section className="py-10 border-y border-slate-100 bg-white">
      <div className="max-w-5xl mx-auto px-6 text-center">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-6">Built for trades businesses</p>
        <div className="flex flex-wrap justify-center gap-3">
          {trades.map((t) => (
            <span key={t.label} className={`px-4 py-2 border rounded-lg text-sm font-medium shadow-sm ${t.color}`}>
              {t.label}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── How it works ──────────────────────────────────────────────────────────────

function HowItWorks() {
  const steps = [
    {
      icon: PhoneCall,
      iconBg: "bg-blue-100",
      iconColor: "text-brand",
      stepColor: "text-brand",
      title: "Customer calls your number",
      desc: "Turboman picks up instantly — 24/7. It greets the caller by business name, collects their name and address, and understands what they need.",
    },
    {
      icon: CalendarCheck,
      iconBg: "bg-violet-100",
      iconColor: "text-violet-600",
      stepColor: "text-violet-500",
      title: "AI books the job",
      desc: "Service request details are logged automatically. For after-hours emergencies, the AI quotes rates and flags it as urgent before confirming.",
    },
    {
      icon: Bell,
      iconBg: "bg-emerald-100",
      iconColor: "text-emerald-600",
      stepColor: "text-emerald-500",
      title: "Your team gets notified",
      desc: "Dispatchers see new requests on the dashboard instantly. For emergencies, on-call technicians are contacted by call and SMS in priority order.",
    },
  ];

  return (
    <section id="how-it-works" className="py-24 px-6 bg-slate-950 text-white">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">How Turboman works</h2>
          <p className="text-slate-400 max-w-xl mx-auto">Three steps, zero missed calls.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-10">
          {steps.map((s, i) => (
            <div key={s.title} className="relative">
              <div className={`w-12 h-12 rounded-2xl ${s.iconBg} flex items-center justify-center mb-5`}>
                <s.icon size={22} className={s.iconColor} />
              </div>
              {i < steps.length - 1 && (
                <div className="absolute top-6 left-12 right-0 h-px bg-gradient-to-r from-slate-600 to-transparent hidden md:block" />
              )}
              <p className={`text-xs font-bold uppercase tracking-widest mb-2 ${s.stepColor}`}>Step {i + 1}</p>
              <h3 className="text-lg font-semibold mb-2 text-white">{s.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Features ──────────────────────────────────────────────────────────────────

function Features() {
  const features = [
    { icon: PhoneCall,     iconBg: "bg-blue-100",    iconColor: "text-brand",        title: "24/7 AI call answering",        desc: "Never goes to voicemail. Handles routine calls, bookings, and questions around the clock." },
    { icon: Zap,           iconBg: "bg-amber-100",   iconColor: "text-amber-600",    title: "Instant emergency detection",   desc: "Identifies life-safety situations, quotes after-hours rates, and triggers your on-call chain automatically." },
    { icon: CalendarCheck, iconBg: "bg-violet-100",  iconColor: "text-violet-600",   title: "Smart service request logging", desc: "Captures service type, address, urgency, and notes — structured and ready for your dispatchers." },
    { icon: Bell,          iconBg: "bg-emerald-100", iconColor: "text-emerald-600",  title: "On-call escalation",            desc: "Texts and calls your technicians in priority order until someone accepts. Escalates to managers if needed." },
    { icon: Clock,         iconBg: "bg-orange-100",  iconColor: "text-orange-600",   title: "After-hours management",        desc: "Separate after-hours rates, AM priority flagging, and a dedicated after-hours view for your team." },
    { icon: Shield,        iconBg: "bg-cyan-100",    iconColor: "text-cyan-600",     title: "Your knowledge base",           desc: "Upload documents or fill in your pricing and services — the AI uses it to answer customer questions accurately." },
  ];

  return (
    <section id="features" className="py-24 px-6 bg-slate-50">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Everything your office needs</h2>
          <p className="text-slate-500 max-w-xl mx-auto">
            Built specifically for trades companies — not a generic chatbot bolted onto a CRM.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
          {features.map((f) => (
            <div key={f.title} className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className={`w-10 h-10 rounded-xl ${f.iconBg} flex items-center justify-center mb-4`}>
                <f.icon size={19} className={f.iconColor} />
              </div>
              <h3 className="font-semibold text-slate-800 mb-2">{f.title}</h3>
              <p className="text-sm text-slate-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Pricing ───────────────────────────────────────────────────────────────────

function Pricing() {
  const included = [
    "Unlimited inbound calls",
    "24/7 AI answering",
    "Emergency detection & on-call dispatch",
    "After-hours management dashboard",
    "Knowledge base (documents + manual entry)",
    "Team logins (multiple users)",
    "Service request tracking",
  ];

  return (
    <section id="pricing" className="py-24 px-6 bg-white">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Simple pricing</h2>
          <p className="text-slate-500 max-w-xl mx-auto">Try everything free for 60 days. No credit card needed.</p>
        </div>
        <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto">
          {/* Trial */}
          <div className="bg-white rounded-2xl border-2 border-slate-200 p-8 shadow-sm relative">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Free trial</p>
            <p className="text-4xl font-bold mb-1">$0</p>
            <p className="text-sm text-slate-500 mb-6">for 60 days, then $149/mo</p>
            <Link
              href="/register"
              className="block w-full text-center bg-slate-900 text-white font-semibold py-3 rounded-xl hover:bg-slate-800 transition-colors mb-6"
            >
              Start free trial
            </Link>
            <ul className="space-y-3">
              {included.map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm text-slate-600">
                  <CheckCircle size={16} className="text-emerald-500 shrink-0 mt-0.5" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Pro */}
          <div className="relative rounded-2xl p-8 shadow-xl text-white overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-brand via-violet-600 to-violet-700" />
            <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "radial-gradient(circle at 80% 20%, white 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
            <div className="relative">
              <div className="flex items-center gap-2 mb-2">
                <p className="text-xs font-bold text-blue-200 uppercase tracking-widest">Pro</p>
                <span className="text-xs font-semibold bg-amber-400 text-amber-900 px-2 py-0.5 rounded-full">Most popular</span>
              </div>
              <p className="text-4xl font-bold mb-1">$149</p>
              <p className="text-sm text-blue-200 mb-6">per month, billed monthly</p>
              <Link
                href="/register"
                className="block w-full text-center bg-white text-brand font-semibold py-3 rounded-xl hover:bg-blue-50 transition-colors mb-6"
              >
                Start free trial
              </Link>
              <ul className="space-y-3">
                {included.map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm text-blue-100">
                    <CheckCircle size={16} className="text-emerald-300 shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
                <li className="flex items-start gap-2.5 text-sm text-white font-medium">
                  <Star size={16} className="text-amber-300 fill-amber-300 shrink-0 mt-0.5" />
                  Priority support
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer className="bg-slate-950 py-10 px-6">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-brand flex items-center justify-center">
            <Zap size={11} className="text-white" />
          </div>
          <span className="font-bold text-white text-base">Turboman</span>
        </div>
        <p>© {new Date().getFullYear()} Turboman. All rights reserved.</p>
        <div className="flex gap-6">
          <a href="#" className="hover:text-slate-300 transition-colors">Privacy</a>
          <a href="#" className="hover:text-slate-300 transition-colors">Terms</a>
          <Link href="/login" className="hover:text-slate-300 transition-colors">Log in</Link>
        </div>
      </div>
    </footer>
  );
}
