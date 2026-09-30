import { Leaf } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function LoadingScreen() {
  const { t } = useLanguage();
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center" role="status" aria-live="polite">
      <div className="relative w-24 h-24 mb-6">
        <div className="absolute inset-0 rounded-full border-4 border-leaf-100" />
        <div className="absolute inset-0 rounded-full border-4 border-leaf-600 border-t-transparent animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <Leaf className="text-leaf-600" size={32} />
        </div>
      </div>
      <p className="text-lg font-semibold text-gray-800">{t('analyzing')}</p>
      <p className="text-sm text-gray-500 mt-1">{t('please_wait')}</p>
    </div>
  );
}
