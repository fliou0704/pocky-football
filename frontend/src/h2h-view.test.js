import test from 'node:test';
import assert from 'node:assert/strict';
import {defaultPair,pairFile,otherTeamOptions} from './h2h-view.js';
import {routeFromHash} from './season-route.js';
test('H2H routes select distinct modes and current season',()=>{
 for(const mode of ['historical','theoretical']){const route=routeFromHash(`#/h2h/${mode}`,2026);assert.equal(route.page,'h2h');assert.equal(route.mode,mode);assert.equal(route.season,2026);}
});
test('default IDs are deterministic and same-team comparison is prevented',()=>{
 const teams=[{teamId:15},{teamId:3},{teamId:1}];assert.deepEqual(defaultPair(teams),[1,3]);assert.equal(pairFile(3,1),'1-3');assert.equal(pairFile(1,1),null);assert.deepEqual(otherTeamOptions(teams,1).map(t=>t.teamId),[15,3]);
});
