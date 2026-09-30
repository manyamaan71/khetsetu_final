import { WifiOff } from 'lucide-react';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { useLanguage } from '../context/LanguageContext';

export default function OfflineBanner() {
  const isOnline = useOnlineStatus();
  const { t } = useLanguage();

  if (isOnline) return null;

  return (
    <div
      role="status"
      className="flex items-center gap-2 bg-amber-100 text-amber-900 text-sm font-medium px-4 py-2 justify-center"
    >
      <WifiOff size={16} />
      {t('offline_banner')}
    </div>
  );
}
