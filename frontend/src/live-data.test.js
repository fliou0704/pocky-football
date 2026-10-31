import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { applyLive, loadCurrent, loadLive, contentHash } from './live-data.js';

if (!globalThis.crypto) globalThis.crypto = webcrypto;
const prefix='pocky-football/2026/';
const match={week:8,homeTeamId:1,awayTeamId:2,homeScore:12.5,awayScore:-1,status:'live'};
const live={season:2026,week:8,baseGenerationId:'base',matchups:[match],lineups:{teams:{'1':[{playerId:10,points:12.5,slot:'QB'}],'2':[]}}};

test('shared overlay updates Home and current scoreboard while retaining historical weeks and season totals',()=>{
 const base={matchups:[{week:7,status:'final'}, {...match,homeScore:0}],teams:{'1':{roster:[{playerId:10,seasonPoints:150}],weeks:[{week:7,score:30},{week:8,score:0}]}}};
 const value=applyLive(prefix+'teams.json',base,live);
 assert.equal(value.matchups[1].homeScore,12.5);
 assert.equal(value.teams['1'].roster[0].seasonPoints,150);
 assert.equal(value.teams['1'].roster[0].liveWeek,8);
 assert.equal(value.teams['1'].weeks[0].score,30);
 assert.equal(base.matchups[1].homeScore,0);
 assert.equal(applyLive('pocky-football/2025/teams.json',base,live),base);
 assert.equal(applyLive(prefix+'home.json',{state:{currentWeek:8}},live).currentMatchups[0].homeScore,12.5);
 assert.equal(applyLive(prefix+'lineups/8.json',{},live),live.lineups);
});

test('raw-byte integrity admits only a matching overlay and all matching sources',async()=>{
 const body=JSON.stringify(live);
 const meta={schemaVersion:1,mode:'live',generationId:'new',baseGenerationId:'base',liveContentHash:await contentHash(body)};
 const bundle=await loadLive(async path=>path.includes('refresh.json') ? meta : body);
 assert.equal(bundle.live.week,8);
 const source=JSON.stringify({state:{currentWeek:8}});
 bundle.live.sourceFileHashes={[prefix+'home.json']:await contentHash(source)};
 const rows=await loadCurrent([prefix+'home.json',null],async(path,opts)=>opts?.raw ? source : {fallback:true},bundle);
 assert.equal(rows[0].currentMatchups[0].homeScore,12.5);assert.equal(rows[1],null);
 const fallback=await loadCurrent([prefix+'home.json'],async(path,opts)=>opts?.raw ? '{}' : {fallback:true},bundle);
 assert.equal(fallback[0].fallback,true);
 assert.equal(await loadLive(async path=>path.includes('refresh') ? {...meta,liveContentHash:'wrong'} : body),null);
 assert.equal(await loadLive(async()=>{throw Error('offline');}),null);
});
