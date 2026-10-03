import { useLanguage } from '../context/LanguageContext';
import Card from '../components/Card';
import { Bi } from '../types';
// Same file the backend serves at /api/crops. Bundled here so crop information works fully offline.
import cropsData from '../../../data/crops.json';

interface CropInfo {
  crop: string;
  name: Bi;
  healthy_characteristics: Bi;
  diseases_in_dataset: { class_name: string; name: Bi }[];
  basic_care: Bi<string[]>;
  important_nutrients: Bi<string[]>;
  prevention_tips: Bi<string[]>;
  source_note: Bi;
}

const CROPS = Object.values(cropsData as unknown as Record<string, CropInfo>);

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="mt-3">
      <p className="text-sm font-semibold text-gray-700 mb-1">{title}</p>
      <ul className="space-y-1 text-sm text-gray-600 list-disc list-inside">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
}

export default function Advisory() {
  const { t, language: l } = useLanguage();
  return (
    <div className="space-y-4 pt-2">
      <h1 className="text-2xl font-extrabold text-gray-800">{t('advisory_title')}</h1>
      <p className="text-gray-500 text-sm">{t('advisory_intro')}</p>
      <div className="space-y-3">
        {CROPS.map((c) => (
          <Card key={c.crop}>
            <p className="font-extrabold text-lg text-leaf-800">{c.name[l]}</p>
            <p className="text-sm text-gray-600 mt-2"><span className="font-semibold text-gray-700">{t('adv_healthy_looks')}: </span>{c.healthy_characteristics[l]}</p>
            <List title={t('adv_diseases')} items={c.diseases_in_dataset.map((d) => d.name[l])} />
            <List title={t('adv_care')} items={c.basic_care[l]} />
            <List title={t('adv_nutrients')} items={c.important_nutrients[l]} />
            <List title={t('adv_prevention')} items={c.prevention_tips[l]} />
            <p className="text-[11px] text-gray-400 mt-3">{c.source_note[l]}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
