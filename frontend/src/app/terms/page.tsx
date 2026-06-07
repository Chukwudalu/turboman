import Link from "next/link";
import { Zap } from "lucide-react";

export const metadata = { title: "Terms of Service — Turboman" };

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#fafafa]">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-3xl mx-auto px-6 h-16 flex items-center">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
              <Zap size={14} className="text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight">Turboman</span>
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Terms of Service</h1>
        <p className="text-sm text-slate-500 mb-12">Last updated: June 18, 2026</p>

        <div className="prose prose-slate prose-sm max-w-none space-y-8 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-slate-900 [&_h2]:mb-3 [&_p]:text-slate-600 [&_p]:leading-relaxed [&_li]:text-slate-600">
          <section>
            <h2>1. Agreement to Terms</h2>
            <p>
              By accessing or using Turboman (&quot;the Service&quot;), operated by Turboman (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service.
            </p>
          </section>

          <section>
            <h2>2. Description of Service</h2>
            <p>
              Turboman provides an AI-powered after-hours answering and dispatch service for trades and service companies. The Service receives inbound phone calls on your behalf, collects caller information, logs service requests, and dispatches notifications to your on-call team via SMS and voice.
            </p>
          </section>

          <section>
            <h2>3. Account Registration</h2>
            <p>
              You must provide accurate and complete information when creating an account. You are responsible for maintaining the confidentiality of your account credentials and for all activity that occurs under your account. You must notify us immediately of any unauthorized use.
            </p>
          </section>

          <section>
            <h2>4. Acceptable Use</h2>
            <p>You agree not to:</p>
            <ul className="list-disc pl-5 space-y-1.5 mt-2">
              <li>Use the Service for any unlawful purpose or in violation of any applicable law</li>
              <li>Interfere with or disrupt the Service or its infrastructure</li>
              <li>Attempt to gain unauthorized access to the Service or related systems</li>
              <li>Use the Service to make calls or send messages that violate anti-spam or telemarketing regulations</li>
              <li>Resell or redistribute the Service without our written consent</li>
            </ul>
          </section>

          <section>
            <h2>5. Fees and Payment</h2>
            <p>
              Certain features of the Service require a paid subscription. Fees are billed monthly in advance. All fees are non-refundable except where required by law. We reserve the right to change pricing with 30 days notice. Your continued use after a price change constitutes acceptance of the new pricing.
            </p>
          </section>

          <section>
            <h2>6. Free Trial</h2>
            <p>
              We may offer a free trial period. At the end of the trial, your access to paid features will be suspended unless you subscribe to a paid plan. We reserve the right to modify or discontinue free trials at any time.
            </p>
          </section>

          <section>
            <h2>7. Call Handling and Dispatch</h2>
            <p>
              The Service uses artificial intelligence to answer calls and collect information. While we strive for accuracy, AI-generated responses may occasionally contain errors. You acknowledge that the Service is not a substitute for emergency services (911) and should not be used for life-threatening situations. We are not liable for missed calls, failed dispatches, or inaccurate information captured during calls.
            </p>
          </section>

          <section>
            <h2>8. Data and Content</h2>
            <p>
              You retain ownership of all data you provide to the Service, including business information, on-call schedules, and knowledge base content. You grant us a limited license to use this data solely to provide the Service. Call transcripts and service request records are stored on your behalf and can be accessed through your dashboard.
            </p>
          </section>

          <section>
            <h2>9. Service Availability</h2>
            <p>
              We aim to provide reliable service but do not guarantee uninterrupted availability. The Service depends on third-party providers including telephony and cloud infrastructure services. We are not liable for downtime caused by factors outside our reasonable control.
            </p>
          </section>

          <section>
            <h2>10. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by law, Turboman shall not be liable for any indirect, incidental, special, consequential, or punitive damages, or any loss of profits or revenue, whether incurred directly or indirectly, or any loss of data, use, or goodwill. Our total aggregate liability for all claims related to the Service shall not exceed the fees you paid in the 12 months preceding the claim.
            </p>
          </section>

          <section>
            <h2>11. Termination</h2>
            <p>
              Either party may terminate at any time. You may cancel your account through the dashboard or by contacting us. We may suspend or terminate your account for violation of these terms. Upon termination, your right to access the Service ceases, and we may delete your data after a 30-day grace period.
            </p>
          </section>

          <section>
            <h2>12. Governing Law</h2>
            <p>
              These Terms are governed by the laws of the Province of British Columbia and the federal laws of Canada applicable therein. Any disputes shall be resolved in the courts of British Columbia.
            </p>
          </section>

          <section>
            <h2>13. Changes to Terms</h2>
            <p>
              We may update these Terms from time to time. We will notify you of material changes via email or through the Service. Your continued use after changes take effect constitutes acceptance of the revised Terms.
            </p>
          </section>

          <section>
            <h2>14. Contact</h2>
            <p>
              If you have questions about these Terms, contact us at{" "}
              <a href="mailto:support@turboman.ca" className="text-slate-900 underline">support@turboman.ca</a>.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
