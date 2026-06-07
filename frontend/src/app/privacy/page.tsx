import Link from "next/link";
import { Zap } from "lucide-react";

export const metadata = { title: "Privacy Policy — Turboman" };

export default function PrivacyPage() {
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
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Privacy Policy</h1>
        <p className="text-sm text-slate-500 mb-12">Last updated: June 18, 2026</p>

        <div className="prose prose-slate prose-sm max-w-none space-y-8 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-slate-900 [&_h2]:mb-3 [&_p]:text-slate-600 [&_p]:leading-relaxed [&_li]:text-slate-600">
          <section>
            <h2>1. Introduction</h2>
            <p>
              Turboman (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard information when you use our AI-powered after-hours answering and dispatch service. We comply with the Personal Information Protection and Electronic Documents Act (PIPEDA) and the British Columbia Personal Information Protection Act (PIPA).
            </p>
          </section>

          <section>
            <h2>2. Information We Collect</h2>

            <p className="font-medium text-slate-800 mt-4 mb-1">Account Information</p>
            <p>When you register, we collect your name, email address, company name, phone numbers, and payment information.</p>

            <p className="font-medium text-slate-800 mt-4 mb-1">Call Data</p>
            <p>When callers reach your Turboman number, we collect the caller&apos;s phone number, name, address, and the details of their service request as provided during the call. Call audio is processed in real-time for speech-to-text transcription but is not recorded or stored.</p>

            <p className="font-medium text-slate-800 mt-4 mb-1">Service Request Data</p>
            <p>We store transcripts and structured summaries of service requests, including caller name, address, issue description, and urgency classification.</p>

            <p className="font-medium text-slate-800 mt-4 mb-1">On-Call Team Data</p>
            <p>We store the names and phone numbers of on-call technicians you add to the system for dispatch purposes.</p>

            {/* <p className="font-medium text-slate-800 mt-4 mb-1">Usage Data</p>
            <p>We collect standard usage data such as IP addresses, browser type, and pages visited to maintain and improve the Service.</p> */}
          </section>

          <section>
            <h2>3. How We Use Your Information</h2>
            <p>We use the information we collect to:</p>
            <ul className="list-disc pl-5 space-y-1.5 mt-2">
              <li>Provide and operate the Service, including answering calls and dispatching your on-call team</li>
              <li>Process AI-powered conversations with callers on your behalf</li>
              <li>Send dispatch notifications to your on-call technicians via SMS and voice</li>
              <li>Display service request history and call transcripts in your dashboard</li>
              <li>Send account-related communications such as verification emails and billing notices</li>
              <li>Maintain, improve, and troubleshoot the Service</li>
            </ul>
          </section>

          <section>
            <h2>4. Third-Party Service Providers</h2>
            <p>We use the following categories of third-party services to operate Turboman. These providers process data on our behalf and are bound by contractual obligations to protect your information:</p>
            <ul className="list-disc pl-5 space-y-1.5 mt-2">
              <li><span className="text-slate-800 font-medium">Telephony</span> — for call handling, SMS delivery, and voice dispatch</li>
              <li><span className="text-slate-800 font-medium">Speech-to-text</span> — for real-time transcription of caller speech</li>
              <li><span className="text-slate-800 font-medium">Text-to-speech</span> — for generating AI voice responses</li>
              <li><span className="text-slate-800 font-medium">AI language model</span> — for understanding caller requests and generating responses</li>
              <li><span className="text-slate-800 font-medium">Email delivery</span> — for sending account verification and notification emails</li>
              <li><span className="text-slate-800 font-medium">Cloud hosting</span> — for hosting the application and database</li>
            </ul>
            <p className="mt-3">We do not sell your personal information to third parties.</p>
          </section>

          <section>
            <h2>5. Data Retention</h2>
            <p>
              We retain your account information and service request data for as long as your account is active. Call transcripts and service request records are retained indefinitely unless you request deletion. Upon account termination, we retain your data for 30 days to allow for reactivation, after which it is permanently deleted.
            </p>
          </section>

          <section>
            <h2>6. Data Security</h2>
            <p>
              We implement appropriate technical and organizational measures to protect your information, including encryption in transit (TLS), secure authentication with hashed passwords, and access controls. However, no method of electronic transmission or storage is 100% secure, and we cannot guarantee absolute security.
            </p>
          </section>

          <section>
            <h2>7. Your Rights</h2>
            <p>Under Canadian privacy law, you have the right to:</p>
            <ul className="list-disc pl-5 space-y-1.5 mt-2">
              <li>Access the personal information we hold about you</li>
              <li>Request correction of inaccurate information</li>
              <li>Request deletion of your personal information</li>
              <li>Withdraw consent for data processing (which may limit your ability to use the Service)</li>
              <li>File a complaint with the Office of the Privacy Commissioner of Canada</li>
            </ul>
            <p className="mt-3">To exercise these rights, contact us at <a href="mailto:support@turboman.ca" className="text-slate-900 underline">support@turboman.ca</a>.</p>
          </section>

          <section>
            <h2>8. Caller Privacy</h2>
            <p>
              When someone calls a Turboman-powered number, they are interacting with an AI system acting on behalf of our customer (the business). The caller&apos;s phone number and any information they provide during the call is collected and stored as part of the service request. Businesses using Turboman are responsible for informing their own customers about how their data is handled through the Service.
            </p>
          </section>

          <section>
            <h2>9. Cookies and Tracking</h2>
            <p>
              We use essential cookies required for authentication and session management. We do not use third-party advertising or tracking cookies.
            </p>
          </section>

          <section>
            <h2>10. Children&apos;s Privacy</h2>
            <p>
              The Service is not intended for individuals under 18 years of age. We do not knowingly collect personal information from children.
            </p>
          </section>

          <section>
            <h2>11. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of material changes via email or through the Service. The &quot;Last updated&quot; date at the top indicates the most recent revision.
            </p>
          </section>

          <section>
            <h2>12. Contact</h2>
            <p>
              If you have questions or concerns about this Privacy Policy or our data practices, contact us at{" "}
              <a href="mailto:support@turboman.ca" className="text-slate-900 underline">support@turboman.ca</a>.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
