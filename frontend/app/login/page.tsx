import type { Metadata } from 'next';
import Link from 'next/link';
import { Logo } from '@/components/shell/Logo';

export const metadata: Metadata = { title: 'Sign in' };

/**
 * Accounts aren't built yet (planned: Supabase Auth). Until then this page says
 * so plainly instead of pretending to sign people in.
 */
export default function LoginPage() {
  return (
    <div className="grid min-h-dvh place-items-center px-5 py-12">
      <div className="w-full max-w-sm">
        <Link href="/" aria-label="StockSense home"><Logo /></Link>
        <div className="panel mt-8 p-6">
          <h1 className="font-display text-[1.5rem] font-semibold tracking-tight text-ink">Sign in</h1>
          <p className="mt-2 text-[0.9333rem] text-ink-2">
            Accounts are on the way. Until then, everything works without one — your paper-trading portfolio and investor profile are saved on this device.
          </p>
          <form className="mt-6 space-y-4" aria-describedby="login-status">
            <label className="block">
              <span className="label">Email</span>
              <input className="field" type="email" autoComplete="email" disabled placeholder="you@example.com" />
            </label>
            <label className="block">
              <span className="label">Password</span>
              <input className="field" type="password" autoComplete="current-password" disabled />
            </label>
            <p id="login-status" className="text-sm text-ink-3">Sign-in opens once accounts launch.</p>
          </form>
          <Link href="/dashboard" className="btn btn-primary mt-6 w-full">Continue without an account</Link>
        </div>
      </div>
    </div>
  );
}
