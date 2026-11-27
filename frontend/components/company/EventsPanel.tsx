'use client';
import type { CompanyEvents } from '@/lib/api';
import { fmtCrore } from '@/lib/api';

const GROUP: Record<string, { label: string; pill: string; plain: string }> = {
  warning: { label: 'Red flag', pill: 'pill pill-r', plain: 'defaults, fraud, insolvency, an auditor resigning, operations stopped or results delayed' },
  exchange: { label: 'Exchange query', pill: 'pill pill-r', plain: 'the exchange asked about a price or volume spike or a news report' },
  legal: { label: 'Legal', pill: 'pill pill-r', plain: 'regulatory actions, court cases, licences' },
  results: { label: 'Results', pill: 'pill pill-gold', plain: 'board meetings and quarterly results' },
  orders: { label: 'Order win', pill: 'pill pill-g', plain: 'orders and contracts won' },
  deals: { label: 'Deal', pill: 'pill pill-b', plain: 'acquisitions, mergers, disposals, new subsidiaries, tie-ups' },
  capital: { label: 'Capital', pill: 'pill pill-b', plain: 'dividends, bonuses, splits, buybacks, new shares issued' },
  rating: { label: 'Rating', pill: 'pill pill-b', plain: 'credit ratings on its debt' },
  management: { label: 'Management', pill: 'pill pill-gold', plain: 'directors, executives or auditors joining or leaving' },
  business: { label: 'Business', pill: 'pill pill-g', plain: 'press releases, new capacity, products, monthly updates' },
};
const ORDER = ['warning', 'exchange', 'legal', 'results', 'orders', 'deals', 'capital', 'rating', 'management', 'business'];

const day = (s: string) => new Date(s.length > 10 ? s : s + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
const month = (s: string) => new Date(s + 'T00:00:00').toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });

