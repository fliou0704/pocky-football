import React from 'react';
import { readFileSync } from 'node:fs';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import WeeklyRecap, { PreviewIndicators, matchupId } from './WeeklyRecap.jsx';
import ScoreboardPage from './ScoreboardPage.jsx';
import TeamOfWeek from './TeamOfWeek.jsx';
import { Match, BrandingSeason } from './Match.jsx';
import { Standings } from './main.jsx';
const json = path => JSON.parse(readFileSync(`${process.cwd()}/public/data/pocky-football/${path}`));
const league = json('2021/league.json'), data=json('2021/teams.json'), weekly=json('2021/weekly.json'), totw=json('2021/team-of-week.json');
const teams = new Map(league.standings.map(t=>[t.teamId,t]));
const loader = async path => path.endsWith('weekly.json') ? weekly : totw;
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('shares ordered sections, expands all ranked teams and deduplicates awards',async()=>{
 const recap={...weekly.weeks[1],awards:[{id:'one',labels:['Closest Matchup','Top Two Scorers'],match:data.matchups[0]}]};
 const view=render(<WeeklyRecap recap={recap} teams={teams} season={2021} teamOfWeekPath="2021/team-of-week.json" loadData={loader}/>);
 await screen.findByText(totw.weeks[1].totalPoints.toFixed(2));
 const headings=screen.getAllByRole('heading').map(h=>h.textContent);
 expect(headings.slice(0,5)).toEqual(['Weekly Recap','Team of the Week','Top Performers','Top Team','Closest Matchup · Top Two Scorers']);
 expect(view.container.querySelectorAll('.match')).toHaveLength(1);
 expect(screen.queryByRole('list',{name:'Weekly team scoring leaderboard'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'View full leaderboard'}));
 const list=screen.getByRole('list',{name:'Weekly team scoring leaderboard'});
 expect(within(list).getAllByRole('listitem')).toHaveLength(league.standings.length);
 expect(list.querySelector('a').getAttribute('href')).toContain('/2021/');
 fireEvent.click(screen.getByRole('button',{name:'Hide full leaderboard'}));
 expect(screen.queryByRole('list',{name:'Weekly team scoring leaderboard'})).toBeNull();
});
it('selects the historical recap, collapses and clears on week changes; disables unfinished weeks',async()=>{
 const view=render(<ScoreboardPage league={league} data={data} teamOfWeekPath="2021/team-of-week.json" loadData={loader}/>);
 const button=screen.getByRole('button',{name:'View Weekly Recap'});
 await waitFor(()=>expect(button.disabled).toBe(false));
 fireEvent.click(button);expect(screen.getByRole('heading',{name:'Weekly Recap'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Hide Weekly Recap'}));expect(screen.queryByRole('heading',{name:'Weekly Recap'})).toBeNull();
 fireEvent.click(button);fireEvent.change(screen.getByLabelText('Week'),{target:{value:'2'}});
 expect(screen.queryByRole('heading',{name:'Weekly Recap'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'View Weekly Recap'}));
 expect(screen.getByText('Week 2 · Final')).toBeTruthy();
 view.rerender(<ScoreboardPage key="unfinished" league={league} data={{...data,matchups:data.matchups.filter(m=>m.week===1).map(m=>({...m,status:'live'}))}} currentWeek={1} teamOfWeekPath="missing" loadData={async()=>weekly}/>);
 await waitFor(()=>expect(screen.getByRole('button',{name:'View Weekly Recap'}).disabled).toBe(true));
});
it('only renders preview indicators for upcoming/live Home presentations',()=>{
 const match={week:4,homeTeamId:1,awayTeamId:2,status:'upcoming'};
 const contract={previews:{4:{[matchupId(2026,match)]:['Top Two Showdown','Rivalry Tied 4–4','Hot Streak Showdown']}}};
 const view=render(<PreviewIndicators match={match} season={2026} weekly={contract}/>);
 expect(screen.getByText('Top Two Showdown')).toBeTruthy();expect(screen.getByText('Rivalry Tied 4–4')).toBeTruthy();
 view.rerender(<PreviewIndicators match={{...match,status:'live'}} season={2026} weekly={contract}/>);expect(screen.getByText('Hot Streak Showdown')).toBeTruthy();
 view.rerender(<PreviewIndicators match={{...match,status:'final'}} season={2026} weekly={contract}/>);expect(view.container.textContent).toBe('');
 view.rerender(<Match match={{...match,homeScore:10,awayScore:11}} teams={teams}/>);expect(screen.queryByText('Top Two Showdown')).toBeNull();
});
it('uses historical fantasy ownership and season logo resolution; distinguishes unknown from free agent',async()=>{
 const lineup=totw.weeks[1].lineup.map((p,i)=> i===0 ? {...p,teamId:null} : i===1 ? {...p,teamId:undefined} : p);
 const view=render(<BrandingSeason.Provider value={2021}><TeamOfWeek season={2021} week={1} completedWeek teams={teams} path="ownership" loadData={async()=>({...totw,weeks:{1:{...totw.weeks[1],lineup}}})}/></BrandingSeason.Provider>);
 expect((await screen.findAllByText('Free Agent')).length).toBeGreaterThan(0);expect(screen.getByText('Unknown')).toBeTruthy();
 for(const p of lineup.filter(p=>teams.has(p.teamId))) {
 const row=screen.getByText(p.name).closest('li');
 expect(within(row).getByText(teams.get(p.teamId).name)).toBeTruthy();
 expect(row.querySelector('.totw-owner a').getAttribute('href')).toBe(`#/teams/2021/${p.teamId}`);
 }
 expect(view.container.querySelector('.totw-owner img[data-logo-provenance]')).toBeTruthy();
 expect(view.container.querySelectorAll('.totw-slot')).toHaveLength(9);
});
it('sorts all-play in both directions while preserving official ranks and normal records',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>weekly})));
 const view=render(<Standings league={league}/>);
 await waitFor(()=>expect(view.container.querySelector('tbody').textContent).toContain('–'));
 await waitFor(()=>expect(view.container.querySelector('tbody').textContent).toContain(`${weekly.allPlay[league.standings[0].teamId].wins}–`));
 fireEvent.click(screen.getByRole('button',{name:/^All-play/}));
 const best=[...league.standings].sort((a,b)=>weekly.allPlay[b.teamId].wins-weekly.allPlay[a.teamId].wins || a.rank-b.rank)[0];
 expect(view.container.querySelector('tbody tr').textContent).toContain(best.name);
 expect(view.container.querySelector('tbody tr td').textContent).toBe(String(best.rank));
 expect(view.container.querySelector('[aria-sort="descending"]')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:/^All-play/}));expect(view.container.querySelector('[aria-sort="ascending"]')).toBeTruthy();
});
