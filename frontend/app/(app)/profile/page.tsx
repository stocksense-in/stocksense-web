import type { Metadata } from 'next';
import { cookies } from 'next/headers';
import { ProfileForm } from '@/components/profile/ProfileForm';
import { PROFILE_COOKIE, parseProfile } from '@/lib/profile';

export const metadata: Metadata = { title: 'Investor profile' };

export default async function ProfilePage() {
  const initial = parseProfile((await cookies()).get(PROFILE_COOKIE)?.value);
  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <h1 className="font-display text-[2rem] font-semibold tracking-[-0.02em] text-ink">Investor profile</h1>
        <p className="mt-1 text-ink-2">Four questions. Your answers decide which stocks appear in Matched picks — nothing leaves this device.</p>
      </header>
      <ProfileForm initial={initial} />
    </div>
  );
}
