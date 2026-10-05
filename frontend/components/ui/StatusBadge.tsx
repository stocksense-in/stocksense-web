import type { Status } from '@/lib/types';

const STYLES: Record<Status, { dot: string; text: string; bg: string }> = {
  healthy: { dot: 'bg-up', text: 'text-up', bg: 'bg-up-wash' },
  watch: { dot: 'bg-watch', text: 'text-watch-ink', bg: 'bg-watch-wash' },
  concern: { dot: 'bg-down', text: 'text-down', bg: 'bg-down-wash' },
  neutral: { dot: 'bg-ink-3', text: 'text-ink-2', bg: 'bg-sunken' },
};

/** Coloured dot + word. Status is never shown by colour alone. */
export function StatusBadge({ status, children }: { status: Status; children: React.ReactNode }) {
  const s = STYLES[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.8rem] font-medium ${s.bg} ${s.text}`}>
      <span className={`size-1.5 rounded-full ${s.dot}`} aria-hidden />
      {children}
    </span>
  );
}

export const STATUS_FILL: Record<Status, string> = {
  healthy: 'bg-up',
  watch: 'bg-watch',
  concern: 'bg-down',
  neutral: 'bg-ink-3',
};
