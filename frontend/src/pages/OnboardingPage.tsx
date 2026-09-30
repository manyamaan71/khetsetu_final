import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, User } from 'lucide-react';
import Button from '../components/Button';
import Card from '../components/Card';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import LanguageSelector from '../components/LanguageSelector';
import { isValidLanguageCode } from '../config/languages';
import { Language, PreferredLanguage } from '../types';

const emptyProfile = {
  full_name: '',
  state: '',
  district: '',
  taluk: '',
  village: '',
  crops: '',
  farm_size: '',
};

export default function OnboardingPage() {
  const { profile, user, updateProfile, isAuthenticated } = useAuth();
  const { language, setLanguage, t, isSavingLanguage } = useLanguage();
  const navigate = useNavigate();
  const [form, setForm] = useState({ ...emptyProfile, preferred_language: (profile?.preferred_language ?? language) as PreferredLanguage });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const initializedProfileId = useRef<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { replace: true });
      return;
    }

    if (profile && profile.onboarding_completed) {
      navigate('/home', { replace: true });
      return;
    }

    if (profile && initializedProfileId.current !== profile.user_id) {
      initializedProfileId.current = profile.user_id;
      setForm({
        full_name: profile.full_name ?? '',
        state: profile.state ?? '',
        district: profile.district ?? '',
        taluk: profile.taluk ?? '',
        village: profile.village ?? '',
        crops: profile.crops?.join(', ') ?? '',
        farm_size: profile.farm_size?.toString() ?? '',
        preferred_language: isValidLanguageCode(profile.preferred_language) ? profile.preferred_language : language,
      });
    } else {
      setForm((current) => ({ ...current, full_name: user?.user_metadata?.full_name ?? current.full_name }));
    }
  }, [isAuthenticated, language, navigate, profile, user?.user_metadata?.full_name]);

  const updateField = (field: keyof typeof emptyProfile | 'preferred_language', value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleContinue = async () => {
    if (!form.full_name.trim()) {
      setStatus(t('auth_name_required'));
      return;
    }

    const farmSize = form.farm_size.trim() === '' ? null : Number(form.farm_size.trim());
    if (farmSize !== null && (!Number.isFinite(farmSize) || farmSize < 0)) {
      setStatus(t('profile_farm_size_invalid'));
      return;
    }

    setSaving(true);
    setStatus(null);

    try {
      await updateProfile({
        full_name: form.full_name.trim(),
        preferred_language: form.preferred_language,
        state: form.state.trim() || null,
        district: form.district.trim() || null,
        taluk: form.taluk.trim() || null,
        village: form.village.trim() || null,
        crops: form.crops.split(',').map((crop) => crop.trim()).filter(Boolean),
        farm_size: farmSize,
        onboarding_completed: true,
      });
      setStatus(t('profile_save_success'));
      navigate('/home', { replace: true });
    } catch (error) {
      if (error instanceof Error && error.message === 'AUTH_REQUIRED') {
        setStatus(t('auth_save_session_expired'));
      } else {
        setStatus(t('profile_save_error'));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl space-y-6 py-6">
      <Card>
        <div className="flex items-center gap-2 text-leaf-700">
          <User size={18} />
          <span className="font-bold">{t('welcome')}</span>
        </div>
        <h1 className="mt-3 text-2xl font-extrabold text-gray-800">{t('farmer_profile_setup')}</h1>

        <div className="mt-5 space-y-4">
          <div className="space-y-1.5">
            <label className="block text-sm font-semibold text-gray-700">{t('choose_language')}</label>
            <LanguageSelector
              variant="dropdown"
              value={form.preferred_language as Language}
              onChange={(lang) => {
                updateField('preferred_language', lang);
                void setLanguage(lang);
              }}
            />
            <p className="text-xs text-leaf-700 font-medium mt-1">{t('change_language_anytime')}</p>
          </div>

          <label className="block text-sm font-semibold text-gray-700">{t('full_name')}</label>
          <input value={form.full_name} onChange={(e) => updateField('full_name', e.target.value)} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-semibold text-gray-700">{t('state')}</label>
              <input value={form.state} onChange={(e) => updateField('state', e.target.value)} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700">{t('district')}</label>
              <input value={form.district} onChange={(e) => updateField('district', e.target.value)} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-semibold text-gray-700">{t('taluk')}</label>
              <input value={form.taluk} onChange={(e) => updateField('taluk', e.target.value)} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700">{t('village')}</label>
              <input value={form.village} onChange={(e) => updateField('village', e.target.value)} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-semibold text-gray-700">{t('main_crop')}</label>
              <input value={form.crops} onChange={(e) => updateField('crops', e.target.value)} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700">{t('farm_size')}</label>
              <input value={form.farm_size} onChange={(e) => updateField('farm_size', e.target.value)} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
          </div>

          {status ? <div className="rounded-2xl bg-amber-50 p-3 text-sm text-amber-800">{status}</div> : null}

          <Button onClick={handleContinue} disabled={saving || isSavingLanguage} icon={<ArrowRight size={18} />}>
            {saving ? t('please_wait') : t('continue')}
          </Button>
        </div>
      </Card>
    </div>
  );
}
