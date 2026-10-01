import test from 'node:test';
import assert from 'node:assert/strict';
import { TEAM_TABS, orderedRoster, slotLabel, validTeamSeasons, resolveTeamSeason } from './team-view.js';

test('Team tabs support Schedule and Roster', () => assert.deepEqual(TEAM_TABS, ['Schedule', 'Roster', 'Draft']));
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

test('draft selection uses team ID, season, and authoritative overall order',async()=>{
 const {teamDraft}=await import('./team-view.js');
 const data={season:2021,picks:[{teamId:1,overallPick:24,round:3,pickInRound:4,position:'RB'},{teamId:2,overallPick:2},{teamId:1,overallPick:4,round:1,pickInRound:4,position:'WR'}]};
 const picks=teamDraft(data,2021,1);
 assert.deepEqual(picks.map(p=>[p.round,p.pickInRound,p.overallPick,p.position]),[[1,4,4,'WR'],[3,4,24,'RB']]);
 assert.deepEqual(teamDraft(data,2022,1),[]);
 assert.deepEqual(teamDraft(null,2021,1),[]);
 assert.equal(teamDraft({season:2022,picks:[{teamId:1,overallPick:1}]},2022,1).length,1);
});
