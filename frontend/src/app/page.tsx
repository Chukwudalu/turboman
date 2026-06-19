"use client";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useEffect, useRef, useState } from "react";
import { motion, useInView, useScroll, useTransform } from "framer-motion";
import { ArrowRight, CheckCircle, Phone, Zap } from "lucide-react";

const fade = {
  hidden: { opacity: 0, y: 32 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, delay: i * 0.12, ease: [0.25, 0.4, 0.25, 1] as const },
  }),
};

const stagger = {
  visible: { transition: { staggerChildren: 0.1 } },
};

function Section({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.section
      ref={ref}
      initial="hidden"
      animate={inView ? "visible" : "hidden"}
      variants={stagger}
      className={className}
    >
      {children}
    </motion.section>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#fafafa] text-slate-900 antialiased">
      <Nav />
      <Hero />
      <Statement />
      <HowItWorks />
      <Features />
      <Pricing />
      <CTA />
      <Footer />
    </div>
  );
}

// ── Nav ──────────────────────────────────────────────────────────────────────

function Nav() {
  const { data: session } = useSession();
  const loggedIn = !!session;
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-white/90 backdrop-blur-xl shadow-sm" : "bg-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
            <Zap size={14} className="text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight">Turboman</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
          <a href="#how" className="hover:text-slate-900 transition-colors">How it works</a>
          <a href="#features" className="hover:text-slate-900 transition-colors">Features</a>
          <a href="#pricing" className="hover:text-slate-900 transition-colors">Pricing</a>
        </nav>

        <div className="flex items-center gap-3">
          {loggedIn ? (
            <Link href="/dashboard" className="text-[13px] font-medium bg-slate-800 text-white px-4 py-2 rounded-full hover:bg-slate-700 transition-colors">
              Dashboard
            </Link>
          ) : (
            <>
              <Link href="/login" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors hidden sm:block">
                Log in
              </Link>
              <Link
                href="/register"
                className="text-[13px] font-medium bg-slate-800 text-white px-4 py-2 rounded-full hover:bg-slate-700 transition-colors"
              >
                Get started
              </Link>
            </>
          )}
        </div>
      </div>
    </motion.header>
  );
}

// ── Hero ─────────────────────────────────────────────────────────────────────

function Hero() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);
  const scale = useTransform(scrollYProgress, [0, 0.5], [1, 0.97]);

  return (
    <motion.section
      ref={ref}
      style={{ opacity, scale }}
      className="relative pt-40 pb-32 px-6"
    >
      <div className="max-w-3xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="inline-block text-sm font-semibold tracking-[0.15em] uppercase text-slate-500 mb-8">
            After-hours answering for trades
          </span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="text-[clamp(2.5rem,6vw,4.5rem)] font-bold leading-[1.05] tracking-tight mb-8"
        >
          Never miss an<br />
          after-hours service request
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25 }}
          className="text-lg sm:text-xl text-slate-600 leading-relaxed max-w-xl mx-auto mb-12"
        >
          Turboman picks up after-hours calls, takes the details, and dispatches
          your on-call tech,automatically.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 bg-slate-800 text-white font-medium px-8 py-3.5 rounded-full hover:bg-slate-700 transition-all text-[15px]"
          >
            Start free trial
            <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform" />
          </Link>
          <a
            href="#how"
            className="inline-flex items-center gap-2 text-slate-500 font-medium px-8 py-3.5 rounded-full hover:text-slate-900 transition-colors text-[15px]"
          >
            See how it works
          </a>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="mt-8 text-sm text-slate-500"
        >
          30 days free · No credit card · Cancel anytime
        </motion.p>
      </div>
    </motion.section>
  );
}

// ── Statement ────────────────────────────────────────────────────────────────

function Statement() {
  return (
    <Section className="py-24 px-6">
      <div className="max-w-4xl mx-auto text-center">
        <motion.p
          variants={fade}
          custom={0}
          className="text-2xl sm:text-3xl md:text-4xl font-semibold leading-snug tracking-tight text-slate-800"
        >
          Your customers call at 2 AM with a burst pipe.{" "}
          <span className="text-slate-500">
            Turboman answers in your company&apos;s name, takes the details, quotes your
            after-hours rate, and dispatches your on-call tech,before you wake up.
          </span>
        </motion.p>
      </div>
    </Section>
  );
}

// ── How it works ─────────────────────────────────────────────────────────────

