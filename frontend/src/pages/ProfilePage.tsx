import { useEffect, useRef, useState } from 'react';
import { Save } from 'lucide-react';
import Button from '../components/Button';
import Card from '../components/Card';
import LanguageSelector from '../components/LanguageSelector';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';

export default function ProfilePage() {
  const { profile, updateProfile } = useAuth();
  const { t } = useLanguage();
  const [form, setForm] = useState({
    full_name: '',
    state: '',
    district: '',
    taluk: '',
    village: '',
    crops: '',
    farm_size: '',
  });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const initializedProfileId = useRef<string | null>(null);

  useEffect(() => {
    if (!profile || initializedProfileId.current === profile.user_id) return;
    initializedProfileId.current = profile.user_id;
    setForm({
      full_name: profile.full_name ?? '',
      state: profile.state ?? '',
      district: profile.district ?? '',
      taluk: profile.taluk ?? '',
      village: profile.village ?? '',
      crops: profile.crops?.join(', ') ?? '',
      farm_size: profile.farm_size?.toString() ?? '',
    });
  }, [profile]);

  const handleSave = async () => {
    const farmSize = form.farm_size.trim() === '' ? null : Number(form.farm_size.trim());
    if (farmSize !== null && (!Number.isFinite(farmSize) || farmSize < 0)) {
      setStatus(t('profile_farm_size_invalid'));
      return;
    }

    setSaving(true);
    setStatus(null);
    try {
      await updateProfile({
        ...form,
        state: form.state.trim() || null,
        district: form.district.trim() || null,
        taluk: form.taluk.trim() || null,
        village: form.village.trim() || null,
        crops: form.crops.split(',').map((crop) => crop.trim()).filter(Boolean),
        farm_size: farmSize,
      });
      setStatus(t('profile_update_success'));
    } catch {
      setStatus(t('profile_update_error'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4 py-4">
      <h1 className="text-2xl font-extrabold text-gray-800">{t('profile_title')}</h1>
      <Card>
        <div className="space-y-4">
          <div className="space-y-1.5 mb-2">
            <label className="block text-sm font-semibold text-gray-700">{t('choose_language')}</label>
            <LanguageSelector variant="dropdown" />
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-gray-700">{t('full_name')}</label>
            <input value={form.full_name} onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">{t('state')}</label>
              <input value={form.state} onChange={(e) => setForm((p) => ({ ...p, state: e.target.value }))} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">{t('district')}</label>
              <input value={form.district} onChange={(e) => setForm((p) => ({ ...p, district: e.target.value }))} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">{t('taluk')}</label>
              <input value={form.taluk} onChange={(e) => setForm((p) => ({ ...p, taluk: e.target.value }))} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">{t('village')}</label>
              <input value={form.village} onChange={(e) => setForm((p) => ({ ...p, village: e.target.value }))} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">{t('main_crop')}</label>
              <input value={form.crops} onChange={(e) => setForm((p) => ({ ...p, crops: e.target.value }))} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">{t('farm_size')}</label>
              <input value={form.farm_size} onChange={(e) => setForm((p) => ({ ...p, farm_size: e.target.value }))} className="w-full rounded-2xl border border-gray-200 px-4 py-3" />
            </div>
          </div>

          {status ? <div className="rounded-2xl bg-leaf-50 p-3 text-sm text-leaf-700">{status}</div> : null}

          <Button onClick={handleSave} disabled={saving} icon={<Save size={18} />}>
            {saving ? t('please_wait') : t('save_profile')}
          </Button>
        </div>
      </Card>
    </div>
  );
}
