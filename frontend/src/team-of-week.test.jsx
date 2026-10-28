import React from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import TeamOfWeek from './TeamOfWeek.jsx';
import derived from '../public/data/pocky-football/2021/team-of-week.json';
import league from '../public/data/pocky-football/2021/league.json';
import data from '../public/data/pocky-football/2021/teams.json';
afterEach(cleanup);
const props = {season:2021, week:1, matches:data.matchups.filter(m=>m.week===1), teams:new Map(league.standings.map(t=>[t.teamId,t])), path:'derived.json', loadData:async()=>derived};
it('renders the committed optimal nine-player historical lineup and ownership', async()=>{
 const view=render(<TeamOfWeek {...props}/>);
 await screen.findByText(`${derived.weeks['1'].totalPoints.toFixed(2)} FPTS`);
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
