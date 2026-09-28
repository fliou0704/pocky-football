import assert from 'node:assert/strict';
import test from 'node:test';
import { assetUrl } from './asset-url.js';

test('local logo uses the GitHub Pages project base', () => {
  assert.equal(assetUrl('team-logos/team-11.png', '/pocky-football/'), '/pocky-football/team-logos/team-11.png');
});

test('verified ESPN logo keeps its absolute URL', () => {
  assert.equal(assetUrl('https://g.espncdn.com/logo.svg', '/pocky-football/'), 'https://g.espncdn.com/logo.svg');
});

test('missing logo stays absent for initials fallback', () => {
  assert.equal(assetUrl(null, '/pocky-football/'), null);
});
