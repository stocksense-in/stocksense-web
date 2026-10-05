import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scanProspectus } from '../lib/rhp.ts';

const pages = [
  'Our top 10 customers contributed 62.4% of our revenue from operations in Fiscal 2025.',
  'There are outstanding litigation proceedings. Claims against us aggregating to Rs. 142.5 crore are pending. ' +
    'Certain criminal proceedings are pending against our Promoters.',
  'The Offer comprises a Fresh Issue of Rs. 300 crore and an Offer for Sale of Rs. 1,200 crore. ' +
    'We intend to use Rs. 75 crore towards general corporate purposes.',
];

test('finds the expected red flags with page numbers', () => {
  const { findings, pages: n } = scanProspectus(pages);
  assert.equal(n, 3);
  const byId = Object.fromEntries(findings.map((f) => [f.id, f]));
  assert.equal(byId['customer-concentration'].severity, 'high');
  assert.equal(byId['customer-concentration'].evidence[0].page, 1);
  assert.match(byId['litigation'].summary, /₹143 crore/);
  assert.ok(byId['criminal-proceedings']);
  assert.match(byId['offer-for-sale'].summary, /80%/);
  assert.match(byId['general-corporate-purposes'].summary, /₹75 crore/);
});

test('high-severity findings come first', () => {
  const order = scanProspectus(pages).findings.map((f) => f.severity);
  assert.deepEqual(order, [...order].sort((a, b) => ['high', 'medium', 'low'].indexOf(a) - ['high', 'medium', 'low'].indexOf(b)));
});

test('a clean document has no findings', () => {
  const result = scanProspectus(['We make biscuits. Revenue grew steadily.']);
  assert.equal(result.findings.length, 0);
  assert.ok(result.clear.length > 5);
});
