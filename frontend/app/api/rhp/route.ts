import { extractText, getDocumentProxy } from 'unpdf';
import { scanProspectus } from '@/lib/rhp';

const MAX_BYTES = 60 * 1024 * 1024; // DRHPs run 10–40 MB

/** POST a PDF as multipart field "file" → ScanResult JSON. */
export async function POST(request: Request) {
  const form = await request.formData().catch(() => null);
  const file = form?.get('file');
  if (!(file instanceof File)) return Response.json({ error: 'Attach a PDF in the "file" field.' }, { status: 400 });
  if (file.size > MAX_BYTES) return Response.json({ error: 'That file is over 60 MB. Upload the DRHP or RHP PDF only.' }, { status: 413 });

  const bytes = new Uint8Array(await file.arrayBuffer());
  if (String.fromCharCode(...bytes.slice(0, 5)) !== '%PDF-') {
    return Response.json({ error: 'That isn’t a PDF. Upload the prospectus as a .pdf file.' }, { status: 415 });
  }

  try {
    const pdf = await getDocumentProxy(bytes);
    const { text } = await extractText(pdf, { mergePages: false });
    const pages = Array.isArray(text) ? text : [text];
    if (pages.join('').trim().length < 200) {
      return Response.json({ error: 'No text found — this PDF looks scanned. Use the text PDF from the SEBI or exchange website.' }, { status: 422 });
    }
    return Response.json(scanProspectus(pages));
  } catch {
    return Response.json({ error: 'Couldn’t read this PDF. It may be password-protected or damaged.' }, { status: 422 });
  }
}
