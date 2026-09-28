import assert from 'node:assert/strict';
import test from 'node:test';
import { formatRecord } from './record.js';

test('formats a record without ties', () => {
  assert.equal(formatRecord({ wins: 10, losses: 4, ties: 0 }), '10-4');
});

test('includes nonzero ties', () => {
  assert.equal(formatRecord({ wins: 9, losses: 4, ties: 1 }), '9-4-1');
});
