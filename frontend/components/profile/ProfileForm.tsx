'use client';

import Link from 'next/link';
import { useState } from 'react';
import { inr } from '@/lib/format';
import { DEFAULT_PROFILE, HORIZON_LABEL, PROFILE_COOKIE, RISK_COPY, type Horizon, type Profile, type Risk } from '@/lib/profile';
import { SECTOR_LABELS } from '@/lib/sectors';
import type { SectorCode } from '@/lib/types';

const SECTOR_CHOICES: SectorCode[] = ['it', 'bank', 'nbfc', 'pharma', 'fmcg', 'auto', 'energy', 'industrial', 'defence', 'materials', 'consumer', 'realestate'];

function saveProfile(profile: Profile) {
  document.cookie = `${PROFILE_COOKIE}=${encodeURIComponent(JSON.stringify(profile))}; path=/; max-age=31536000; samesite=lax`;
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-4 border-t border-rule-2 py-6 first:border-t-0 first:pt-0 sm:grid-cols-[2rem_minmax(0,1fr)]">
      <span className="num grid size-7 place-items-center rounded-full border border-rule text-sm text-ink-2" aria-hidden>{n}</span>
      <div>
        <h2 className="mb-3 font-display text-[1.0667rem] font-semibold text-ink">{title}</h2>
        {children}
      </div>
    </section>
  );
}

/** Edits the investor profile and saves it to a cookie as you go. */
export function ProfileForm({ initial }: { initial: Profile | null }) {
  const [profile, setProfile] = useState<Profile>(initial ?? DEFAULT_PROFILE);
  const [saved, setSaved] = useState(!!initial);

  /** Apply a change and save it straight away (a year-long cookie the server can read). */
  const update = (patch: Partial<Profile>) => {
    const next = { ...profile, ...patch };
    setProfile(next);
    saveProfile(next);
    setSaved(true);
  };
  const toggleSector = (s: SectorCode) =>
    update({ sectors: profile.sectors.includes(s) ? profile.sectors.filter((x) => x !== s) : [...profile.sectors, s] });

  return (
    <div className="panel p-6">
      <Step n={1} title="How much would you invest?">
        <input
          type="range"
          min={10_000}
          max={1_000_000}
          step={10_000}
          value={profile.capital}
          onChange={(e) => update({ capital: Number(e.target.value) })}
          className="w-full accent-[var(--color-brand)]"
          aria-label="Capital to invest"
        />
        <div className="num mt-1 flex justify-between text-sm text-ink-3">
          <span>₹10,000</span>
          <span className="font-medium text-ink">{inr(profile.capital, 0)}</span>
          <span>₹10,00,000</span>
        </div>
      </Step>

      <Step n={2} title="How long can you leave it invested?">
        <div className="segmented" role="group" aria-label="Time horizon">
          {(Object.keys(HORIZON_LABEL) as Horizon[]).map((h) => (
            <button key={h} aria-pressed={profile.horizon === h} onClick={() => update({ horizon: h })}>
              {HORIZON_LABEL[h]}
            </button>
          ))}
        </div>
      </Step>

      <Step n={3} title="How much movement can you stomach?">
        <div className="segmented" role="group" aria-label="Risk appetite">
          {(Object.keys(RISK_COPY) as Risk[]).map((r) => (
            <button key={r} aria-pressed={profile.risk === r} onClick={() => update({ risk: r })}>
              {RISK_COPY[r].label}
            </button>
          ))}
        </div>
        <p className="mt-3 max-w-prose text-sm text-ink-2">{RISK_COPY[profile.risk].description}</p>
        {profile.risk === 'aggressive' && profile.horizon === '1y' && (
          <p className="mt-2 text-sm text-watch-ink">Growth stocks can fall 30% or more in a year. Consider a longer horizon or a balanced profile.</p>
        )}
      </Step>

      <Step n={4} title="Any sectors you understand or prefer?">
        <p className="mb-3 text-sm text-ink-3">Leave all off to consider every sector.</p>
        <div className="flex flex-wrap gap-2">
          {SECTOR_CHOICES.map((s) => {
            const on = profile.sectors.includes(s);
            return (
              <button
                key={s}
                aria-pressed={on}
                onClick={() => toggleSector(s)}
                className={`btn btn-sm ${on ? 'border border-brand bg-brand-wash text-brand-ink' : 'btn-secondary'}`}
              >
                {SECTOR_LABELS[s]}
              </button>
            );
          })}
        </div>
      </Step>

      <div className="mt-2 flex items-center gap-4 border-t border-rule-2 pt-6">
        <Link href="/premium" className="btn btn-primary">See matched picks</Link>
        <span className="text-sm text-ink-3" role="status">{saved ? 'Saved on this device' : ''}</span>
      </div>
    </div>
  );
}
