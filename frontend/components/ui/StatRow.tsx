'use client';
import React from 'react';

export function StatRow({ label, value, valueStyle }: { label: string; value: React.ReactNode; valueStyle?: React.CSSProperties }) {
  return (
    <div className="stat-r">
      <span className="sl">{label}</span>
      <span className="sv" style={valueStyle}>{value}</span>
    </div>
  );
}