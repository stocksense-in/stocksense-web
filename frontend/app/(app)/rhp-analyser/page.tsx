import type { Metadata } from 'next';
import { ProspectusScanner } from '@/components/rhp/ProspectusScanner';

export const metadata: Metadata = { title: 'Prospectus scanner' };

export default function ProspectusScannerPage() {
  return (
    <div className="space-y-6">
      <header className="max-w-2xl">
        <h1 className="font-display text-[2rem] font-semibold tracking-[-0.02em] text-ink">Prospectus scanner</h1>
        <p className="mt-1 text-ink-2">
          An IPO prospectus runs to hundreds of pages. Upload one and the scanner pulls out the disclosures that most often hurt new investors, with the page each came from.
        </p>
      </header>
      <ProspectusScanner />
      <p className="text-[0.8rem] text-ink-3">
        Pattern matching on the document’s text, not a legal review. It can miss risks that are worded differently — always read the Risk Factors chapter yourself.
      </p>
    </div>
  );
}
