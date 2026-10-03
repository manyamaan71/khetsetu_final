import { NavLink } from 'react-router-dom';
import { Home, ScanLine, LineChart, History, Settings } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function BottomNav() {
  const { t } = useLanguage();

  const items = [
    { to: '/', icon: Home, label: t('nav_home') },
    { to: '/scan', icon: ScanLine, label: t('nav_scan') },
    { to: '/market', icon: LineChart, label: t('nav_market') },
    { to: '/history', icon: History, label: t('nav_history') },
    { to: '/settings', icon: Settings, label: t('nav_settings') },
  ];

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-leaf-100 shadow-[0_-2px_10px_rgba(0,0,0,0.05)] z-40"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      aria-label="Primary navigation"
    >
      <div className="flex items-stretch justify-between px-1">
        {items.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 min-h-[56px] text-[11px] font-medium ${
                isActive ? 'text-leaf-700' : 'text-gray-400'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
