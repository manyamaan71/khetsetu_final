import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertTriangle, MapPin } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import Card from '../components/Card';
import { fetchMarketPrices, ApiError } from '../services/api';
import { MarketResponse } from '../types';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { localizedCropName } from '../config/agricultureTerms';

const CROPS = ['Tomato', 'Potato', 'Maize'];
const STATES = ['Karnataka', 'Maharashtra', 'Uttar Pradesh', 'Punjab', 'Himachal Pradesh'];

export default function Market() {
  const { t, language } = useLanguage();
  const isOnline = useOnlineStatus();
  const [params] = useSearchParams();
  const initialCrop = CROPS.includes(params.get('crop') ?? '') ? (params.get('crop') as string) : '';
  const [crop, setCrop] = useState(initialCrop);
  const [state, setState] = useState('');
  const [data, setData] = useState<MarketResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchMarketPrices({ crop: crop || undefined, state: state || undefined, language }));
    } catch (err) {
      if (err instanceof ApiError && (err.code === 'offline' || err.code === 'network')) setError(t(isOnline ? 'error_network' : 'market_offline'));
      else if (err instanceof ApiError && err.code === 'timeout') setError(t('error_timeout'));
      else setError(t('error_server'));
      setData(null);      // never keep showing numbers we could not refresh
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [crop, language, state]);

  return (
    <div className="space-y-4 pt-2">
      <h1 className="text-2xl font-extrabold text-gray-800">{t('market_title')}</h1>

      {!isOnline && (
        <div className="bg-red-50 text-red-700 text-sm font-semibold text-center py-2 rounded-xl">{t('market_offline')}</div>
      )}
      {data && !loading && data.source === 'live' && (
        <div className="bg-leaf-100 text-leaf-800 text-xs font-bold text-center py-1.5 rounded-full">{t('market_live')}</div>
      )}
      {data && !loading && data.source === 'cached' && (
        <div role="status" className="bg-amber-100 text-amber-900 text-sm font-bold text-center py-2 rounded-xl">
          {data.message?.[language] || t('market_cached')}
        </div>
      )}
      {data?.source === 'unavailable' && !loading && (
        <div role="status" className="bg-red-50 text-red-700 text-sm font-semibold text-center py-2 rounded-xl">{data.message?.[language] || t('dashboard_market_unavailable')}</div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <select
          value={crop}
          onChange={(e) => setCrop(e.target.value)}
          className="rounded-xl border border-leaf-200 px-3 py-3 text-sm font-medium bg-white min-h-[44px]"
          aria-label={t('select_crop')}
        >
          <option value="">{t('select_crop')}</option>
          {CROPS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={state}
          onChange={(e) => setState(e.target.value)}
          className="rounded-xl border border-leaf-200 px-3 py-3 text-sm font-medium bg-white min-h-[44px]"
          aria-label={t('select_state')}
        >
          <option value="">{t('select_state')}</option>
          {STATES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="flex items-start gap-2 bg-red-50 text-red-700 rounded-xl p-4 text-sm font-medium">
          <AlertTriangle size={18} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-white rounded-2xl animate-pulse border border-leaf-100" />
          ))}
        </div>
      ) : (data?.rows.length ?? 0) === 0 && !error && data?.source !== 'unavailable' ? (
        <Card className="text-center py-10 text-gray-500">{t('market_none')}</Card>
      ) : (
        <div className="space-y-3">
          {(data?.rows ?? []).map((row, i) => (
            <Card key={i}>
              <div className="flex items-center justify-between mb-2">
                <p className="font-bold text-gray-800">{localizedCropName(row.crop, language)}</p>
                <p className="text-xs text-gray-400">{row.date}</p>
              </div>
              <p className="flex items-center gap-1 text-sm text-gray-500 mb-3">
                <MapPin size={14} /> {row.market}, {row.district}, {row.state}
              </p>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-leaf-50 rounded-xl py-2">
                  <p className="text-[11px] text-gray-500">{t('min_price')}</p>
                  <p className="font-bold text-gray-800">₹{row.min_price}</p>
                </div>
                <div className="bg-wheat-400/20 rounded-xl py-2">
                  <p className="text-[11px] text-gray-500">{t('modal_price')}</p>
                  <p className="font-bold text-gray-800">₹{row.modal_price}</p>
                </div>
                <div className="bg-leaf-50 rounded-xl py-2">
                  <p className="text-[11px] text-gray-500">{t('max_price')}</p>
                  <p className="font-bold text-gray-800">₹{row.max_price}</p>
                </div>
              </div>
              <p className="text-[11px] text-gray-400 mt-2 text-right">{t('per_quintal')}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
