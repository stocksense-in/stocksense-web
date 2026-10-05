import Link from 'next/link';
import { Logo } from '@/components/shell/Logo';

export default function NotFound() {
  return (
    <div className="grid min-h-dvh place-items-center px-5">
      <div className="max-w-md text-center">
        <Logo />
        <h1 className="mt-8 font-display text-[2rem] font-semibold tracking-tight text-ink">There’s no page here</h1>
        <p className="mt-2 text-ink-2">The link may be old. Everything StockSense does starts from the dashboard.</p>
        <Link href="/dashboard" className="btn btn-primary mt-6">Go to the dashboard</Link>
      </div>
    </div>
  );
}
