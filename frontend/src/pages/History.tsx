import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Trash2, Sprout, Leaf } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import Card from '../components/Card';
import Button from '../components/Button';
import { getHistory, clearHistory, saveLastResult } from '../services/storageService';
import { HistoryItem } from '../types';

export default function History() {
  const { t, language } = useLanguage();
  const navigate = useNavigate();
  const [items, setItems] = useState<HistoryItem[]>([]);

  useEffect(() => {
    setItems(getHistory());
  }, []);

  const handleClear = () => {
    if (!window.confirm(t('clear_history_confirm'))) return;
    clearHistory();
    setItems([]);
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(language === 'hi' ? 'hi-IN' : 'en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });

  return (
    <div className="space-y-4 pt-2">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-extrabold text-gray-800">{t('history_title')}</h1>
        {items.length > 0 && (
          <button
            onClick={handleClear}
            className="flex items-center gap-1 text-red-600 text-sm font-semibold min-h-[44px] px-2"
          >
            <Trash2 size={16} /> {t('clear_history')}
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <Card className="text-center py-12 text-gray-500">
          <Leaf className="mx-auto mb-3 text-leaf-300" size={40} />
          {t('no_history')}
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.id} className="flex items-center gap-4">
              {item.thumbnail ? (
                <img
                  src={item.thumbnail}
                  alt={`${item.crop} scan thumbnail`}
                  className="w-14 h-14 rounded-xl object-cover shrink-0"
                />
              ) : (
                <div className="w-14 h-14 rounded-xl bg-leaf-100 flex items-center justify-center shrink-0">
                  <Sprout size={22} className="text-leaf-600" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-400">{formatDate(item.date)}</p>
                <p className="font-semibold text-gray-800 truncate">
                  {language === 'hi' ? item.hindi_crop : item.crop}
                </p>
                <p className={`text-sm truncate ${item.is_healthy ? 'text-leaf-600' : 'text-amber-700'}`}>
                  {item.is_healthy ? t('healthy_leaf') : language === 'hi' ? item.hindi_disease : item.disease}
                </p>
              </div>
              <div className="text-right shrink-0 space-y-1">
                <p className="font-extrabold text-gray-700">{Math.round(item.confidence * 100)}%</p>
                {item.result && (
                  <button
                    onClick={() => { saveLastResult(item.result); navigate('/result'); }}
                    className="text-leaf-700 text-sm font-semibold min-h-[44px] px-2"
                  >
                    {t('view_result')}
                  </button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {items.length === 0 && (
        <Link to="/scan">
          <Button>{t('scan_crop')}</Button>
        </Link>
      )}
    </div>
  );
}
