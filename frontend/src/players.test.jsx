import React from 'react';
import {afterEach,expect,test,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import PlayersPage,{PlayerDetail,PlayerSearch} from './PlayersPage.jsx';
afterEach(cleanup);
const Team=({team})=><span>{team.name}</span>;
const Section=({title,children})=><section><h2>{title}</h2>{children}</section>;
const team={teamId:1,name:'Historical Team'};
const week=(season,week,state,points)=>({season,week,gameState:state,points,nflOpponent:'BUF',nflStats:{receptions:state==='played'?0:null}});
const detail={metadataGeneratedAt:'2026-10-03T17:15:00Z',currentSeason:2026,statColumns:[{key:'receptions',label:'Rec'}],profile:{espnId:7,name:'A.J. Brown',entityType:'player',position:'WR',nflTeam:'CIN',headshot:'https://example.com/image.png'},seasons:[{season:2026,complete:false,seasonStats:{gp:1,points:0,fppg:0,nflStats:{receptions:0}},ownership:[{team}],draft:[{timestamp:'2026-09-09T12:00:00Z',team,round:2,pickInRound:3,overallPick:13}],transactions:[{type:'waiver_add',timestamp:'2026-09-18T12:00:00Z',fromTeams:[],toTeams:[team]}],weeks:[week(2026,1,'played',0),week(2026,2,'bye',0),week(2026,3,'did_not_play',0),week(2026,4,'upcoming',0)]},{season:2025,complete:true,seasonStats:{gp:1,points:12,fppg:12,nflStats:{receptions:2}},ownership:[{team}],draft:[],transactions:[],weeks:[week(2025,17,'played',12)]}]};
test('landing is search-only and normalized matching preserves displayed name',()=>{
 render(<PlayerSearch players={[detail.profile]}/>);expect(screen.queryByRole('link')).toBeNull();expect(screen.queryByRole('table')).toBeNull();expect(screen.queryByRole('combobox')).toBeNull();
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:' AJ   brown '}});expect(screen.getByRole('link',{name:/A.J. Brown/}).getAttribute('href')).toBe('#/players/7');
});
test('profile timestamp, three tabs, simplified Career and no global selector',()=>{
 render(<PlayerDetail detail={detail} Section={Section} Team={Team}/>);
 expect(screen.getByText(/Last updated:/)).toBeTruthy();expect(screen.getByText('Fantasy Team')).toBeTruthy();expect(screen.getByText('GP')).toBeTruthy();expect(screen.getByText('FPPG')).toBeTruthy();expect(screen.getByText('Rec')).toBeTruthy();
 expect(screen.queryByRole('combobox')).toBeNull();expect(screen.queryByText('Fantasy Team History')).toBeNull();expect(screen.queryByText('Season History')).toBeNull();expect(screen.queryByRole('tab',{name:'Draft'})).toBeNull();expect(document.querySelector('.player-stats')).toBeNull();
 expect(screen.getAllByRole('tab').map(t=>t.textContent)).toEqual(['Career','Game Log','Transactions']);
});
test('Game Log current-only recents, internal season selection, states, and real played zero',()=>{
 render(<PlayerDetail detail={detail} Section={Section} Team={Team}/>);fireEvent.click(screen.getByRole('tab',{name:'Game Log'}));
 const tables=screen.getAllByRole('table');expect(within(tables[0]).getAllByRole('row').length).toBe(2);expect(within(tables[0]).getByText('0.00')).toBeTruthy();
 expect(screen.getByText('BYE')).toBeTruthy();expect(screen.getByText('BUF · Did not play')).toBeTruthy();expect(screen.getByText('BUF · Upcoming')).toBeTruthy();expect(screen.queryByText('STATUS')).toBeNull();
 const selector=screen.getByRole('combobox',{name:'Game Log season'});expect(selector.value).toBe('2026');fireEvent.change(selector,{target:{value:'2025'}});expect(screen.getByText('12.00')).toBeTruthy();expect(within(screen.getAllByRole('table')[0]).queryByText('12.00')).toBeNull();
});
test('Transactions merges drafts newest first without pick-in-round or coverage selectors',()=>{
 render(<PlayerDetail detail={detail} Section={Section} Team={Team}/>);fireEvent.click(screen.getByRole('tab',{name:'Transactions'}));
 const rows=screen.getAllByRole('listitem');expect(rows[0].textContent).toContain('Waivers');expect(rows[1].textContent).toContain('Drafted by');expect(rows[1].textContent).toContain('Round 2');expect(rows[1].textContent).toContain('Overall Pick 13');
 expect(screen.queryByRole('combobox')).toBeNull();expect(screen.queryByText(/coverage/)).toBeNull();expect(screen.queryByText(/Pick in round/)).toBeNull();
});
test('direct profile fetch has no back button and D/ST has no human biography',async()=>{
 const load=vi.fn(p=>Promise.resolve(p==='index'?{players:[{...detail.profile,path:'profile'}]}:detail));
 const r=render(<PlayersPage path="index" playerId={7} loadData={load} Section={Section} Team={Team}/>);
 await screen.findByRole('heading',{name:'A.J. Brown'});expect(screen.queryByRole('link',{name:/All players/i})).toBeNull();
 r.rerender(<PlayersPage path="index" playerId={999} loadData={load} Section={Section} Team={Team}/>);await screen.findByText('Player not found in Pocky Football history.');
 cleanup();render(<PlayerDetail detail={{...detail,profile:{espnId:-16001,name:'Falcons D/ST',entityType:'team_defense',position:'D/ST'}}} Section={Section} Team={Team}/>);expect(screen.queryByText('Born')).toBeNull();expect(screen.getByText('Pocky Football Team Defense')).toBeTruthy();
});

test('full NFL log includes week 18 chronologically while recents stay newest first',()=>{
 const full={...detail,seasons:[{...detail.seasons[0],weeks:[week(2026,18,'played',18),week(2026,2,'played',2),week(2026,1,'played',1)]},detail.seasons[1]]};
 render(<PlayerDetail detail={full} Section={Section} Team={Team}/>);fireEvent.click(screen.getByRole('tab',{name:'Game Log'}));
 const tables=screen.getAllByRole('table');const weeks=t=>within(t).getAllByRole('row').slice(1).map(r=>within(r).getByRole('rowheader').textContent);
 expect(weeks(tables[0])).toEqual(['18','2','1']);expect(weeks(tables[1])).toEqual(['1','2','18']);
});
test('draft, waiver, free-agent, drop and trade descriptions have correct directions',()=>{
 const other={teamId:2,name:'Receiving Team'};
 const all={...detail,seasons:[{...detail.seasons[0],transactions:[
 {type:'drop',timestamp:'2026-09-21T12:00:00Z',fromTeams:[team],toTeams:[]},
 {type:'trade',timestamp:'2026-09-20T12:00:00Z',fromTeams:[team],toTeams:[other]},
 {type:'free_agent_add',timestamp:'2026-09-19T12:00:00Z',fromTeams:[],toTeams:[team]},
 ...detail.seasons[0].transactions]}]};
 render(<PlayerDetail detail={all} Section={Section} Team={Team}/>);fireEvent.click(screen.getByRole('tab',{name:'Transactions'}));
 const text=screen.getAllByRole('listitem').map(r=>r.textContent);
 expect(text[0]).toContain('Dropped by Historical Team');expect(text[0]).not.toContain('Added');
 expect(text[1]).toContain('Traded from Historical Team to Receiving Team');expect(text[2]).toContain('Added by Historical Team via Free Agency');expect(text[3]).toContain('via Waivers');expect(text[4]).toContain('Drafted by');
});
