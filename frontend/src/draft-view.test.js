import test from 'node:test';
import assert from 'node:assert/strict';
import { hydrateDraft } from './draft-view.js';
test('draft evidence resolves to its canonical season pick', () => {
  const pick={season:2025,overallPick:2,playerId:99,value:25};
  const data=hydrateDraft({seasons:{2025:{picks:[pick]}},summary:{bestPicks:[{pickRef:[2025,2]}]}});
  assert.deepEqual(data.summary.bestPicks[0],pick);
});
