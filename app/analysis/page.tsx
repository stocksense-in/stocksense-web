'use client'
import { useState } from "react";

export default function AnalysisPage() {
  const [openCard, setOpenCard] = useState<string | null>(null);

  const dummyStocks = [
    { symbol: "INFY", name: "Infosys Ltd", sector: "IT", pe: 24.5, roe: 31, de: 0.2, score: 78 },
    { symbol: "HDFCBANK", name: "HDFC Bank", sector: "Banking", pe: 18.2, roe: 16, de: 1.1, score: 72 },
    { symbol: "RELIANCE", name: "Reliance", sector: "Energy", pe: 22, roe: 12, de: 0.6, score: 64 },
  ];

  const renderCard = (stock: any) => {
    const signal =
      stock.score >= 70
        ? { label: "BUY", color: "#00E676" }
        : stock.score >= 50
        ? { label: "WATCH", color: "#D4AF37" }
        : { label: "AVOID", color: "#FF3A3A" };

    return (
      <div
        key={stock.symbol}
        style={{
          background: "#0D1220",
          borderRadius: "10px",
          padding: "16px",
          border: `1px solid ${signal.color}30`,
          boxShadow: `0 0 20px ${signal.color}15`,
          cursor: "pointer",
          transition: "all 0.2s",
        }}
        onClick={() =>
          setOpenCard(openCard === stock.symbol ? null : stock.symbol)
        }
      >
        {/* TOP */}
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
          <div>
            <div style={{ fontSize: "10px", color: "#00D4FF" }}>NSE: {stock.symbol}</div>
            <div style={{ fontSize: "18px", fontWeight: "800" }}>{stock.name}</div>
            <div style={{ fontSize: "11px", color: "#8B9EC0" }}>{stock.sector}</div>
          </div>

          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "22px", fontWeight: "800", color: signal.color }}>
              {stock.score}
            </div>

            <div style={{ fontSize: "9px", color: "#3D5070" }}>SCORE</div>

            {/* SIGNAL */}
            <div
              style={{
                marginTop: "4px",
                fontSize: "10px",
                fontWeight: "700",
                padding: "4px 8px",
                borderRadius: "4px",
                display: "inline-block",
                background: `${signal.color}20`,
                color: signal.color,
                border: `1px solid ${signal.color}40`,
              }}
            >
              {signal.label}
            </div>

            {/* CONFIDENCE BAR */}
            <div
              style={{
                marginTop: "8px",
                height: "4px",
                background: "#1A2540",
                borderRadius: "2px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${stock.score}%`,
                  height: "100%",
                  background: signal.color,
                  boxShadow: `0 0 10px ${signal.color}`,
                }}
              />
            </div>
          </div>
        </div>

        {/* METRICS */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
          <Metric label="P/E" value={stock.pe} idealMin={10} idealMax={20} />
          <Metric label="ROE" value={stock.roe} idealMin={15} idealMax={40} />
          <Metric label="D/E" value={stock.de} idealMin={0} idealMax={1} />
        </div>

        {/* EXPAND */}
        {openCard === stock.symbol && (
          <div
            style={{
              marginTop: "12px",
              paddingTop: "10px",
              borderTop: "1px solid rgba(0,212,255,0.1)",
              fontSize: "12px",
              color: "#8B9EC0",
            }}
          >
            <div style={{ fontWeight: "600", color: "#EEF2FF", marginBottom: "6px" }}>
              Insight:
            </div>

            <div>
              {stock.score >= 70 && "Strong fundamentals. Low risk, high efficiency."}
              {stock.score >= 50 && stock.score < 70 && "Decent company. Needs improvement."}
              {stock.score < 50 && "Weak fundamentals. High risk."}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ padding: "24px", color: "#EEF2FF", background: "#080C14", minHeight: "100vh" }}>
      {/* HEADER */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: "800" }}>Stock Analysis</h1>
        <p style={{ fontSize: "13px", color: "#8B9EC0" }}>
          Fundamentals · Score · Decision Ready
        </p>
      </div>

      {/* FLEX 2 COLUMN */}
      <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
        
        {/* LEFT */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "12px" }}>
          {dummyStocks.filter((_, i) => i % 2 === 0).map(renderCard)}
        </div>

        {/* RIGHT */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "12px" }}>
          {dummyStocks.filter((_, i) => i % 2 !== 0).map(renderCard)}
        </div>

      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  idealMin,
  idealMax,
}: {
  label: string;
  value: number;
  idealMin: number;
  idealMax: number;
}) {
  const max = idealMax * 1.5;
  const percent = Math.min((value / max) * 100, 100);

  const inRange = value >= idealMin && value <= idealMax;

  return (
    <div
      style={{
        background: "#111827",
        padding: "10px",
        borderRadius: "6px",
      }}
    >
      {/* LABEL */}
      <div style={{ fontSize: "8px", color: "#3D5070" }}>{label}</div>

      {/* VALUE */}
      <div
        style={{
          fontSize: "14px",
          fontWeight: "700",
          marginBottom: "6px",
        }}
      >
        {value}
      </div>

      {/* BAR */}
      <div
        style={{
          position: "relative",
          height: "5px",
          background: "#1A2540",
          borderRadius: "3px",
        }}
      >
        {/* IDEAL ZONE */}
        <div
          style={{
            position: "absolute",
            left: `${(idealMin / max) * 100}%`,
            width: `${((idealMax - idealMin) / max) * 100}%`,
            height: "100%",
            background: "rgba(0,230,118,0.3)",
            borderRadius: "3px",
          }}
        />

        {/* NEEDLE */}
        <div
          style={{
            position: "absolute",
            left: `${percent}%`,
            top: "-3px",
            width: "2px",
            height: "10px",
            background: inRange ? "#00E676" : "#FF3A3A",
            boxShadow: `0 0 6px ${
              inRange ? "#00E676" : "#FF3A3A"
            }`,
          }}
        />
      </div>
    </div>
  );
}