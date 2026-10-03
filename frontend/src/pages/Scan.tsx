import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, ImagePlus, X, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import Button from '../components/Button';
import Card from '../components/Card';
import LoadingScreen from '../components/LoadingScreen';
import { compressImage, predictCrop, validateImageType, ApiError } from '../services/api';
import ModelStatus from '../components/ModelStatus';
import { saveLastResult, saveCurrentScanImage, addHistoryItem, makeThumbnail } from '../services/storageService';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { localName } from '../types';

export default function Scan() {
  const { t, language } = useLanguage();
  const navigate = useNavigate();
  const isOnline = useOnlineStatus();

  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const handleFileChosen = (f: File | undefined) => {
    setError(null);
    if (!f) return;
    try {
      validateImageType(f);            // type + sanity size; big phone photos are compressed before upload
    } catch (e) {
      setError(t(e instanceof ApiError && e.code === 'too_large' ? 'error_too_large' : 'error_invalid_image'));
      return;
    }
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
  };

  const clearImage = () => {
    setFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setError(null);
  };

  const handleScan = async () => {
    if (!file) {
      setError(t('error_no_image'));
      return;
    }
    if (!isOnline) {
      setError(t('error_offline_scan'));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await predictCrop(file, language);
      const scanId = crypto.randomUUID();
      const reportImage = await compressImage(file).catch(() => file);
      await saveCurrentScanImage(scanId, reportImage).catch(() => undefined);
      saveLastResult({ ...result, client_scan_id: scanId });

      const thumbnail = await makeThumbnail(file).catch(() => undefined);
      if (result.is_confident) {          // history only stores real, confident predictions
        addHistoryItem({
          id: `${Date.now()}`,
          date: new Date().toISOString(),
          crop: localName(result.prediction, 'crop', 'en'),
          disease: localName(result.prediction, 'disease', 'en'),
          hindi_crop: localName(result.prediction, 'crop', 'hi'),
          hindi_disease: localName(result.prediction, 'disease', 'hi'),
          crop_i18n: result.prediction.crop_i18n,
          disease_i18n: result.prediction.disease_i18n,
          confidence: result.prediction.confidence,
          is_healthy: result.prediction.is_healthy,
          is_confident: true,
          thumbnail,
          result,
        });
      }
      navigate('/result');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'network') setError(t('error_network'));
        else if (err.code === 'offline') setError(t('error_offline_scan'));
        else if (err.code === 'timeout') setError(t('error_timeout'));
        else if (err.code === 'model_unavailable') setError(t('error_model'));
        else if (err.code === 'invalid_image') setError(t('error_invalid_image'));
        else if (err.code === 'too_large') setError(t('error_too_large'));
        else setError(t('error_server'));
      } else {
        setError(t('error_server'));
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingScreen />;

  return (
    <div className="space-y-5 pt-2">
      <div>
        <h1 className="text-2xl font-extrabold text-gray-800">{t('scan_title')}</h1>
        <p className="text-gray-500 mt-1">{t('scan_instructions')}</p>
        <div className="mt-2"><ModelStatus compact /></div>
        <p className="text-xs text-gray-400 mt-2">{t('scope_note')}</p>
      </div>

      {!previewUrl && (
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => cameraInputRef.current?.click()}
            className="flex flex-col items-center justify-center gap-2 bg-leaf-600 text-white rounded-2xl py-10 shadow-lg shadow-leaf-600/20 active:scale-[0.98] transition-transform min-h-[44px]"
          >
            <Camera size={32} />
            <span className="font-semibold">{t('take_photo')}</span>
          </button>
          <button
            onClick={() => uploadInputRef.current?.click()}
            className="flex flex-col items-center justify-center gap-2 bg-white text-leaf-700 border-2 border-leaf-600 rounded-2xl py-10 active:scale-[0.98] transition-transform min-h-[44px]"
          >
            <ImagePlus size={32} />
            <span className="font-semibold">{t('upload_photo')}</span>
          </button>
        </div>
      )}

      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => handleFileChosen(e.target.files?.[0])}
      />
      <input
        ref={uploadInputRef}
        type="file"
        accept="image/jpeg,image/jpg,image/png,image/webp"
        className="hidden"
        onChange={(e) => handleFileChosen(e.target.files?.[0])}
      />

      {previewUrl && (
        <Card className="p-3">
          <div className="relative rounded-xl overflow-hidden">
            <img src={previewUrl} alt={t('selected_leaf_preview')} className="w-full max-h-96 object-cover" />
            <button
              onClick={clearImage}
              aria-label={t('remove_image')}
              className="absolute top-3 right-3 bg-white/90 rounded-full p-2 shadow-md min-h-[44px] min-w-[44px] flex items-center justify-center"
            >
              <X size={20} className="text-gray-700" />
            </button>
          </div>
        </Card>
      )}

      {error && (
        <div className="flex items-start gap-2 bg-red-50 text-red-700 rounded-xl p-4 text-sm font-medium">
          <AlertTriangle size={18} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <Card className="bg-leaf-50 border-none">
        <p className="font-semibold text-gray-700 mb-2">{t('tips_title')}</p>
        <ul className="space-y-1.5 text-sm text-gray-600">
          {[t('tip1'), t('tip2'), t('tip3'), t('tip4')].map((tip, i) => (
            <li key={i} className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-leaf-600 shrink-0" />
              {tip}
            </li>
          ))}
        </ul>
      </Card>

      {previewUrl && (
        <div className="space-y-3">
          <Button onClick={handleScan} icon={<Camera size={20} />}>
            {t('scan_now')}
          </Button>
          <Button variant="ghost" onClick={clearImage}>
            {t('remove_image')}
          </Button>
        </div>
      )}
    </div>
  );
}
