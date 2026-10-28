import test from 'node:test';
import assert from 'node:assert/strict';
import { routeFromHash, selectedTeamId } from './season-route.js';

test('historical season and team are read from hash route', () => {
  assert.deepEqual(routeFromHash('#/teams/2021/9', 2026), {page:'teams', season:2021, teamId:9});
  assert.equal(routeFromHash('#/standings/2025', 2026).season, 2025);
});

test('missing team ID after season switch picks a valid team in that season', () => {
  assert.equal(selectedTeamId([{teamId:1},{teamId:9}], 16), 1);
  assert.equal(selectedTeamId([{teamId:1},{teamId:9}], 9), 9);
});

test('Draft routes support Summary and historical years', () => {
  assert.equal(routeFromHash('#/draft', 2026).draftYear, 'Summary');
  assert.equal(routeFromHash('#/draft/2021?pick=40', 2026).draftYear, '2021');
  assert.equal(routeFromHash('#/draft/2021', 2026).page, 'draft');
});
