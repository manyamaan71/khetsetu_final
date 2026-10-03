import React from 'react';
import { Link } from 'react-router-dom';
import {
  Camera,
  History,
  LineChart,
  MapPinned,
  Sprout,
  UserRound,
  LayoutDashboard,
  BarChart3,
  Leaf,
  Sparkles,
  Truck,
  Building2,
  Wallet,
  Globe,
  Bell,
  ArrowRight
} from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import LanguageSelector from '../components/LanguageSelector';

export default function DashboardPage() {
  const { profile, signOut } = useAuth();
  const { t } = useLanguage();

  const sidebarNav = [
    { label: t('nav_home') || 'Home', icon: LayoutDashboard, active: true },
    { label: 'Farm stats', icon: BarChart3 },
    { label: 'Crop management', icon: Leaf },
    { label: 'Precision farming', icon: Sparkles },
    { label: 'Logistics & storage', icon: Truck },
    { label: 'Agri-finance', icon: Wallet },
  ];

  return (
    <div className="min-h-screen bg-emerald-50/40 text-gray-800 flex flex-col md:flex-row">
      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 bg-white border-r border-emerald-100 p-4 flex flex-col justify-between space-y-6">
        <div className="space-y-6">
          <div className="flex items-center gap-2.5 px-2">
            <div className="rounded-xl bg-emerald-600 p-2 text-white shadow-sm">
              <Sprout size={20} />
            </div>
            <div>
              <h2 className="font-extrabold text-gray-900 tracking-tight">KhetSetu</h2>
              <p className="text-[10px] font-semibold tracking-wider text-emerald-700 uppercase">Field Operations</p>
            </div>
          </div>

          <nav className="space-y-1">
            <p className="px-2 text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2">Workspace</p>
            {sidebarNav.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.label}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                    item.active
                      ? 'bg-emerald-100/70 text-emerald-900'
                      : 'text-gray-600 hover:bg-emerald-50/50 hover:text-emerald-800'
                  }`}
                >
                  <Icon size={18} className={item.active ? 'text-emerald-700' : 'text-gray-400'} />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* User Card at Sidebar Bottom */}
        <div className="pt-4 border-t border-emerald-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-emerald-200 text-emerald-800 font-bold flex items-center justify-center text-sm">
              {profile?.full_name?.charAt(0) || 'M'}
            </div>
            <div className="text-left">
              <p className="text-sm font-bold text-gray-900 leading-tight">{profile?.full_name || 'M R Niharika'}</p>
              <p className="text-xs text-gray-500">{profile?.district || 'Mandya'}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-4 md:p-8 space-y-6">
        {/* Top Bar / Welcome Header */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-emerald-100 shadow-sm">
          <div>
            <p className="text-xs font-semibold text-emerald-700 tracking-wide uppercase">Saturday, 3 October · Field Overview</p>
            <h1 className="text-2xl font-extrabold text-gray-900 mt-0.5">
              {t('welcome')}, {profile?.full_name || 'M R Niharika'}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-gray-600 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-100">
              <MapPinned size={14} className="text-emerald-600" />
              <span>{profile?.district || 'Mandya'}</span>
            </div>
            <button className="p-2 text-gray-500 hover:text-emerald-700 rounded-xl hover:bg-emerald-50 border border-emerald-100">
              <Bell size={18} />
            </button>
            <LanguageSelector variant="compact" />
          </div>
        </header>

        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-white border-emerald-100 shadow-sm">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Farm Area</p>
                <p className="text-2xl font-extrabold text-gray-900 mt-2">{profile?.farm_size || '2.5 Acres'}</p>
                <p className="text-xs text-gray-500 mt-1">1 crop in your profile</p>
              </div>
              <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600">
                <Sprout size={20} />
              </div>
            </div>
          </Card>

          <Card className="bg-white border-emerald-100 shadow-sm">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Crop Records</p>
                <p className="text-2xl font-extrabold text-gray-900 mt-2">01</p>
                <p className="text-xs text-gray-500 mt-1">2 saved scans</p>
              </div>
              <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600">
                <History size={20} />
              </div>
            </div>
          </Card>

          <Card className="bg-emerald-600 text-white shadow-sm border-none">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-bold text-emerald-100 uppercase tracking-wider">Voice Interface</p>
                <h3 className="text-base font-bold mt-1">Multi-Language Access</h3>
                <p className="text-xs text-emerald-100 mt-1">Spoken guidance in 7 languages</p>
              </div>
              <div className="p-2.5 rounded-xl bg-white/20 text-white">
                <Globe size={20} />
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-1.5">
              {['English', 'हिन्दी', 'ಕನ್ನಡ', 'தமிழ்', 'తెలుగు', 'मराठी', 'বাংলা'].map((lang) => (
                <span key={lang} className="text-[11px] px-2 py-0.5 rounded-md bg-white/20 font-medium">
                  {lang}
                </span>
              ))}
            </div>
          </Card>
        </div>

        {/* Analytics & Diagnosis Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chart Card */}
          <Card className="lg:col-span-2 bg-white border-emerald-100 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center mb-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-gray-400">Field Profile</p>
                  <h3 className="text-lg font-bold text-gray-900">Crop Distribution</h3>
                </div>
                <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-100">
                  Illustrative
                </span>
              </div>

              {/* Chart Placeholder / Curves */}
              <div className="h-44 w-full bg-emerald-50/50 rounded-xl border border-emerald-100/60 p-4 flex items-end justify-between relative overflow-hidden">
                <svg className="absolute inset-0 w-full h-full text-emerald-500/20" preserveAspectRatio="none" viewBox="0 0 100 100">
                  <path d="M0,80 Q25,20 50,70 T100,30 L100,100 L0,100 Z" fill="currentColor" />
                  <path d="M0,90 Q30,40 60,80 T100,50 L100,100 L0,100 Z" fill="rgba(16,185,129,0.15)" />
                </svg>
                <div className="relative z-10 text-xs font-medium text-gray-500 flex justify-between w-full">
                  <span>100%</span>
                  <span>75%</span>
                  <span>50%</span>
                  <span>25%</span>
                  <span>0%</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-500 mt-4 pt-3 border-t border-emerald-100">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Season reference</span>
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-300"></span> Field activity</span>
              </div>
              <span>Corn</span>
            </div>
          </Card>

          {/* AI Diagnosis Action Card */}
          <Card className="bg-white border-emerald-100 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center mb-3">
                <p className="text-xs font-bold uppercase tracking-wider text-gray-400">Precision Farming · AI</p>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                  Real AI model
                </span>
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-4">Crop health diagnosis</h3>

              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-100 space-y-2">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-600 text-white">
                    <Camera size={20} />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Latest saved diagnosis</p>
                    <p className="text-base font-extrabold text-gray-900">Tomato · Healthy</p>
                  </div>
                </div>
                <p className="text-xs text-emerald-700 font-semibold pt-1">100% confidence · Saved on this device</p>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              <p className="text-[11px] text-gray-400">Diagnosis uses the crop model; uncertain results are withheld.</p>
              <Link to="/scan" className="block">
                <Button className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2">
                  <span>Start another scan</span>
                  <ArrowRight size={18} />
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}