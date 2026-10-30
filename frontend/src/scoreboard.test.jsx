import React from 'react';
import { readFileSync } from 'node:fs';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import ScoreboardPage, { availableWeeks } from './ScoreboardPage.jsx';
import { Match, Team } from './Match.jsx';
import { App } from './main.jsx';
const json = path => JSON.parse(readFileSync(`${process.cwd()}/public/data/${path}`));
const season = year => ({league: json(`pocky-football/${year}/league.json`), data: json(`pocky-football/${year}/teams.json`)});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.location.hash = ''; });
it('renders the real scoreboard route, changes season, and resets week safely', async () => {
 vi.stubGlobal('fetch', vi.fn(async url => ({ok: true, json: async () => json(String(url).split('data/')[1])})));
 window.location.hash = '#/scoreboard'; render(<App/>);
 await screen.findByRole('heading', {name:'Scoreboard'});
 expect(screen.getByLabelText('Season').value).toBe('2026');
 expect(screen.getByLabelText('Week').value).toBe(String(json('pocky-football/2026/home.json').state.currentWeek));
 fireEvent.change(screen.getByLabelText('Season'), {target:{value:'2021'}});
 await waitFor(() => expect(screen.getByLabelText('Week').value).toBe('1'));
 expect(screen.getAllByText('Final').length).toBeGreaterThan(0);
});
it('navigates all configured weeks with boundaries, future schedules and missing playoffs', () => {
 const props=season(2026);
 props.data={...props.data,matchups:props.data.matchups.filter(m=>m.week<=14).map(m=>m.week===14 ? {...m,status:'upcoming',homeScore:null,awayScore:null,winnerTeamId:null}:m)};
 render(<ScoreboardPage {...props} currentWeek={4}/>);
 fireEvent.click(screen.getByLabelText('Previous week')); expect(screen.getByLabelText('Week').value).toBe('3');
 fireEvent.click(screen.getByLabelText('Next week')); expect(screen.getByLabelText('Week').value).toBe('4');
 fireEvent.change(screen.getByLabelText('Week'), {target:{value:'1'}}); expect(screen.getByLabelText('Previous week').disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('Week'), {target:{value:'14'}}); expect(screen.getAllByText('Upcoming').length).toBe(5); expect(screen.queryByText('0.00')).toBeNull();
 fireEvent.change(screen.getByLabelText('Week'), {target:{value:'17'}}); expect(screen.getByLabelText('Next week').disabled).toBe(true); expect(screen.getByRole('status').textContent).toContain('not available');
 expect(availableWeeks({regularSeasonWeeks:12,playoffTeams:4},[])).toHaveLength(14);
});
it('renders every committed historical playoff period and bye', () => {
 for (const year of [2021,2022,2023,2024,2025]) {
 const props=season(year); const view=render(<ScoreboardPage {...props}/>);
 for(const week of [15,16,17]) fireEvent.change(screen.getByLabelText('Week'), {target:{value:String(week)}});
 expect(screen.getAllByText(/Final/).length).toBeGreaterThan(0); view.unmount();
 }
 const props=season(2021);const bye=props.data.matchups.find(m=>m.status==='bye');
 render(<Match match={bye} teams={new Map(props.league.standings.map(t=>[t.teamId,t]))}/>);expect(screen.getByText('Bye')).toBeTruthy();
});
it('renders committed live status and scores, final outcomes and ties', () => {
 const props=season(2026); props.data={...props.data,matchups:props.data.matchups.map(m=>m.week===4 ? {...m,status:'live',homeScore:0,awayScore:12.34}:m)}; render(<ScoreboardPage {...props} currentWeek={4}/>);
 expect(screen.getAllByText('In Progress').length).toBeGreaterThan(0);
 cleanup(); const match=season(2025).data.matchups[0]; const teams=new Map(props.league.standings.map(t=>[t.teamId,t]));
 render(<Match match={match} teams={teams}/>); expect(screen.getByText('· W')).toBeTruthy();
 cleanup();render(<Match match={{...match,winnerTeamId:null,homeScore:10,awayScore:10}} teams={teams}/>);expect(screen.getAllByText('· Tie')).toHaveLength(2);
});
it('uses committed logos and falls back after image failure or absent logo', () => {
 const team=season(2026).league.standings.find(t=>t.logo);const view=render(<Team team={team}/>);
 const img=view.container.querySelector('img');expect(img.getAttribute('src')).toContain('team-logos/');fireEvent.error(img);fireEvent.error(view.container.querySelector('img'));expect(view.container.querySelector('.team-logo-fallback')).toBeTruthy();
 view.rerender(<Team team={{...team,teamId:999,logo:null}}/>);expect(screen.getByText(team.name)).toBeTruthy();expect(view.container.querySelector('img')).toBeNull();
});
