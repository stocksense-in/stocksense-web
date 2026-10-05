'use client';

/** Shown when a page fails to render — usually the data source is unreachable. */
export default function PageError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="panel mx-auto max-w-lg px-8 py-12 text-center">
      <h1 className="font-display text-2xl font-semibold text-ink">This page couldn’t load</h1>
      <p className="mt-2 text-ink-2">The market data service didn’t respond. Check your connection, then try again.</p>
      <button className="btn btn-primary mt-6" onClick={reset}>Try again</button>
    </div>
  );
}
