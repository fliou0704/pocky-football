import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveTeamBranding as resolve, validateBranding, DEFAULT_TEAM_COLOR } from './team-branding.js';
const team = { teamId: 11, name: 'Cheese Touch', logo: 'https://example.com/espn.svg' };
const config = { teams: { 11: [
  { startSeason: 2021, endSeason: 2023, primaryColor: '#D92332' },
  { startSeason: 2024, endSeason: 2025, primaryColor: '#2864DC', logoOverride: 'team-logos/team-11-2024.png' },
  { startSeason: 2026, primaryColor: '#1A9F54' },
] } };
test('historical ranges keep color independent of automatic logos', () => {
  validateBranding(config);
  for (const year of [2021, 2022, 2023]) {
    assert.equal(resolve(team, year, config).primaryColor, '#D92332');
    assert.equal(resolve(team, year, config).logo, team.logo);
  }
  for (const year of [2024, 2025]) {
    assert.equal(resolve(team, year, config).primaryColor, '#2864DC');
    assert.deepEqual(resolve(team, year, config).logoCandidates, ['team-logos/team-11-2024.png', team.logo]);
  }
  for (const year of [2026, 2030]) {
    assert.equal(resolve(team, year, config).primaryColor, '#1A9F54');
    assert.equal(resolve(team, year, config).logo, team.logo);
  }
});
test('All-Time uses latest configured period regardless of order or name', () => {
  assert.equal(resolve({ ...team, name: 'Choose Olave' }, 'All-Time', config).primaryColor, '#1A9F54');
  assert.equal(resolve(team, 'All-Time', { teams: { 11: [...config.teams[11]].reverse() } }).logo, team.logo);
});
test('unknown IDs, missing periods and logo-only periods use default green', () => {
  assert.equal(resolve(team, 2020, config).primaryColor, DEFAULT_TEAM_COLOR);
  assert.equal(resolve({ ...team, teamId: 99 }, 2024, config).primaryColor, DEFAULT_TEAM_COLOR);
  const logoOnly = { teams: { 11: [{ startSeason: 2024, logoOverride: 'team-logos/example.svg' }] } };
  assert.equal(resolve(team, 2024, logoOnly).primaryColor, DEFAULT_TEAM_COLOR);
  assert.equal(resolve(team, 'All-Time', logoOnly).logo, 'team-logos/example.svg');
});
test('missing images leave initials as final fallback', () => {
  assert.deepEqual(resolve({ ...team, logo: null }, 2023, config).logoCandidates, []);
  assert.equal(resolve({ ...team, logo: null }, 2023, config).initials, 'C');
});
test('rejects overlapping ranges, malformed IDs, colors and unsafe image paths', () => {
  for (const period of [{ startSeason: 2024, endSeason: 2023 }, { startSeason: 2024, primaryColor: 'red' }, { startSeason: 2024, logoOverride: '../secret.png' }]) assert.throws(() => validateBranding({ teams: { 11: [period] } }));
  assert.throws(() => validateBranding({ teams: { 11: [{ startSeason: 2021 }, { startSeason: 2024 }] } }));
  assert.throws(() => validateBranding({ teams: { 'Cheese Touch': [] } }));
});
