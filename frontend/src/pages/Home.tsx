import { Link } from 'react-router-dom';
import { Camera, LineChart, History, BookOpen, Sprout, ScanLine, ClipboardCheck } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import Button from '../components/Button';
import Card from '../components/Card';
import ModelStatus from '../components/ModelStatus';

export default function Home() {
  const { t, language, setLanguage } = useLanguage();

  const steps = [
    { icon: Camera, title: t('step1_title'), desc: t('step1_desc') },
    { icon: ScanLine, title: t('step2_title'), desc: t('step2_desc') },
    { icon: ClipboardCheck, title: t('step3_title'), desc: t('step3_desc') },
    { icon: LineChart, title: t('step4_title'), desc: t('step4_desc') },
  ];

  const quickActions = [
    { to: '/scan', icon: Camera, label: t('scan_crop'), color: 'bg-leaf-600' },
    { to: '/market', icon: LineChart, label: t('check_market'), color: 'bg-wheat-500' },
    { to: '/history', icon: History, label: t('my_history'), color: 'bg-earth-600' },
    { to: '/advisory', icon: BookOpen, label: t('crop_advisory'), color: 'bg-leaf-700' },
  ];

  return (
    <div className="space-y-6 pt-2">
      {/* Header */}
      <div className="flex items-center justify-between md:hidden">
        <div className="flex items-center gap-2">
          <span className="bg-leaf-600 text-white rounded-xl p-2 flex items-center justify-center">
            <Sprout size={20} />
          </span>
          <div>
            <p className="font-extrabold text-lg text-leaf-900 leading-none">{t('app_name')}</p>
            <p className="text-xs text-gray-500">{t('tagline')}</p>
          </div>
        </div>
        <div className="flex items-center gap-1 bg-white rounded-full p-1 shadow-sm border border-leaf-100">
          <button
            onClick={() => setLanguage('en')}
            className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
              language === 'en' ? 'bg-leaf-600 text-white' : 'text-gray-500'
            }`}
          >
            EN
          </button>
          <button
            onClick={() => setLanguage('hi')}
            className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
              language === 'hi' ? 'bg-leaf-600 text-white' : 'text-gray-500'
            }`}
          >
            हि
          </button>
        </div>
      </div>

      <div className="flex justify-center"><ModelStatus /></div>

      {/* Hero */}
      <div className="bg-gradient-to-br from-leaf-600 to-leaf-800 rounded-3xl p-6 text-white relative overflow-hidden">
        <div className="absolute -right-6 -bottom-6 opacity-20">
          <Sprout size={140} />
        </div>
        <h1 className="text-2xl font-extrabold leading-snug relative z-10">{t('hero_title')}</h1>
        <p className="text-leaf-50 mt-2 text-sm relative z-10">{t('hero_subtext')}</p>
        <div className="mt-5 flex flex-col sm:flex-row gap-3 relative z-10">
          <Link to="/scan" className="flex-1">
            <Button variant="secondary" icon={<Camera size={20} />}>
              {t('scan_crop')}
            </Button>
          </Link>
          <Link to="/market" className="flex-1">
            <Button variant="outline" icon={<LineChart size={20} />} className="!bg-white/10 !text-white !border-white/40">
              {t('check_market')}
            </Button>
          </Link>
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-3">
        {quickActions.map(({ to, icon: Icon, label, color }) => (
          <Link key={to} to={to}>
            <Card className="h-full flex flex-col items-center text-center gap-2 py-6">
              <span className={`${color} text-white rounded-2xl p-3`}>
                <Icon size={22} />
              </span>
              <span className="font-semibold text-sm text-gray-700">{label}</span>
            </Card>
          </Link>
        ))}
      </div>

      {/* How it works */}
      <div>
        <h2 className="font-bold text-lg text-gray-800 mb-3">{t('how_it_works')}</h2>
        <div className="space-y-3">
          {steps.map(({ icon: Icon, title, desc }, i) => (
            <Card key={i} className="flex items-center gap-4 py-4">
              <span className="shrink-0 w-11 h-11 rounded-full bg-leaf-100 text-leaf-700 flex items-center justify-center font-bold">
                <Icon size={20} />
              </span>
              <div>
                <p className="font-semibold text-gray-800">{title}</p>
                <p className="text-sm text-gray-500">{desc}</p>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
