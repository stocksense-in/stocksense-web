'use client';

import { usePathname } from 'next/navigation';

/** Renders its children everywhere except the listed routes. */
export function HideOn({ paths, children }: { paths: string[]; children: React.ReactNode }) {
  const pathname = usePathname();
  return paths.includes(pathname) ? null : <>{children}</>;
}
