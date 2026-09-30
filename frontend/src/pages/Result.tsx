import { ReactNode, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Volume2, Square, RotateCcw, CheckCircle2, ShieldCheck, Sprout, Info, AlertCircle, AlertTriangle, Download, LoaderCircle,
  Stethoscope, Droplets, FlaskConical, PhoneCall, Ban, Bug, Languages, TrendingUp, ScanSearch,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import Button from '../components/Button';
import Card from '../components/Card';
import ConfidenceIndicator from '../components/ConfidenceIndicator';
import { getCurrentScanImage, getLastResult } from '../services/storageService';
import { downloadScanReport } from '../services/api';
import LanguageSelector from '../components/LanguageSelector';
import { speak, stopSpeaking, isSpeechSupported, getSpeechLang } from '../services/speechService';
import { Language, ScanApiResponse, ScanOk } from '../types';

function Section({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <Card>
      <h2 className="flex items-center gap-2 font-bold text-gray-800 mb-2 text-base">{icon} {title}</h2>
      {children}
    </Card>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5 text-[15px] leading-relaxed text-gray-700 list-disc list-inside">
      {items.map((x, i) => <li key={i}>{x}</li>)}
    </ul>
  );
}

function localizedValue(value: Record<string, string | string[]> | undefined, language: Language): string | string[] | undefined {
  const result = value?.[language] ?? value?.en;
  return typeof result === 'string' || Array.isArray(result) ? result : undefined;
}

function localizedList(value: Record<string, string | string[]> | undefined, language: Language): string[] {
  const result = localizedValue(value, language);
  if (Array.isArray(result)) return result.filter((item): item is string => typeof item === 'string');
  return typeof result === 'string' && result ? [result] : [];
}

function speechText(r: ScanOk, lang: Language, t: (k: any) => string): string {
  const g = r.advisory ?? r.guidance;
  const p = r.prediction;
  const crop = lang === 'hi' ? p.crop_hi : p.crop;
  const cond = lang === 'hi' ? p.disease_hi : p.disease;
  const whatFound = localizedValue(g.what_we_found, lang) ?? localizedValue(g.what_is_it, lang) ?? '';
  const why = localizedList(g.why_it_happened, lang).join(' ');
  const actionPlan = (localizedList(g.immediate_actions, lang).length
    ? localizedList(g.immediate_actions, lang)
    : localizedList(g.basic_care, lang)).join(' ');
  const management = localizedList(g.management, lang).join(' ');
  const prevention = localizedList(g.prevention, lang).join(' ');
  const healthyPrefix = p.is_healthy ? `${crop}. ${t('healthy_leaf')}. ${whatFound}` : `${crop}. ${cond}. ${whatFound}`;
  return [healthyPrefix, why, actionPlan, management, prevention, localizedValue(g.source_note, lang) ?? ''].join(' ');
}

export default function Result() {
  const { t, language } = useLanguage();
  const { profile } = useAuth();
  const navigate = useNavigate();
  const [result, setResult] = useState<ScanApiResponse | null>(null);
  const [speaking, setSpeaking] = useState(false);
  const [voiceNote, setVoiceNote] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  useEffect(() => {
    const data = getLastResult<ScanApiResponse>();
    if (!data) { navigate('/scan'); return; }
    setResult(data);
    return () => stopSpeaking();
  }, [navigate]);

  useEffect(() => { stopSpeaking(); setSpeaking(false); setVoiceNote(null); }, [language]);

  if (!result) return null;

  const downloadReport = async () => {
    const scanId = result.client_scan_id;
    if (!scanId) { setDownloadError(t('download_report_error')); return; }
    setDownloading(true);
    setDownloadError(null);
    try {
      const image = await getCurrentScanImage(scanId);
      if (!image) throw new Error('Current scan image is unavailable');
      const report = await downloadScanReport(image, language, profile?.full_name);
      const url = URL.createObjectURL(report.blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = report.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setDownloadError(t('download_report_error'));
    } finally {
      setDownloading(false);
    }
  };

  const reportButton = (
    <>
      <Button variant="outline" icon={downloading ? <LoaderCircle size={18} className="animate-spin" /> : <Download size={18} />}
        onClick={downloadReport} disabled={downloading}>
        {downloading ? t('download_report_loading') : t('download_report')}
      </Button>
      {downloadError && <p role="alert" className="text-sm text-red-700">{downloadError}</p>}
    </>
  );

  const langToggle = <LanguageSelector variant="compact" />;

  if (!result.is_confident) {
    const m = result.message;
    const title = m.title[language] || m.title.en;
    const body = m.body[language] || m.body.en;
    const tips = m.tips[language] || m.tips.en;
    return (
      <div className="space-y-5 pt-4 text-center">
        <div className="flex justify-end">{langToggle}</div>
        <div className="w-20 h-20 mx-auto rounded-full bg-amber-100 flex items-center justify-center">
          {result.status === 'not_a_leaf' ? <ScanSearch size={36} className="text-amber-600" /> : <AlertCircle size={36} className="text-amber-600" />}
        </div>
        <h1 className="text-2xl font-extrabold text-gray-800">{title}</h1>
        <p className="text-gray-600 max-w-sm mx-auto text-base">{body}</p>
        {result.demo_mode && (
          <p className="inline-block bg-amber-100 text-amber-800 text-xs font-bold px-3 py-1 rounded-full">{t('status_demo')}</p>
        )}
        <Card className="bg-leaf-50 border-none text-left max-w-sm mx-auto">
          <p className="font-semibold text-gray-700 mb-2">{t('tips_title')}</p>
          <ul className="space-y-1.5 text-sm text-gray-600">
            {tips.map((tip, i) => (
              <li key={i} className="flex items-center gap-2"><CheckCircle2 size={16} className="text-leaf-600 shrink-0" />{tip}</li>
            ))}
          </ul>
        </Card>
        {reportButton}
        <Link to="/scan"><Button icon={<RotateCcw size={20} />}>{t('scan_again')}</Button></Link>
        <p className="text-xs text-gray-400 max-w-sm mx-auto">{t('scope_note')}</p>
      </div>
    );
  }

  const r = result;
  const p = r.prediction;
  const g = (r.advisory ?? r.guidance) as any;
  const crop = language === 'hi' ? p.crop_hi : p.crop;
  const cond = language === 'hi' ? p.disease_hi : p.disease;
  const marketCrop = p.crop === 'Corn' ? 'Maize' : p.crop;

  const toggleSpeech = async () => {
    if (speaking) { stopSpeaking(); setSpeaking(false); return; }
    if (!isSpeechSupported()) { setVoiceNote(t('tts_unsupported')); return; }
    const targetSpeechLang = getSpeechLang(language);
    setVoiceNote(null);
    setSpeaking(true);
    const voicePlayed = await speak(speechText(r, language, t), targetSpeechLang);
    if (!voicePlayed) setVoiceNote(t('tts_no_voice'));
    setSpeaking(false);
  };

  return (
    <div className="space-y-4 pt-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">{t('ai_result_title')}</span>
        {langToggle}
      </div>

      {r.demo_mode && (
        <div className="bg-amber-100 text-amber-900 text-sm font-bold text-center py-2 px-3 rounded-xl flex items-center justify-center gap-2">
          <AlertTriangle size={16} /> {t('demo_banner')}
        </div>
      )}

      {p.is_healthy ? (
        <Card className="bg-leaf-50 border-leaf-200">
          <div className="flex items-center justify-between gap-4">
            <div>
              <Sprout size={36} className="text-leaf-600 mb-2" />
              <h1 className="text-2xl font-extrabold text-leaf-800">🌱 {t('healthy_leaf')}</h1>
              <p className="text-gray-700 mt-1 text-base">{crop} {t('healthy_msg')}</p>
            </div>
            <ConfidenceIndicator confidence={p.confidence} />
          </div>
        </Card>
      ) : (
        <Card>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-xs text-gray-500">{t('label_crop')}</p>
              <p className="text-2xl font-extrabold text-gray-800">{crop}</p>
              <p className="text-xs text-gray-500 mt-3">{t('label_condition')}</p>
              <p className="text-xl font-bold text-amber-700 leading-snug">{cond}</p>
              <span className="inline-flex items-center gap-1 mt-3 bg-amber-100 text-amber-800 text-xs font-bold px-2.5 py-1 rounded-full">
                <Bug size={12} /> {t('status_diseased')}
              </span>
            </div>
            <ConfidenceIndicator confidence={p.confidence} />
          </div>
        </Card>
      )}

      <Button variant="outline" icon={speaking ? <Square size={18} /> : <Volume2 size={22} />} onClick={toggleSpeech}>
        {speaking ? t('listen_stop') : t('listen')} 🔊
      </Button>
      {reportButton}
      {voiceNote && <p className="text-xs text-amber-800 bg-amber-50 rounded-lg p-3">{voiceNote}</p>}

      {g.urgency === 'act_fast' && (
        <div className="flex items-start gap-2 bg-red-50 text-red-800 rounded-xl p-4 text-sm font-semibold">
          <AlertTriangle size={18} className="shrink-0 mt-0.5" /> {t('urgent_note')}
        </div>
      )}

      <Section icon={<Info size={18} className="text-leaf-600" />} title={t('what_found')}>
        <p className="text-[15px] leading-relaxed text-gray-700">{localizedValue(g.what_we_found, language) ?? localizedValue(g.what_is_it, language) ?? ''}</p>
      </Section>

      <Section icon={<Stethoscope size={18} className="text-leaf-600" />} title={t('why_it_happened')}>
        <Bullets items={localizedList(g.why_it_happened, language).length
          ? localizedList(g.why_it_happened, language)
          : localizedList(g.possible_cause, language)} />
      </Section>

      <Section icon={<Bug size={18} className="text-leaf-600" />} title={t('sec_symptoms')}>
        <Bullets items={localizedList(g.symptoms, language)} />
      </Section>

      <Section icon={<CheckCircle2 size={18} className="text-leaf-600" />} title={t('what_should_i_do_now')}>
        <ol className="space-y-2 list-decimal list-inside text-[15px] leading-relaxed text-gray-700">
          {(localizedList(g.immediate_actions, language).length
            ? localizedList(g.immediate_actions, language)
            : localizedList(g.basic_care, language)).map((step: string, idx: number) => (
            <li key={idx}>{step}</li>
          ))}
        </ol>
      </Section>

      <Section icon={<ShieldCheck size={18} className="text-leaf-600" />} title={t('treatment_management')}>
        <Bullets items={localizedList(g.management, language)} />
      </Section>

      <Section icon={<Droplets size={18} className="text-leaf-600" />} title={t('how_to_prevent')}>
        <Bullets items={localizedList(g.prevention, language)} />
      </Section>

      {!p.is_healthy && (
        <Section icon={<Ban size={18} className="text-red-600" />} title={t('avoid_title')}>
          <Bullets items={localizedList(g.avoid, language)} />
        </Section>
      )}

      <Section icon={<PhoneCall size={18} className="text-leaf-600" />} title={t('when_to_seek_help')}>
        <Bullets items={localizedList(g.when_to_seek_help, language).length
          ? localizedList(g.when_to_seek_help, language)
          : localizedList(g.consult_expert_when, language)} />
      </Section>

      <Card>
        <h2 className="font-bold text-gray-800 mb-3 text-base">{t('disease_information')}</h2>
        <div className="grid gap-3 sm:grid-cols-2 text-sm text-gray-700">
          <div className="rounded-xl bg-leaf-50 p-3"><div className="text-xs uppercase tracking-wide text-gray-500">{t('severity_label')}</div><div className="font-bold text-gray-800 mt-1">{localizedValue(g.severity, language) ?? '—'}</div></div>
          <div className="rounded-xl bg-leaf-50 p-3"><div className="text-xs uppercase tracking-wide text-gray-500">{t('spread_risk_label')}</div><div className="font-bold text-gray-800 mt-1">{localizedValue(g.spread_risk, language) ?? '—'}</div></div>
          <div className="rounded-xl bg-leaf-50 p-3"><div className="text-xs uppercase tracking-wide text-gray-500">{t('label_crop')}</div><div className="font-bold text-gray-800 mt-1">{crop}</div></div>
          <div className="rounded-xl bg-leaf-50 p-3"><div className="text-xs uppercase tracking-wide text-gray-500">{t('label_condition')}</div><div className="font-bold text-gray-800 mt-1">{cond}</div></div>
        </div>
      </Card>

      <div className="flex items-start gap-2 bg-amber-50 text-amber-900 rounded-xl p-4 text-xs leading-relaxed">
        <AlertCircle size={16} className="shrink-0 mt-0.5" />
        <span>{localizedValue(g.source_note, language) ?? ''} {t('pesticide_disclaimer')}</span>
      </div>

      <div className="grid grid-cols-1 gap-3 pt-2 pb-4">
        <Link to="/scan"><Button icon={<RotateCcw size={20} />}>{t('scan_again')}</Button></Link>
        <Link to={`/market?crop=${marketCrop}`}><Button variant="ghost" icon={<TrendingUp size={20} />}>{t('market_for_crop')}</Button></Link>
      </div>
    </div>
  );
}
