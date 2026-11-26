'use client';
import type { StockOut } from '@/lib/api';
import { fmtCrore, fmtNum, fmtPct, fmtRupees, stockScoreColor } from '@/lib/api';

export function PeersTable({ stock, peers, onOpen }: { stock: StockOut; peers: StockOut[]; onOpen: (symbol: string) => void }) {
  const rows = [stock, ...peers.filter(p => p.symbol !== stock.symbol)];
  return (
    <div className="card">
      <div className="ct">Largest {stock.sector_label ?? 'sector'} companies</div>
      <div style={{ overflowX: 'auto' }}>
        <table className="tbl">
          <thead>
            <tr><th>Company</th><th>Price</th><th>Market cap</th><th>P/E</th><th>ROE</th><th>Debt/eq</th><th>Margin</th><th>Score</th></tr>
          </thead>
          <tbody>
            {rows.map(p => {
              const self = p.symbol === stock.symbol;
              return (
                <tr key={p.symbol} onClick={() => !self && onOpen(p.symbol)} style={{ cursor: self ? 'default' : 'pointer', background: self ? 'rgba(201,168,76,0.05)' : undefined }}>
                  <td>
                    <div style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--gold)' }}>{p.symbol}</div>
                    <div style={{ fontSize: 9, color: 'var(--cream-mute)', marginTop: 2 }}>{p.name}</div>
                  </td>
                  <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtRupees(p.price, 0)}</td>
                  <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtCrore(p.market_cap)}</td>
                  <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtNum(p.pe)}</td>
                  <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtPct(p.roe)}</td>
                  <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtNum(p.de, 2)}</td>
                  <td style={{ fontFamily: 'var(--f-mono)' }}>{fmtPct(p.margin)}</td>
                  <td style={{ fontFamily: 'var(--f-mono)', color: stockScoreColor(p.score) }}>{p.score ?? '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mc-plain" style={{ marginTop: 10 }}>Click a peer to open it. Comparing within a sector matters: a P/E that is cheap for a software company can be expensive for a bank.</p>
    </div>
  );
}
