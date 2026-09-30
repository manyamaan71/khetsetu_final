import { useEffect, useState } from 'react';
import { Globe, Info, LogOut, ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import LanguageSelector from '../components/LanguageSelector';
import Card from '../components/Card';
import Button from '../components/Button';
import { fetchHealth } from '../services/api';
import ModelStatus from '../components/ModelStatus';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

export default function Settings() {
  const { t, availableLanguages } = useLanguage();
  const { profile, signOut } = useAuth();
  const navigate = useNavigate();
  const isOnline = useOnlineStatus();
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [logoutError, setLogoutError] = useState(false);

  useEffect(() => {
    fetchHealth().then((h) => setBackendOk(!!h));
  }, []);

  const handleLogout = async () => {
    setLogoutError(false);
    try {
      await signOut();
      navigate('/login', { replace: true });
    } catch {
      setLogoutError(true);
    }
  };

  return (
    <div className="space-y-4 pt-2">
      <h1 className="text-2xl font-extrabold text-gray-800">{t('settings_title')}</h1>

      <Card>
        <p className="flex items-center gap-2 font-semibold text-gray-700 mb-3">
          <Globe size={18} className="text-leaf-600" /> {t('language')}
        </p>
        <LanguageSelector variant="dropdown" showLabel />
      </Card>

      <Card>
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="flex items-center gap-2 font-semibold text-gray-700">
            <ShieldCheck size={18} className="text-leaf-600" /> {t('settings_profile')}
          </p>
          <Link to="/profile">
            <Button variant="outline" size="md" fullWidth={false}>{t('edit_profile')}</Button>
          </Link>
        </div>

        <div className="space-y-2 text-sm text-gray-600">
          <p><span className="font-semibold text-gray-700">{t('full_name')}:</span> {profile?.full_name || t('not_set')}</p>
          <p>
            <span className="font-semibold text-gray-700">{t('language')}:</span>{' '}
            {availableLanguages.find((l) => l.code === profile?.preferred_language)?.nativeLabel || availableLanguages[0].nativeLabel}
          </p>
          <p><span className="font-semibold text-gray-700">{t('village')}:</span> {profile?.village || t('not_set')}</p>
        </div>
      </Card>

      <Card>
        <p className="flex items-center gap-2 font-semibold text-gray-700 mb-3">
          <ShieldCheck size={18} className="text-leaf-600" /> {t('system_status')}
        </p>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-500 flex items-center gap-2">
              {isOnline ? <Wifi size={16} /> : <WifiOff size={16} />} {t('internet')}
            </span>
            <span className={isOnline ? 'text-leaf-600 font-semibold' : 'text-red-600 font-semibold'}>
              {isOnline ? t('connected') : t('offline')}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-500">{t('model_status')}</span>
            <ModelStatus compact />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-500">{t('backend_server')}</span>
            <span
              className={
                backendOk === null
                  ? 'text-gray-400 font-semibold'
                  : backendOk
                  ? 'text-leaf-600 font-semibold'
                  : 'text-red-600 font-semibold'
              }
            >
              {backendOk === null ? t('checking') : backendOk ? t('connected') : t('unavailable')}
            </span>
          </div>
        </div>
      </Card>

      {logoutError ? <p role="alert" className="text-sm text-red-700">{t('logout_error')}</p> : null}
      <Button variant="outline" icon={<LogOut size={18} />} onClick={() => void handleLogout()}>
        {t('logout_button')}
      </Button>

      <Card className="bg-leaf-50 border-none">
        <p className="flex items-center gap-2 font-semibold text-gray-700 mb-2">
          <Info size={18} className="text-leaf-600" /> {t('about_title')}
        </p>
        <p className="text-sm text-gray-600">{t('about_description')}</p>
      </Card>
    </div>
  );
}
