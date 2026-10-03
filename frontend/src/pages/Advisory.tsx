import { useLanguage } from '../context/LanguageContext';
import Card from '../components/Card';
import { Language } from '../types';
// Same file the backend serves at /api/crops. Bundled here so crop information works fully offline.
import cropsData from '../../../data/crops.json';

interface CropInfo {
  crop: string;
  name: Record<string, string>;
  healthy_characteristics: Record<string, string>;
  diseases_in_dataset: { class_name: string; name: Record<string, string> }[];
  basic_care: Record<string, string[]>;
  important_nutrients: Record<string, string[]>;
  prevention_tips: Record<string, string[]>;
  source_note: Record<string, string>;
}

const CROPS = Object.values(cropsData as unknown as Record<string, CropInfo>);

// Safe helper to resolve single strings for any selected language code
function getLocalizedText(obj: Record<string, string> | undefined, lang: Language): string {
  if (!obj) return '';
  return obj[lang] ?? obj['en'] ?? obj['hi'] ?? Object.values(obj)[0] ?? '';
}

// Safe helper to resolve array lists for any selected language code
function getLocalizedList(obj: Record<string, string[]> | undefined, lang: Language): string[] {
  if (!obj) return [];
  const val = obj[lang] ?? obj['en'] ?? obj['hi'] ?? Object.values(obj)[0];
  if (Array.isArray(val)) return val;
  if (typeof val === 'string' && val) return [val];
  return [];
}

function List({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="text-sm font-semibold text-gray-700 mb-1">{title}</p>
      <ul className="space-y-1 text-sm text-gray-600 list-disc list-inside">
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
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
        {CROPS.map((c) => {
          const cropName = getLocalizedText(c.name, l);
          const healthyChar = getLocalizedText(c.healthy_characteristics, l);
          const diseases = (c.diseases_in_dataset || []).map((d) => getLocalizedText(d.name, l));
          const basicCare = getLocalizedList(c.basic_care, l);
          const nutrients = getLocalizedList(c.important_nutrients, l);
          const prevention = getLocalizedList(c.prevention_tips, l);
          const sourceNote = getLocalizedText(c.source_note, l);

          return (
            <Card key={c.crop}>
              <p className="font-extrabold text-lg text-leaf-800">{cropName}</p>
              
              {healthyChar && (
                <p className="text-sm text-gray-600 mt-2">
                  <span className="font-semibold text-gray-700">{t('adv_healthy_looks')}: </span>
                  {healthyChar}
                </p>
              )}

              <List title={t('adv_diseases')} items={diseases} />
              <List title={t('adv_care')} items={basicCare} />
              <List title={t('adv_nutrients')} items={nutrients} />
              <List title={t('adv_prevention')} items={prevention} />
              
              {sourceNote && (
                <p className="text-[11px] text-gray-400 mt-3">{sourceNote}</p>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}