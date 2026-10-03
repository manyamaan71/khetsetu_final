import { Link, Navigate } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Sprout } from 'lucide-react';
import Button from '../components/Button';
import Card from '../components/Card';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import LanguageSelector from '../components/LanguageSelector';

export default function LandingPage() {
  const { isAuthenticated, profile } = useAuth();
  const { t } = useLanguage();

  if (isAuthenticated) {
    return <Navigate to={profile && profile.onboarding_completed === false ? '/onboarding' : '/home'} replace />;
  }

  return (
    <div className="space-y-6 py-6">
      <div className="rounded-3xl bg-gradient-to-br from-leaf-700 to-leaf-500 p-6 text-white">
        <div className="flex items-center gap-3">
          <span className="rounded-2xl bg-white/15 p-3"><Sprout size={24} /></span>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-leaf-100">KhetSetu</p>
            <h1 className="text-3xl font-extrabold">{t('landing_welcome')}</h1>
          </div>
        </div>
        <p className="mt-4 text-base text-leaf-50">{t('hero_subtext')}</p>
      </div>

      <Card>
        <h2 className="mb-3 text-lg font-extrabold text-gray-800">{t('choose_language')}</h2>
        <LanguageSelector variant="dropdown" />
      </Card>

      <Card className="bg-leaf-50 border-none">
        <div className="mb-3 flex items-center gap-2 text-gray-700">
          <ShieldCheck size={18} className="text-leaf-600" />
          <span className="font-semibold">{t('login_title')}</span>
        </div>
        <p className="text-sm text-gray-600">{t('auth_intro')}</p>
      </Card>

      <div className="space-y-3">
        <Link to="/signup">
          <Button icon={<ArrowRight size={18} />}>{t('create_account')}</Button>
        </Link>
        <Link to="/login">
          <Button variant="outline">{t('login_button')}</Button>
        </Link>
      </div>
      <nav aria-label="Information" className="flex justify-center gap-4 pb-2 text-sm text-leaf-800">
        <Link to="/about" className="underline">About</Link>
        <Link to="/privacy" className="underline">Privacy</Link>
        <Link to="/terms" className="underline">Terms</Link>
      </nav>
    </div>
  );
}
