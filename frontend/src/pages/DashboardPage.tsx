import { Link } from 'react-router-dom';
import { Camera, History, LineChart, MapPinned, Sprout, UserRound } from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import LanguageSelector from '../components/LanguageSelector';

export default function DashboardPage() {
  const { profile, signOut } = useAuth();
  const { t } = useLanguage();

  const quickActions = [
    { to: '/scan', icon: Camera, label: t('scan_crop') },
    { to: '/market', icon: LineChart, label: t('check_market') },
    { to: '/history', icon: History, label: t('my_history') },
    { to: '/advisory', icon: Sprout, label: t('crop_advisory') },
  ];

  return (
    <div className="space-y-5 py-4">
      <Card className="bg-gradient-to-r from-leaf-600 to-leaf-800 text-white border-none">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-leaf-100">{t('welcome')}</p>
            <h1 className="mt-2 text-2xl font-extrabold">{profile?.full_name || t('farmer_fallback')}</h1>
          </div>
          <div className="flex items-center gap-2">
            <LanguageSelector variant="compact" />
            <div className="rounded-2xl bg-white/10 p-2.5"><UserRound size={22} /></div>
          </div>
        </div>
        <p className="mt-3 text-sm text-leaf-50">{t('dashboard_prompt')}</p>
      </Card>

      <div className="grid grid-cols-2 gap-3">
        {quickActions.map(({ to, icon: Icon, label }) => (
          <Link key={to} to={to}>
            <Card className="h-full flex flex-col items-center justify-center gap-2 py-6 text-center">
              <span className="rounded-2xl bg-leaf-100 p-3 text-leaf-700"><Icon size={22} /></span>
              <span className="font-semibold text-gray-700">{label}</span>
            </Card>
          </Link>
        ))}
      </div>

      <Card>
        <div className="flex items-center gap-2 text-gray-800 font-bold">
          <MapPinned size={18} className="text-leaf-600" />
          {t('your_farm')}
        </div>
        <div className="mt-3 space-y-2 text-sm text-gray-600">
          <p>{profile?.village || t('label_village')} · {profile?.district || t('label_district')} · {profile?.state || t('label_state')}</p>
          <p>{profile?.crops?.join(', ') || 'Main crop'} · {profile?.farm_size || 'Farm size'}</p>
        </div>
      </Card>

      <div className="space-y-3">
        <Link to="/settings">
          <Button variant="outline">{t('nav_settings')}</Button>
        </Link>
        <Button variant="ghost" onClick={() => void signOut()}>{t('logout_button')}</Button>
      </div>
    </div>
  );
}
