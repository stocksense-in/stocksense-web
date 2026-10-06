/**
 * The mark is a tiny metric gauge — a ruler, its ideal range, and a gold reading —
 * the same device used for every metric in the product.
 */
export function Logo({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width="24" height="24" viewBox="0 0 22 22" aria-hidden>
        <rect x="0.5" y="0.5" width="21" height="21" rx="6" fill="#141D33" stroke="rgb(148 163 209 / 0.3)" />
        <rect x="4" y="10" width="14" height="2" rx="1" fill="#ffffff" opacity="0.3" />
        <rect x="8" y="9" width="6" height="4" rx="1" fill="#F2B544" opacity="0.35" />
        <circle cx="12.5" cy="11" r="2.6" fill="#F2B544" stroke="#141D33" strokeWidth="1.2" />
      </svg>
      <span className="font-display text-[1.1rem] font-semibold tracking-[-0.02em] text-ink">StockSense</span>
    </span>
  );
}
