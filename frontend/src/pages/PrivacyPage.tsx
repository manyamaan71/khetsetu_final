import { Link } from 'react-router-dom';

export default function PrivacyPage() {
  return (
    <article className="space-y-5 py-6 text-gray-800">
      <header className="space-y-2">
        <p className="font-bold uppercase tracking-wide text-amber-700">TEMPLATE - needs legal review</p>
        <h1 className="text-3xl font-extrabold">Privacy</h1>
      </header>
      <section className="space-y-2">
        <h2 className="text-xl font-bold">Information in your farmer profile</h2>
        <p>The farmer_profiles account record can contain your name, phone number, preferred language, state, district, taluk, village, crops, farm size, and onboarding status, along with account timestamps. It is linked to your Supabase account and protected by access policies intended to limit access to your own profile.</p>
      </section>
      <section className="space-y-2">
        <h2 className="text-xl font-bold">Consent and your choices</h2>
        <p>Before collecting or using profile information, the service should explain its purpose and ask for your clear, informed consent in a language you understand, following applicable data-protection requirements, including India’s Digital Personal Data Protection (DPDP) framework. You should be able to withdraw consent and request correction or deletion as applicable. Final processes and wording require legal review.</p>
      </section>
      <section className="space-y-2">
        <h2 className="text-xl font-bold">Crop scan photos</h2>
        <p>Scan images are processed to generate a crop-health result and are not stored by this service. Your browser may keep scan history on your device. Do not include people or identifying details in photos.</p>
      </section>
      <p className="text-sm text-gray-600">This draft is not legal advice. See <Link to="/terms" className="underline">Terms</Link> and <Link to="/about" className="underline">About</Link>.</p>
    </article>
  );
}
