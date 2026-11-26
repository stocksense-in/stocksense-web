'use client';
import type { CompanyHeadline } from '@/lib/api';
import { timeAgo } from '@/lib/api';

export function NewsPanel({ items, name }: { items: CompanyHeadline[] | null; name: string }) {
  return (
    <div className="card">
      <div className="ct">Recent news naming {name}</div>
      {items === null && <div style={{ fontSize: 11, color: 'var(--cream-mute)' }}>Loading headlines…</div>}
      {items !== null && items.length === 0 && (
        <div style={{ fontSize: 11, color: 'var(--cream-mute)' }}>No recent headlines name this company.</div>
      )}
      {items?.map((n, i) => (
        <a key={n.link + i} href={n.link} target="_blank" rel="noopener noreferrer"
          style={{ display: 'block', padding: '10px 0', borderBottom: i < items.length - 1 ? '1px solid rgba(201,168,76,0.04)' : 'none', textDecoration: 'none' }}>
          <div style={{ fontSize: 12, color: 'var(--cream)', lineHeight: 1.55 }}>{n.title}</div>
          <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 4 }}>{n.source}{n.published ? ` · ${timeAgo(n.published)}` : ''}</div>
        </a>
      ))}
      <p style={{ fontSize: 9.5, color: 'var(--cream-mute)', marginTop: 12, lineHeight: 1.6 }}>
        Headlines from news searches, kept only when they name the company. A share-price move in a headline is what happened, not a reason; read the story and the company&apos;s own filings.
      </p>
    </div>
  );
}
