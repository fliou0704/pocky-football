import test from 'node:test';
import assert from 'node:assert/strict';
import {searchPlayers,ageOnDate,formatHeight,playerHash,resolvePlayerSeason} from './player-view.js';
import {routeFromHash} from './season-route.js';
const players=[{espnId:7,name:'Ja’Marr Chasé',entityType:'player',position:'WR'},{espnId:-16001,name:'Falcons D/ST',entityType:'team_defense',position:'D/ST'}];
test('search normalizes accents and punctuation, filters defenses separately',()=>{
 assert.equal(searchPlayers(players,'ja marr chase')[0].espnId,7);
 assert.equal(searchPlayers(players,'',{position:'RB'}).length,0);
 assert.equal(searchPlayers(players,'falcons',{type:'team_defense'})[0].espnId,-16001);
});
test('birthdays, nulls, and height formatting use common Brawl behavior',()=>{
 assert.equal(ageOnDate('2000-10-04',new Date(2026,9,3)),25);
 assert.equal(ageOnDate('2000-10-04',new Date(2026,9,4)),26);
 assert.equal(ageOnDate(null),null);assert.equal(formatHeight(null),null);assert.equal(formatHeight(72),'6′ 0″');
});
test('hash player routes preserve canonical signed ESPN IDs and valid presence seasons',()=>{
 const route=routeFromHash(playerHash(-16001,2021),2026);
 assert.equal(route.page,'players');assert.equal(route.playerId,-16001);assert.equal(route.playerSeason,'2021');assert.equal(route.season,2026);
 assert.equal(routeFromHash('#/players/4362628',2026).playerSeason,'All-Time');
 assert.equal(resolvePlayerSeason([{season:2021}],'2026'),'All-Time');
});
