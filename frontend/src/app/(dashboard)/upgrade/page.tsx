"use client";

export default function UpgradePage() {
  return (
    <div className="max-w-2xl mx-auto py-16 px-6">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-10 text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-blue-50 mb-6">
          <svg className="w-7 h-7 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Upgrade to Turboman Pro</h1>
        <p className="text-gray-500 mb-8 text-base leading-relaxed">
          Keep your AI after-hours dispatcher running. Never miss an emergency call again.
        </p>

        <div className="bg-gray-50 rounded-xl p-6 mb-8 text-left">
          <div className="flex items-baseline gap-1 mb-4">
            <span className="text-4xl font-bold text-gray-900">$199</span>
            <span className="text-gray-500 text-base">/month</span>
          </div>
          <ul className="space-y-3 text-sm text-gray-700">
            {[
              "AI answers every after-hours call automatically",
              "Books service requests and dispatches on-call techs",
              "Unlimited calls and service requests",
              "SMS + voice dispatch to your on-call team",
              "Full call transcripts and dashboard",
            ].map((feature) => (
              <li key={feature} className="flex items-start gap-2">
                <svg className="w-4 h-4 text-green-500 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                {feature}
              </li>
            ))}
          </ul>
        </div>

        <a
          href="mailto:hello@turboman.ca?subject=Upgrade%20to%20Turboman%20Pro"
          className="inline-flex items-center justify-center w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-base py-3 px-6 rounded-xl transition-colors"
        >
          Contact us to upgrade
        </a>
        <p className="text-xs text-gray-400 mt-4">
          Reply within one business day. No long-term contracts.
        </p>
      </div>
    </div>
  );
}
