import test from 'node:test';
import assert from 'node:assert/strict';
import { TEAM_TABS, orderedRoster, slotLabel, validTeamSeasons, resolveTeamSeason } from './team-view.js';

test('Team tabs support Schedule and Roster', () => assert.deepEqual(TEAM_TABS, ['Schedule', 'Roster']));
test('lineup uses fantasy slots and preserves repeated slot order', () => {
 const players = ['BE','WR','RB','IR','K','QB','RB/WR/TE','TE','RB','D/ST','WR'].map((slot,index)=>({slot,position:'WR',playerId:index}));
 const rows=orderedRoster(players);
 assert.deepEqual(rows.map(p=>p.displaySlot),['QB','RB','RB','WR','WR','TE','FLEX','D/ST','K','BE','IR']);
 assert.deepEqual(rows.filter(p=>p.displaySlot==='RB').map(p=>p.playerId),[2,8]);
 assert.equal(rows[0].position,'WR');
 assert.equal(slotLabel('BE'),'BE');
});
test('season choices and fallback use only team ID membership',()=>{
 const manifest={seasons:[2026,2025,2021],teamSeasons:{15:[2026,2025],1:[2026,2025,2021]}};
 assert.deepEqual(validTeamSeasons(manifest,15),[2026,2025]);
 assert.equal(resolveTeamSeason(manifest,15,2021),2026);
 assert.equal(resolveTeamSeason(manifest,1,2021),2021);
});
