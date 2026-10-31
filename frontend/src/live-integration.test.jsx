import React from 'react';
import { readFileSync } from 'node:fs';
import { webcrypto, createHash } from 'node:crypto';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { afterEach, beforeEach, test, expect, vi } from 'vitest';
import { App } from './main.jsx';

const raw = path => readFileSync(`${process.cwd()}/public/data/${path}`, 'utf8');
const hash = text => createHash('sha256').update(text).digest('hex');
const prefix='pocky-football/2026/';
const home=JSON.parse(raw(prefix+'home.json')), teams=JSON.parse(raw(prefix+'teams.json'));
const week=home.state.currentWeek;
const live={schemaVersion:1,season:2026,week,baseGenerationId:'base',
 matchups:teams.matchups.filter(m=>m.week===week).map(m=>({...m,status:'live',homeScore:11.25,awayScore:11.25})),
 lineups:{teams:Object.fromEntries(Object.entries(teams.teams).map(([tid,t])=>[tid,t.roster.map(p=>({...p,points:p.group==='starter'?1.25:.75}))]))},
 sourceFileHashes:Object.fromEntries(['league','home','teams'].map(n=>[prefix+n+'.json',hash(raw(prefix+n+'.json'))]))};
const body=JSON.stringify(live);
const meta={schemaVersion:1,mode:'live',generationId:'test-live',baseGenerationId:'base',liveContentHash:hash(body)};

beforeEach(()=>{
 vi.stubGlobal('crypto',webcrypto);
 vi.stubGlobal('fetch',vi.fn(async url=>{
  const path=String(url).split('data/')[1].split('?')[0];
  const text=path.endsWith('/refresh.json')?JSON.stringify(meta):path.endsWith('/live.json')?body:raw(path);
  return {ok:true,json:async()=>JSON.parse(text),text:async()=>text};
 }));
});
afterEach(()=>{cleanup();vi.unstubAllGlobals();window.location.hash='';});

test('current scoreboard uses one coherent live overlay and keeps selected week',async()=>{
 window.location.hash='#/scoreboard/2026';render(<App/>);
 await screen.findAllByText('11.25');
 expect(screen.getByLabelText('Week').value).toBe(String(week));
 fireEvent.change(screen.getByLabelText('Week'),{target:{value:'1'}});
 expect(screen.getByLabelText('Week').value).toBe('1');
 expect(screen.queryAllByText('11.25')).toHaveLength(0);
});

test('current roster displays week points while full season overview is preserved',async()=>{
 window.location.hash='#/teams/2026/6';render(<App/>);
 await screen.findByRole('tab',{name:'Roster'});
 fireEvent.click(screen.getByRole('tab',{name:'Roster'}));
 await screen.findAllByText(`Week ${week} FPTS`);
 expect(screen.getAllByText('1.25')).toHaveLength(9);
 expect(screen.getAllByText('0.75').length).toBeGreaterThan(0);
 expect(screen.getByText('Points for')).toBeTruthy();
});
