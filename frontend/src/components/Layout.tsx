import { ReactNode } from 'react';
import BottomNav from './BottomNav';
import TopNav from './TopNav';
import OfflineBanner from './OfflineBanner';
import { useLocation } from 'react-router-dom';

export default function Layout({ children }: { children: ReactNode }) {
  const isDashboard = useLocation().pathname === '/home';
  return (
    <div className={`min-h-screen flex flex-col ${isDashboard ? 'bg-[#0c1315]' : 'bg-leaf-50'}`}>
      <TopNav dark={isDashboard} />
      <OfflineBanner />
      <main className={`flex-1 w-full mx-auto ${isDashboard ? 'max-w-none px-0 pt-0 pb-0' : 'max-w-3xl px-4 pt-4 pb-24 md:pb-10'}`}>
        {children}
      </main>
      <footer className={`border-t px-4 py-4 text-center text-sm ${isDashboard ? 'border-white/10 text-gray-400' : 'border-leaf-100 text-gray-600'}`}>
        <nav aria-label="Information" className="flex justify-center gap-5">
          <a href="/about" className="underline">About</a>
          <a href="/privacy" className="underline">Privacy</a>
          <a href="/terms" className="underline">Terms</a>
        </nav>
      </footer>
      <BottomNav dark={isDashboard} />
    </div>
  );
}
