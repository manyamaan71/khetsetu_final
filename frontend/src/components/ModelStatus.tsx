import { useEffect, useState } from 'react';
import { Cpu, FlaskConical, ServerOff } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { fetchHealth } from '../services/api';
import { HealthInfo } from '../types';

/** Shows whether the scanner is the real trained model, Demo Mode, or not reachable. */
export default function ModelStatus({ compact = false }: { compact?: boolean }) {
  const { t } = useLanguage();
  const [health, setHealth] = useState<HealthInfo | null | undefined>(undefined);

  useEffect(() => { fetchHealth().then(setHealth); }, []);
  if (health === undefined) return null;

  let label = t('status_server_down');
  let cls = 'bg-gray-100 text-gray-600';
  let Icon = ServerOff;
  if (health?.model.mode === 'real') { label = t('status_real'); cls = 'bg-leaf-100 text-leaf-800'; Icon = Cpu; }
  else if (health?.model.mode === 'demo') { label = t('status_demo'); cls = 'bg-amber-100 text-amber-800'; Icon = FlaskConical; }
  else if (health) { label = t('status_model_missing'); cls = 'bg-red-100 text-red-700'; Icon = ServerOff; }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold ${cls} ${compact ? 'text-[11px] px-2.5 py-1' : 'text-xs px-3 py-1.5'}`}
      role="status" aria-label={`${t('model_status')}: ${label}`}>
      <Icon size={compact ? 12 : 14} /> {label}
    </span>
  );
}
