import { Link } from 'react-router-dom';

export default function TermsPage() {
  return (
    <article className="space-y-5 py-6 text-gray-800">
      <header className="space-y-2">
        <p className="font-bold uppercase tracking-wide text-amber-700">TEMPLATE - needs legal review</p>
        <h1 className="text-3xl font-extrabold">Terms of Use</h1>
      </header>
      <section className="space-y-2">
        <h2 className="text-xl font-bold">Using KhetSetu</h2>
        <p>KhetSetu provides crop-health information, general farming guidance, and market-price information. Use the service lawfully, provide accurate account details, and keep your login credentials secure.</p>
      </section>
      <section className="space-y-2">
        <h2 className="text-xl font-bold">Not a substitute for expert care</h2>
        <p>Results and guidance are general advice, not a lab test, diagnosis, or guarantee. Confirm important crop-health decisions with a qualified local agricultural expert. Market information may be delayed, incomplete, or unavailable; verify prices before making a transaction.</p>
      </section>
      <section className="space-y-2">
        <h2 className="text-xl font-bold">Availability and changes</h2>
        <p>The service is provided as available and may change or be interrupted. These template terms must be completed and reviewed by a qualified legal professional before publication.</p>
      </section>
      <p className="text-sm text-gray-600">Read our <Link to="/privacy" className="underline">Privacy page</Link> for information about profile data and scan photos.</p>
    </article>
  );
}
