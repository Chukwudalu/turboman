"use client";
import { CheckCircle } from "lucide-react";

export default function UpgradePage() {
  return (
    <div className="max-w-2xl mx-auto py-16 px-6">
      <div className="bg-white rounded-2xl border border-slate-200 p-10 text-center">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Upgrade to Turboman Pro</h1>
        <p className="text-slate-600 mb-8 text-base leading-relaxed">
          Keep your after-hours dispatcher running. Never miss a service request again.
        </p>

        <div className="bg-[#fafafa] rounded-xl p-6 mb-8 text-left">
          <div className="flex items-baseline gap-1 mb-4">
            <span className="text-4xl font-bold text-slate-900">$199</span>
            <span className="text-slate-500 text-base">/month</span>
          </div>
          <ul className="space-y-3 text-sm text-slate-700">
            {[
              "AI answers every after-hours call automatically",
              "Books service requests and dispatches on-call techs",
              "Unlimited calls and service requests",
              "SMS + voice dispatch to your on-call team",
              "Full call transcripts and dashboard",
            ].map((feature) => (
              <li key={feature} className="flex items-start gap-2">
                <CheckCircle size={16} className="text-slate-400 mt-0.5 shrink-0" />
                {feature}
              </li>
            ))}
          </ul>
        </div>

        <a
          href="mailto:hello@turboman.ca?subject=Upgrade%20to%20Turboman%20Pro"
          className="inline-flex items-center justify-center w-full bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm py-3 px-6 rounded-full transition-colors"
        >
          Contact us to upgrade
        </a>
        <p className="text-xs text-slate-500 mt-4">
          Reply within one business day. No long-term contracts.
        </p>
      </div>
    </div>
  );
}
