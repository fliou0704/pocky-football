import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveTeamBranding } from './team-branding.js';
import catalog from '../public/data/pocky-football/team-logos.json' with {type:'json'};
const config={teams:{}};
test('real exact-season archives preserve changed logos, not merely team IDs',()=>{
 for(const [year,teams] of Object.entries(catalog.seasons)) for(const [id,record] of Object.entries(teams)) {
  const result=resolveTeamBranding({teamId:Number(id),name:record.name,logo:null},Number(year),config,catalog);
  assert.equal(result.logo,record.asset);
  assert.equal(result.provenance,record.provenance);
 }
 assert.notEqual(catalog.seasons['2025']['6'].asset,catalog.seasons['2026']['6'].asset);
});
test('historical automatic identity and intentional current manual branding remain independent',()=>{
 const team={teamId:1,name:'Amazon Rockets',logo:catalog.seasons['2021']['1'].sourceUrl};
 assert.equal(resolveTeamBranding(team,'All-Time',config,catalog).logo,catalog.seasons['2021']['1'].asset);
 const manual={teams:{1:[{startSeason:2026,logoOverride:'team-logos/manual.svg'}]}};
 const result=resolveTeamBranding(team,'All-Time',manual,catalog,2021);
 assert.deepEqual(result.logoCandidates,['team-logos/manual.svg',catalog.seasons['2021']['1'].asset,team.logo]);
});
test('missing identity cannot invent a same-franchise logo from a matching name',()=>{
 const result=resolveTeamBranding({teamId:999,name:'Choose Olave',logo:null},2026,config,catalog);
 assert.equal(result.logo,null);assert.equal(result.provenance,'generated-badge');assert.equal(result.initials,'CO');
 const unknownSeason=resolveTeamBranding({teamId:6,name:'Unverified historical identity',logo:null},'All-Time',config,catalog);
 assert.equal(unknownSeason.logo,null);
});
