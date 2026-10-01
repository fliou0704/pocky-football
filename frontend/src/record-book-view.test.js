import test from 'node:test';
import assert from 'node:assert/strict';
import { recordView, recordValue } from './record-book-view.js';
import { routeFromHash } from './season-route.js';

test('Record Book route defaults to All-Time and preserves season on refresh',()=>{
  assert.equal(routeFromHash('#/record-book',2026).recordYear,'All-Time');
  assert.equal(routeFromHash('#/record-book/2021',2026).recordYear,'2021');
  assert.equal(routeFromHash('#/record-book/2025',2026).page,'record-book');
});
test('precomputed all-time and single-season views with invalid year fallback',()=>{
  const data={allTime:{id:'all'},seasons:{2021:{id:'2021'}}};
  assert.equal(recordView(data,'All-Time').id,'all');
  assert.equal(recordView(data,'2021').id,'2021');
  assert.equal(recordView(data,'1900').id,'all');
});
test('record presentation retains ties and unequal schedule comparison',()=>{
  assert.equal(recordValue({unit:'record'},{wins:9,losses:4,ties:1,value:9.5/14}),'9-4-1 · 67.9%');
  assert.equal(recordValue({unit:'points'},{value:0}),'0.00 FPTS');
  assert.equal(recordValue({unit:'games'},{value:4}),'4 games');
});

test('incomplete Record Book year falls back to All-Time and is absent from choices',()=>{
 const data={years:[2025,2024],allTime:{id:'all'},seasons:{2025:{id:'2025'},2024:{id:'2024'}}};
 assert.equal(recordView(data,'2026').id,'all');assert.equal(data.years.includes(2026),false);
});
test('ranked result keys distinguish both sides and player stints',async()=>{
 const {rankedEntryKey}=await import('./record-book-view.js');
 assert.notEqual(rankedEntryKey({season:2021,week:1,team:{teamId:1}}),rankedEntryKey({season:2021,week:1,team:{teamId:2}}));
 assert.notEqual(rankedEntryKey({season:2021,playerId:10,acquiredAt:'first'}),rankedEntryKey({season:2021,playerId:10,acquiredAt:'second'}));
});
