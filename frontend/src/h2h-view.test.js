import test from 'node:test';
import assert from 'node:assert/strict';
import {pairFile,otherTeamOptions,recordText,recordCaption,h2hHash,nextExpanded,loadedView} from './h2h-view.js';
import {routeFromHash} from './season-route.js';
test('H2H routes start with no team selection',()=>{
 for(const mode of ['historical','theoretical']){const r=routeFromHash(`#/h2h/${mode}`,2026);assert.equal(r.mode,mode);assert.equal(r.firstId,null);assert.equal(r.secondId,null);assert.equal(pairFile(r.firstId,r.secondId),null);}
});
test('mode routes preserve explicit selections and refresh state',()=>{
 for(const mode of ['historical','theoretical','historical','theoretical']){const r=routeFromHash(h2hHash(mode,15,2),2026);assert.equal(r.firstId,15);assert.equal(r.secondId,2);assert.equal(r.mode,mode);}
});
test('both teams are required and same-team selection is prevented',()=>{
 assert.equal(pairFile(null,1),null);assert.equal(pairFile(1,null),null);assert.equal(pairFile(1,1),null);assert.equal(pairFile(3,1),'1-3');assert.deepEqual(otherTeamOptions([{teamId:1},{teamId:2}],1),[{teamId:2}]);
});
test('record hides zero ties and places nonzero ties in the middle',()=>{
 assert.equal(recordText({wins:4,losses:5,ties:0}),'4 – 5');assert.equal(recordText({wins:4,losses:5,ties:1}),'4 – 1 – 5');assert.equal(recordCaption({ties:0}),'Team A wins · Team B wins');
});
test('accordion allows one row and toggles closed',()=>{
 assert.equal(nextExpanded(null,'A'),'A');assert.equal(nextExpanded('A','B'),'B');assert.equal(nextExpanded('B','B'),null);
});
test('stale mode or pair payload cannot be rendered',()=>{
 const loaded={key:'historical/1/2',data:{summary:{}}};assert.equal(loadedView(loaded,'theoretical/1/2'),null);assert.equal(loadedView(loaded,'historical/1/3'),null);assert.equal(loadedView(loaded,'historical/1/2'),loaded.data);
});
