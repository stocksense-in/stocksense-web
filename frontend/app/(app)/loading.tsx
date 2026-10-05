/** Shown while a page's data loads (Supabase, price history). Mirrors the common page shape. */
export default function Loading() {
  return (
    <div className="animate-pulse space-y-6" aria-busy="true" aria-label="Loading">
      <div className="h-9 w-64 rounded-md bg-rule-2" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="panel h-72" />
        <div className="panel h-72" />
      </div>
      <div className="panel h-96" />
    </div>
  );
}