/** What the company told the exchange over the past year, and what its insiders did with their own shares. */
export function EventsPanel({ e, name }: { e: CompanyEvents; name: string }) {
  const counts = ORDER.filter(g => e.counts[g]);
  const flags = (e.counts.warning ?? 0) + (e.counts.legal ?? 0);
  const ins = e.insiders;
  const deals = e.deals ?? [];
  return (
    <div className="g2" style={{ alignItems: 'start' }}>
      <div className="card">
        <div className="ct">What {name} told the exchange</div>
        {e.announcements.length === 0 && <p className="mc-plain">No notable filings in the past year.</p>}
        {e.announcements.map((a, i) => {
          const g = GROUP[a.group] ?? { label: a.group, pill: 'pill pill-b', plain: '' };
          const body = (
            <>
              <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span className={g.pill} style={{ fontSize: 8, flexShrink: 0 }} title={a.category}>{g.label}</span>
                <span style={{ fontFamily: 'var(--f-mono)', fontSize: 9.5, color: 'var(--cream-mute)' }}>{day(a.at)}</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--cream)', lineHeight: 1.55, marginTop: 4 }}>{a.title}</div>
            </>
          );
          const style = { display: 'block', padding: '9px 0', borderBottom: i < e.announcements.length - 1 ? '1px solid rgba(201,168,76,0.04)' : 'none', textDecoration: 'none' };
          return a.link
            ? <a key={a.at + i} href={a.link} target="_blank" rel="noopener noreferrer" style={style} title="Open the filing (PDF on NSE)">{body}</a>
            : <div key={a.at + i} style={style}>{body}</div>;
        })}
        <p style={{ fontSize: 9.5, color: 'var(--cream-mute)', marginTop: 12, lineHeight: 1.6 }}>
          The most recent notable filings{e.since ? ` since ${day(e.since)}` : ''}; routine notices (newspaper copies, trading windows, meeting schedules) are left out, and red flags are always shown. Each links to the filing on NSE.
        </p>
      </div>

      <div>
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="ct">The past year at a glance</div>
          {counts.length === 0 && <p className="mc-plain">Nothing notable filed in the past year.</p>}
          {counts.map(g => (
            <div key={g} className="stat-r" title={GROUP[g]?.plain}>
              <span className="sl">{GROUP[g]?.label ?? g}</span>
              <span className="sv" style={{ fontFamily: 'var(--f-mono)', color: g === 'warning' || g === 'legal' ? 'var(--red)' : undefined }}>{e.counts[g]}</span>
            </div>
          ))}
          <p className="mc-plain" style={{ marginTop: 10 }}>
            {flags > 0
              ? 'Red flags and legal filings deserve a read before anything else: open them and see what actually happened.'
              : 'No red flags or legal filings in the past year.'}
          </p>
        </div>

        <div className="card" style={{ marginBottom: e.deals_since ? 14 : 0 }}>
          <div className="ct">Insiders&apos; own trades</div>
          {!ins && (
            <p className="mc-plain">
              No market purchases or sales by promoters, directors or key managers{e.insiders_until ? ` in the two years to ${month(e.insiders_until)}` : ''}.
            </p>
          )}
          {ins && (
            <>
              <div className="stat-r"><span className="sl">Bought on the market</span><span className="sv" style={{ fontFamily: 'var(--f-mono)', color: 'var(--green)' }}>{fmtCrore(ins.bought_cr ?? 0)} · {ins.buys}×</span></div>
              <div className="stat-r"><span className="sl">Sold on the market</span><span className="sv" style={{ fontFamily: 'var(--f-mono)', color: 'var(--red)' }}>{fmtCrore(ins.sold_cr ?? 0)} · {ins.sells}×</span></div>
              {e.insider_note && <p className="mc-plain" style={{ marginTop: 10, color: 'var(--cream)' }}>{e.insider_note}</p>}
              <div className="ct" style={{ marginTop: 14, marginBottom: 6 }}>Latest trades</div>
              {ins.trades.map((t, i) => (
                <div key={t.date + t.person + i} className="stat-r" style={{ alignItems: 'baseline', gap: 8 }}>
                  <span className="sl" style={{ minWidth: 0 }}>
                    <span style={{ color: 'var(--cream-dim)' }}>{t.person}</span>
                    <span style={{ display: 'block', fontSize: 9, color: 'var(--cream-mute)' }}>{t.role} · {day(t.date)}</span>
                  </span>
                  <span className="sv" style={{ fontFamily: 'var(--f-mono)', whiteSpace: 'nowrap', color: t.side === 'buy' ? 'var(--green)' : 'var(--red)' }}>
                    {t.side === 'buy' ? 'Bought' : 'Sold'} {fmtCrore(t.value_cr)}
                  </span>
                </div>
              ))}
            </>
          )}
          <p style={{ fontSize: 9.5, color: 'var(--cream-mute)', marginTop: 12, lineHeight: 1.6 }}>
            From disclosures under SEBI&apos;s insider-trading rules{e.insiders_until ? `; NSE's feed in our data runs to ${day(e.insiders_until)}` : ''}. Gifts, pledges and transfers within the family are left out.
          </p>
        </div>

        {e.deals_since && (
          <div className="card">
            <div className="ct">Bulk &amp; block deals</div>
            {!deals.length && <p className="mc-plain">No bulk or block deals since {day(e.deals_since)}.</p>}
            {deals.map((d, i) => (
              <div key={d.date + d.client + i} className="stat-r" style={{ alignItems: 'baseline', gap: 8 }}>
                <span className="sl" style={{ minWidth: 0 }}>
                  <span style={{ color: 'var(--cream-dim)' }}>{d.client}</span>
                  <span style={{ display: 'block', fontSize: 9, color: 'var(--cream-mute)' }}>
                    {d.kind === 'block' ? 'Block' : 'Bulk'} · {day(d.date)} · {d.quantity.toLocaleString('en-IN')} at ₹{d.price.toLocaleString('en-IN')}
                  </span>
                </span>
                <span className="sv" style={{ fontFamily: 'var(--f-mono)', whiteSpace: 'nowrap', color: d.side === 'buy' ? 'var(--green)' : 'var(--red)' }}>
                  {d.side === 'buy' ? 'Bought' : 'Sold'} {fmtCrore(d.value_cr)}
                </span>
              </div>
            ))}
            <p style={{ fontSize: 9.5, color: 'var(--cream-mute)', marginTop: 12, lineHeight: 1.6 }}>
              Big trades the exchange names publicly: a bulk deal is one investor trading over 0.5% of the company in a day, a block deal a single trade of ₹10 crore or more. They show which funds and large investors are building or cutting a stake. Collected daily since {day(e.deals_since)}.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
