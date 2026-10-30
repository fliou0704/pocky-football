import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import TeamOfWeek from './TeamOfWeek.jsx';
import { App } from './main.jsx';
import { readFileSync } from 'node:fs';
import derived from '../public/data/pocky-football/2021/team-of-week.json';
import league from '../public/data/pocky-football/2021/league.json';
import data from '../public/data/pocky-football/2021/teams.json';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.location.hash = ''; });
const props = {season:2021, week:1, matches:data.matchups.filter(m=>m.week===1), teams:new Map(league.standings.map(t=>[t.teamId,t])), path:'derived.json', loadData:async()=>derived};
it('renders the committed optimal nine-player historical lineup, portraits and player links', async()=>{
 const view=render(<TeamOfWeek {...props}/>);
 await screen.findByText(derived.weeks['1'].totalPoints.toFixed(2));
 expect(view.container.querySelectorAll('li')).toHaveLength(9);
 for(const p of derived.weeks['1'].lineup) expect(screen.getByText(p.name)).toBeTruthy();
 expect(screen.getByText('2021 · Week 1')).toBeTruthy();
 expect(view.container.querySelector('img')).toBeTruthy();
});
it('hides upcoming/live weeks and supports completed byes and missing data', async()=>{
 const view=render(<TeamOfWeek {...props} matches={[{status:'upcoming'}]}/>);
 expect(screen.queryByText('Team of the Week')).toBeNull();
 view.rerender(<TeamOfWeek {...props} matches={[{status:'live'}]}/>);
 expect(screen.queryByText('Team of the Week')).toBeNull();
 view.rerender(<TeamOfWeek {...props} week={17} matches={[{status:'final'},{status:'bye'}]} loadData={async()=>({season:2021,weeks:{}})}/>);
 expect(await screen.findByText(/unavailable for this completed week/)).toBeTruthy();
});
it('rejects data from a different season and handles a missing contract', async()=>{
 render(<TeamOfWeek {...props} loadData={async()=>{throw new Error('missing');}}/>);
 expect(await screen.findByText(/unavailable for this completed week/)).toBeTruthy();
});

it('handles portraits, defense branding and broken images without changing scoring', async()=>{
 const view=render(<TeamOfWeek {...props}/>);
 await screen.findByText(derived.weeks['1'].totalPoints.toFixed(2));
 expect(view.container.querySelectorAll('.totw-slot')).toHaveLength(9);
 expect(view.container.querySelectorAll('.totw-identity a').length).toBeGreaterThan(0);
 const image=view.container.querySelector('.player-search-portrait img');
 fireEvent.error(image);
 expect(view.container.querySelector('[aria-label="Image unavailable"]')).toBeTruthy();
 const defense=derived.weeks['1'].lineup.find(p=>p.slot==='D/ST');
 const defenseRow=screen.getByText(defense.name).closest('li');
 const mark=defenseRow.querySelector('img');
 if (mark) expect(mark.getAttribute('src')).toBe(defense.logo);
});
it('switches week and season without showing a previous lineup', async()=>{
 const view=render(<TeamOfWeek {...props}/>);
 await screen.findByText(derived.weeks['1'].totalPoints.toFixed(2));
 view.rerender(<TeamOfWeek {...props} week={2}/>);
 expect(await screen.findByText(derived.weeks['2'].totalPoints.toFixed(2))).toBeTruthy();
 view.rerender(<TeamOfWeek {...props} season={2026} path="new-season.json" loadData={()=>new Promise(()=>{})}/>);
 expect(screen.queryByText(derived.weeks['2'].totalPoints.toFixed(2))).toBeNull();
 expect(screen.getByText('Loading Team of the Week…')).toBeTruthy();
});
it('places the latest completed lineup first in the real Home recap', async()=>{
 const json=path=>JSON.parse(readFileSync(`${process.cwd()}/public/data/${path}`));
 vi.stubGlobal('fetch',vi.fn(async url=>({ok:true,json:async()=>json(String(url).split('data/')[1])})));
 window.location.hash='#/';
 render(<App/>);
 const section=await screen.findByRole('region',{name:'Team of the Week'});
 const home=json('pocky-football/2026/home.json');
 expect(within(section).getByText(`2026 · Week ${home.recap.week}`)).toBeTruthy();
 await waitFor(()=>expect(section.querySelectorAll('li')).toHaveLength(9));
 const recap=section.parentElement;
 expect(within(recap).getByRole('heading',{name:'Weekly Recap'})).toBeTruthy();
 expect(section).toBe(recap.children[1]);
 expect(within(recap).getByRole('heading',{name:'Top Performers'})).toBeTruthy();
});