function HowItWorks() {
  const steps = [
    {
      number: "01",
      title: "Customer calls",
      desc: "After hours, calls go to your Turboman number. The AI answers instantly with your company name,no hold music, no voicemail.",
    },
    {
      number: "02",
      title: "Details captured",
      desc: "Name, address, service needed, urgency. Every detail spelled back and confirmed so nothing gets lost over the phone.",
    },
    {
      number: "03",
      title: "Tech dispatched",
      desc: "Your on-call team is contacted by call and SMS in priority order. If no tech responds, managers are escalated to automatically.",
    },
  ];

  return (
    <Section className="py-32 px-6 bg-white" >
      <div id="how" className="max-w-5xl mx-auto scroll-mt-24">
        <motion.p variants={fade} custom={0} className="text-[11px] font-semibold tracking-[0.2em] uppercase text-slate-500 mb-4">
          How it works
        </motion.p>
        <motion.h2 variants={fade} custom={1} className="text-3xl sm:text-4xl font-bold tracking-tight mb-20">
          Three steps. Zero missed calls.
        </motion.h2>

        <div className="grid md:grid-cols-3 gap-16 md:gap-12">
          {steps.map((s, i) => (
            <motion.div key={s.number} variants={fade} custom={i + 2}>
              <span className="text-5xl font-bold text-slate-100 block mb-6">{s.number}</span>
              <h3 className="text-xl font-semibold mb-3">{s.title}</h3>
              <p className="text-[15px] text-slate-600 leading-relaxed">{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </Section>
  );
}

// ── Features ─────────────────────────────────────────────────────────────────

function Features() {
  const features = [
    {
      title: "Answers every call",
      desc: "No voicemail. No hold queue. Turboman picks up instantly after-hours and handles the conversation start to finish.",
    },
    {
      title: "Quotes your rates",
      desc: "Your after-hours pricing, your services. The AI quotes accurately from your knowledge base,never makes up numbers.",
    },
    {
      title: "Dispatches your team",
      desc: "Technicians are contacted by call and SMS in priority order. Managers are auto-escalated if nobody responds.",
    },
    {
      title: "Confirms every detail",
      desc: "Name, address, and postal code,each spelled back individually over the phone. No more garbled addresses.",
    },
    {
      title: "Works for any trade",
      desc: "Plumbing, HVAC, electrical, roofing, pest control,if you have an after-hours on-call team, Turboman fits.",
    },
    {
      title: "Dashboard for your team",
      desc: "See every after-hours request, dispatch status, and call recording. Add team members, set schedules, update your knowledge base.",
    },
  ];

  return (
    <Section className="py-32 px-6">
      <div id="features" className="max-w-5xl mx-auto scroll-mt-24">
        <motion.p variants={fade} custom={0} className="text-[11px] font-semibold tracking-[0.2em] uppercase text-slate-500 mb-4">
          Features
        </motion.p>
        <motion.h2 variants={fade} custom={1} className="text-3xl sm:text-4xl font-bold tracking-tight mb-20 max-w-lg">
          Everything your after-hours answering service should do.
        </motion.h2>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-12 gap-y-14">
          {features.map((f, i) => (
            <motion.div key={f.title} variants={fade} custom={i + 2}>
              <h3 className="text-[15px] font-semibold mb-2">{f.title}</h3>
              <p className="text-[14px] text-slate-600 leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </Section>
  );
}

// ── Pricing ──────────────────────────────────────────────────────────────────

function Pricing() {
  const included = [
    "Unlimited after-hours calls",
    "Automated on-call dispatch",
    "After-hours rate quoting",
    "Management dashboard",
    "Knowledge base",
    "Team logins",
    "Call history & recordings",
  ];

  return (
    <Section className="py-32 px-6 bg-white">
      <div id="pricing" className="max-w-5xl mx-auto scroll-mt-24">
        <motion.p variants={fade} custom={0} className="text-[11px] font-semibold tracking-[0.2em] uppercase text-slate-500 mb-4">
          Pricing
        </motion.p>
        <motion.h2 variants={fade} custom={1} className="text-3xl sm:text-4xl font-bold tracking-tight mb-20">
          One plan. Everything included.
        </motion.h2>

        <motion.div variants={fade} custom={2} className="max-w-md">
          <div className="border border-slate-200 rounded-2xl p-10 bg-white">
            <p className="text-[13px] font-semibold text-slate-500 uppercase tracking-wide mb-6">Pro</p>
            <div className="flex items-baseline gap-1 mb-1">
              <span className="text-5xl font-bold">$199</span>
              <span className="text-slate-500 text-sm font-medium">/month</span>
            </div>
            <p className="text-[14px] text-slate-500 mb-8">Start with a free 30-day trial</p>

            <Link
              href="/register"
              className="group flex items-center justify-center gap-2 w-full bg-slate-800 text-white font-medium py-3.5 rounded-full hover:bg-slate-700 transition-colors text-[15px] mb-10"
            >
              Start free trial
              <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform" />
            </Link>

            <ul className="space-y-4">
              {included.map((item) => (
                <li key={item} className="flex items-center gap-3 text-[14px] text-slate-600">
                  <CheckCircle size={16} className="text-slate-400 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </motion.div>
      </div>
    </Section>
  );
}

// ── CTA ──────────────────────────────────────────────────────────────────────

function CTA() {
  return (
    <Section className="py-32 px-6">
      <div className="max-w-3xl mx-auto text-center">
        <motion.h2
          variants={fade}
          custom={0}
          className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-6"
        >
          Stop losing customers<br />to voicemail
        </motion.h2>
        <motion.p
          variants={fade}
          custom={1}
          className="text-lg text-slate-600 mb-10 max-w-md mx-auto"
        >
          Set up in 10 minutes. Your first 30 days are free.
        </motion.p>
        <motion.div variants={fade} custom={2}>
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 bg-slate-800 text-white font-medium px-8 py-3.5 rounded-full hover:bg-slate-700 transition-all text-[15px]"
          >
            Get started
            <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </motion.div>
      </div>
    </Section>
  );
}

// ── Footer ───────────────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-slate-200 py-12 px-6">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center">
            <Zap size={12} className="text-white" />
          </div>
          <span className="font-bold text-[15px]">Turboman</span>
        </div>
        <p className="text-[13px] text-slate-500">
          &copy; {new Date().getFullYear()} Turboman. All rights reserved.
        </p>
        <div className="flex gap-6 text-[13px] text-slate-500">
          <a href="#" className="hover:text-slate-900 transition-colors">Privacy</a>
          <a href="#" className="hover:text-slate-900 transition-colors">Terms</a>
          <a href="mailto:hello@turboman.ca" className="hover:text-slate-900 transition-colors">Contact</a>
        </div>
      </div>
    </footer>
  );
}
