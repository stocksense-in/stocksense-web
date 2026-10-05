/**
 * The mark is a tiny metric gauge — a ruler, its ideal range, and a reading —
 * the same device used for every metric in the product.
 */
export function Logo({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden>
        <rect width="22" height="22" rx="6" fill="var(--color-ink)" />
        <rect x="4" y="10" width="14" height="2" rx="1" fill="#ffffff" opacity="0.35" />
        <rect x="8" y="9" width="6" height="4" rx="1" fill="#ffffff" opacity="0.55" />
        <circle cx="12.5" cy="11" r="2.6" fill="var(--color-brand)" stroke="var(--color-ink)" strokeWidth="1.2" />
      </svg>
      <span className="font-display text-[1.1rem] font-semibold tracking-[-0.02em] text-ink">StockSense</span>
    </span>
  );
}
