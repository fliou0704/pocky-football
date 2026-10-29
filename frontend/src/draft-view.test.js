import test from 'node:test';
import assert from 'node:assert/strict';
import { hydrateDraft } from './draft-view.js';
test('draft evidence resolves to its canonical season pick', () => {
  const pick={season:2025,overallPick:2,playerId:99,value:25};
  const data=hydrateDraft({seasons:{2025:{picks:[pick]}},summary:{bestPicks:[{pickRef:[2025,2]}]}});
  assert.deepEqual(data.summary.bestPicks[0],pick);
});
test('manager evidence resolves bare references and tolerates unavailable references', () => {
  const pick = { season: 2025, overallPick: 2, playerId: 99, team: { name: 'Team' } };
  const data = hydrateDraft({ seasons: { 2025: { picks: [pick] } }, summary: {
    evidence: [{ season: 2025, overallPick: 2 }, { pickRef: [2025, 2] }, { season: 2025, overallPick: 999 }, null],
    empty: { evidence: null },
  } });
  assert.deepEqual(data.summary.evidence, [pick, pick]);
  assert.deepEqual(data.summary.empty.evidence, []);
});

import { seasonPerformanceRows } from './draft-view.js';
test('single-season performance uses existing team aggregates, sorts raw rank and keeps provisional rows', () => {
  const teams = [{managerId:'b',averageRoundRank:5}, {managerId:'a',averageRoundRank:2}, {managerId:'c',averageRoundRank:null}];
  const season = {teams, overallPerformance:[], performanceEligible:false};
  assert.deepEqual(seasonPerformanceRows(season).map(r => r.managerId), ['a','b','c']);
  assert.equal(teams[0].managerId,'b');
  assert.equal(seasonPerformanceRows({teams:[]}).length,0);
  assert.equal(seasonPerformanceRows({overallPerformance:teams}).length,3);
});
