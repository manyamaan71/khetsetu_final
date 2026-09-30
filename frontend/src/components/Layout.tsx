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
      <BottomNav />
    </div>
  );
}
