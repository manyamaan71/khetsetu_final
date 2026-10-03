export default function AboutPage() {
  return (
    <article className="space-y-5 py-6 text-gray-800">
      <header className="space-y-2">
        <p className="font-bold uppercase tracking-wide text-amber-700">TEMPLATE - needs legal review</p>
        <h1 className="text-3xl font-extrabold">About KhetSetu</h1>
      </header>
      <p>KhetSetu is a farming assistant for crop-health information, practical guidance, and market prices.</p>
      <section className="space-y-2">
        <h2 className="text-xl font-bold">Dataset attribution</h2>
        <p>PlantVillage dataset by spMohanty, licensed under CC BY-SA 3.0: <a href="https://github.com/spMohanty/PlantVillage-Dataset" target="_blank" rel="noreferrer" className="break-all underline">https://github.com/spMohanty/PlantVillage-Dataset</a>.</p>
      </section>
      <p className="rounded-xl bg-amber-50 p-4 font-semibold">KhetSetu results are general advice, not a lab test. Consult a qualified agricultural expert for important decisions.</p>
    </article>
  );
}
