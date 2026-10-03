import React from 'react';
import {afterEach,expect,test,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import PlayersPage,{PlayerDetail,PlayerSearch} from './PlayersPage.jsx';
afterEach(cleanup);
const Team=({team})=><span>{team.name}</span>;
const Section=({title,children})=><section><h2>{title}</h2>{children}</section>;
const team={teamId:1,name:'Historical Team'};
const stats={weeks:1,points:12,average:12,high:{season:2021,week:1,points:12},starts:0,starterPoints:null};
const detail={profile:{espnId:7,name:'Example Player',entityType:'player',position:'WR',nflTeam:'CIN',headshot:'https://example.com/image.png'},career:stats,seasons:[{season:2021,complete:true,summary:stats,ownership:[{team,weeks:[1],evidence:['weekly_roster']}],rosterSnapshot:[],rosterSnapshotLabel:'Final roster',draft:[{team,round:2,pickInRound:3,overallPick:13}],transactions:[{type:'waiver_add',timestamp:'2021-09-01T12:00:00Z',week:1,fromTeams:[],toTeams:[team]}],activityCoverage:{status:'likely_complete'},weeks:[{season:2021,week:1,status:'final',points:12,nflTeam:'BUF',nflOpponent:'NYJ',rosters:[{team,slot:'BE',points:12}]}]}]};
test('landing selection, search, position and defense filters',()=>{
 render(<PlayerSearch players={[detail.profile,{espnId:-16001,name:'Falcons D/ST',position:'D/ST',entityType:'team_defense',nflTeam:'ATL'}]}/>);
 expect(screen.getByRole('link',{name:/Example Player/}).getAttribute('href')).toBe('#/players/7');
 fireEvent.change(screen.getByRole('combobox',{name:'Player position'}),{target:{value:'RB'}});expect(screen.getByText('No Pocky Football players found.')).toBeTruthy();
 fireEvent.change(screen.getByRole('combobox',{name:'Player entity'}),{target:{value:'team_defense'}});expect(screen.getByRole('link',{name:/Falcons/}).getAttribute('href')).toBe('#/players/-16001');
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'unknown'}});expect(screen.queryByRole('link')).toBeNull();
});
test('profile nulls, tabs, historical log, season selection and draft',()=>{
 const change=vi.fn();render(<PlayerDetail detail={detail} requestedSeason="2026" onSeasonChange={change} Section={Section} Team={Team}/>);
 expect(screen.getByRole('combobox',{name:'Player season'}).value).toBe('All-Time');
 expect(screen.queryByText('Age')).toBeNull();expect(screen.queryByText('NFL Draft')).toBeNull();expect(screen.getByRole('img',{name:/headshot/})).toBeTruthy();
 fireEvent.change(screen.getByRole('combobox',{name:'Player season'}),{target:{value:'2021'}});expect(change).toHaveBeenCalledWith('2021');
 fireEvent.click(screen.getByRole('tab',{name:'Draft'}));expect(screen.getByText('#13')).toBeTruthy();expect(screen.getByText('Historical Team')).toBeTruthy();
 fireEvent.click(screen.getByRole('tab',{name:'Weekly Log'}));expect(screen.getAllByText('BUF vs. NYJ').length).toBe(2);expect(screen.getAllByText(/BE · 12.00/).length).toBe(2);
 fireEvent.click(screen.getByRole('tab',{name:'Transactions'}));expect(screen.getByText('Waiver add')).toBeTruthy();
});
test('D/ST skips human biography and failed portraits degrade',()=>{
 const defense={...detail,profile:{espnId:-16001,entityType:'team_defense',name:'Falcons D/ST',position:'D/ST',nflTeam:'ATL',logo:'https://example.com/logo.png'}};
 render(<PlayerDetail detail={defense} Section={Section} Team={Team}/>);
 expect(screen.getByText('Pocky Football Team Defense')).toBeTruthy();expect(screen.queryByText('Born')).toBeNull();
 fireEvent.error(screen.getByRole('img',{name:/logo/}));expect(screen.getByLabelText('Image unavailable')).toBeTruthy();
});
test('direct route fetches compact manifest and one player contract, missing ID remains explicit',async()=>{
 const load=vi.fn(p=>Promise.resolve(p==='index'?{players:[{...detail.profile,path:'profiles/7.json'}]}:detail));
 const r=render(<PlayersPage path="index" playerId={7} loadData={load} Section={Section} Team={Team}/>);
 await screen.findByRole('heading',{name:'Example Player'});expect(load.mock.calls.map(c=>c[0])).toEqual(['index','profiles/7.json']);
 r.rerender(<PlayersPage path="index" playerId={999} loadData={load} Section={Section} Team={Team}/>);
 await screen.findByText('Player not found in Pocky Football history.');expect(screen.queryByRole('heading',{name:'Example Player'})).toBeNull();
});
