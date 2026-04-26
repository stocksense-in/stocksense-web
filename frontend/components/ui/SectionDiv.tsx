'use client';
import React from 'react';

export function SectionDiv({ label }: { label: string }) {
  return (
    <div className="sec-div">
      <span>{label}</span>
      <hr />
    </div>
  );
}