'use client';
import React from 'react';
import { pillClass } from '@/lib/utils';

export function Pill({ type, children }: { type: string; children: React.ReactNode }) {
  return <span className={pillClass(type)}>{children}</span>;
}