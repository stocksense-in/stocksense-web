'use client';

/** A GET form that submits itself whenever a field changes — filters apply instantly, and still work without JavaScript via the submit button. */
export function AutoSubmitForm({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <form
      method="get"
      className={className}
      onChange={(e) => (e.currentTarget as HTMLFormElement).requestSubmit()}
    >
      {children}
    </form>
  );
}
