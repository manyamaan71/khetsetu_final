import { useLanguage } from '../context/LanguageContext';

export default function ConfidenceIndicator({ confidence }: { confidence: number }) {
  const { t } = useLanguage();
  const pct = Math.round(confidence * 100);
  const color = pct >= 85 ? '#16a34a' : pct >= 70 ? '#e5b800' : '#dc2626';

  return (
    <div className="flex items-center gap-4" role="img" aria-label={`${t('confidence')}: ${pct}%`}>
      <div className="relative w-20 h-20 shrink-0">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="42" fill="none" stroke="#e5e7eb" strokeWidth="10" />
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${(pct / 100) * 264} 264`}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center font-extrabold text-lg text-gray-800">
          {pct}%
        </div>
      </div>
      <div>
        <p className="text-sm text-gray-500">{t('confidence')}</p>
        <p className="font-semibold text-gray-800">
          {pct >= 85 ? '●●●' : pct >= 70 ? '●●○' : '●○○'}
        </p>
      </div>
    </div>
  );
}
