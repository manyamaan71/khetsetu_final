import { useEffect, useState } from 'react';
import { Globe, Info, ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import Card from '../components/Card';
import { fetchHealth } from '../services/api';
import ModelStatus from '../components/ModelStatus';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

export default function Settings() {
  const { t, language, setLanguage } = useLanguage();
  const isOnline = useOnlineStatus();
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    fetchHealth().then((h) => setBackendOk(!!h));
  }, []);

  return (
    <div className="space-y-4 pt-2">
      <h1 className="text-2xl font-extrabold text-gray-800">{t('settings_title')}</h1>

      <Card>
        <p className="flex items-center gap-2 font-semibold text-gray-700 mb-3">
          <Globe size={18} className="text-leaf-600" /> {t('language')}
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => setLanguage('en')}
            className={`flex-1 py-3 rounded-xl font-semibold min-h-[44px] ${
              language === 'en' ? 'bg-leaf-600 text-white' : 'bg-leaf-50 text-gray-600'
            }`}
          >
            English
          </button>
          <button
            onClick={() => setLanguage('hi')}
            className={`flex-1 py-3 rounded-xl font-semibold min-h-[44px] ${
              language === 'hi' ? 'bg-leaf-600 text-white' : 'bg-leaf-50 text-gray-600'
            }`}
          >
            हिंदी
          </button>
        </div>
      </Card>

      <Card>
        <p className="flex items-center gap-2 font-semibold text-gray-700 mb-3">
          <ShieldCheck size={18} className="text-leaf-600" /> System Status
        </p>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-500 flex items-center gap-2">
              {isOnline ? <Wifi size={16} /> : <WifiOff size={16} />} Internet
            </span>
            <span className={isOnline ? 'text-leaf-600 font-semibold' : 'text-red-600 font-semibold'}>
              {isOnline ? 'Connected' : 'Offline'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-500">{t('model_status')}</span>
            <ModelStatus compact />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Backend server</span>
            <span
              className={
                backendOk === null
                  ? 'text-gray-400 font-semibold'
                  : backendOk
                  ? 'text-leaf-600 font-semibold'
                  : 'text-red-600 font-semibold'
              }
            >
              {backendOk === null ? 'Checking…' : backendOk ? 'Connected' : 'Unavailable'}
            </span>
          </div>
        </div>
      </Card>

      <Card className="bg-leaf-50 border-none">
        <p className="flex items-center gap-2 font-semibold text-gray-700 mb-2">
          <Info size={18} className="text-leaf-600" /> About KhetSetu
        </p>
        <p className="text-sm text-gray-600">
          KhetSetu helps farmers identify crop leaf diseases from a photo and get simple treatment guidance in
          English and Hindi. Version 2.0.
        </p>
      </Card>
    </div>
  );
}
