import { IndexBar } from '@/components/shell/IndexBar';
import { SearchBox } from '@/components/shell/SearchBox';
import { MobileNav, Sidebar } from '@/components/shell/Sidebar';

/** Shell for every signed-in page: sidebar, search, index bar. The landing page (/) sits outside it. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 border-b border-rule bg-paper/90 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-[1240px] items-center gap-3 px-4 sm:px-6">
            <MobileNav />
            <SearchBox />
          </div>
          <div className="mx-auto max-w-[1240px] px-4 pb-2.5 sm:px-6">
            <IndexBar />
          </div>
        </header>
        <main className="mx-auto max-w-[1240px] px-4 py-6 sm:px-6 sm:py-8">{children}</main>
      </div>
    </div>
  );
}
