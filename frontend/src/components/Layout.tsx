import { ReactNode } from 'react';
import BottomNav from './BottomNav';
import TopNav from './TopNav';
import OfflineBanner from './OfflineBanner';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-leaf-50 flex flex-col">
      <TopNav />
      <OfflineBanner />
      <main className="flex-1 w-full max-w-3xl mx-auto px-4 pt-4 pb-24 md:pb-10">
        {children}
      </main>
      <footer className="border-t border-leaf-100 px-4 py-4 text-center text-sm text-gray-600">
        <nav aria-label="Information" className="flex justify-center gap-5">
          <a href="/about" className="underline">About</a>
          <a href="/privacy" className="underline">Privacy</a>
          <a href="/terms" className="underline">Terms</a>
        </nav>
      </footer>
      <BottomNav />
    </div>
  );
}
