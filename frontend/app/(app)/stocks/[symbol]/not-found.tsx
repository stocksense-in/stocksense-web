import Link from 'next/link';

export default function StockNotFound() {
  return (
    <div className="panel mx-auto max-w-lg px-8 py-12 text-center">
      <h1 className="font-display text-2xl font-semibold text-ink">We don’t track that symbol</h1>
      <p className="mt-2 text-ink-2">
        Check the NSE symbol (for example INFY, not Infosys), or search by company name in the box above.
      </p>
      <Link href="/stocks" className="btn btn-primary mt-6">Browse stocks</Link>
    </div>
  );
}
