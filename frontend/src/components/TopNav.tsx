import { NavLink, Link } from 'react-router-dom';
import { Home, ScanLine, LineChart, History, Settings, Sprout, BookOpen } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function TopNav() {
  const { t, language, setLanguage } = useLanguage();

  const items = [
    { to: '/', icon: Home, label: t('nav_home') },
    { to: '/scan', icon: ScanLine, label: t('nav_scan') },
    { to: '/market', icon: LineChart, label: t('nav_market') },
    { to: '/advisory', icon: BookOpen, label: t('nav_advisory') },
    { to: '/history', icon: History, label: t('nav_history') },
    { to: '/settings', icon: Settings, label: t('nav_settings') },
  ];

  return (
    <header className="hidden md:flex items-center justify-between px-8 py-4 bg-white border-b border-leaf-100 sticky top-0 z-40">
      <Link to="/" className="flex items-center gap-2 font-extrabold text-xl text-leaf-800">
        <span className="bg-leaf-600 text-white rounded-xl p-2 flex items-center justify-center">
          <Sprout size={22} />
        </span>
        {t('app_name')}
      </Link>

      <nav className="flex items-center gap-1">
        {items.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                isActive ? 'bg-leaf-100 text-leaf-800' : 'text-gray-500 hover:bg-leaf-50'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="flex items-center gap-1 bg-leaf-50 rounded-full p-1">
        <button
          onClick={() => setLanguage('en')}
          className={`px-3 py-1.5 rounded-full text-sm font-semibold ${
            language === 'en' ? 'bg-white shadow text-leaf-800' : 'text-gray-500'
          }`}
        >
          English
        </button>
        <button
          onClick={() => setLanguage('hi')}
          className={`px-3 py-1.5 rounded-full text-sm font-semibold ${
            language === 'hi' ? 'bg-white shadow text-leaf-800' : 'text-gray-500'
          }`}
        >
          हिंदी
        </button>
      </div>
    </header>
  );
}
