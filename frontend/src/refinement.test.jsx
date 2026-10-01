import React from 'react';
import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { RankedRecord } from './RecordBookPage.jsx';
import RecordBookPage from './RecordBookPage.jsx';
import TeamDraft from './TeamDraft.jsx';

afterEach(cleanup);
const Team=({team})=><span>{team.name}</span>;
const Section=({title,children})=><section><h2>{title}</h2>{children}</section>;
const teams=[{teamId:1,name:'A'},{teamId:2,name:'B'}];
const rows=[1,2,3].map((week,index)=>({rank:index+1,season:2021,week,team:teams[0],opponent:teams[1],value:100-index,
 matchup:{season:2021,week,teamA:teams[0],teamB:teams[1]}}));
const record={id:'team-high',label:'Highest Team Score',unit:'points',holders:[rows[0]],leaders:rows,limit:10,matchupDetails:true};
const detail=week=>({teams:{1:[{playerId:10,name:`QB ${week}`,nflTeam:'BUF',position:'QB',slot:'QB',points:20}],2:[{playerId:12,name:`Other ${week}`,nflTeam:'NYJ',position:'RB',slot:'RB',points:9}]}});

test('ranked expansion has one shared matchup detail and reuses cached lineups',async()=>{
 const loadData=vi.fn(path=>Promise.resolve(detail(Number(path.match(/(\d+)\.json$/)[1]))));
 render(<RankedRecord record={record} Team={Team} Section={Section} manifest={{lineupPath:'pocky-football/'}} loadData={loadData} cache={{current:new Map()}}/>);
 expect(screen.getAllByRole('button').length).toBe(2);
 fireEvent.click(screen.getByRole('button',{name:/View Top 10/}));expect(screen.getAllByRole('button').length).toBe(4);
 fireEvent.click(screen.getByRole('button',{name:/^#1 /}));await screen.findByText('QB 1');expect(screen.getByText('Other 1')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:/^#2 /}));await screen.findByText('QB 2');expect(screen.queryByText('QB 1')).toBeNull();expect(document.querySelectorAll('.h2h-details').length).toBe(1);
 fireEvent.click(screen.getByRole('button',{name:/^#1 /}));await screen.findByText('QB 1');expect(loadData).toHaveBeenCalledTimes(2);
 fireEvent.click(screen.getByRole('button',{name:/Show record holder/}));expect(screen.queryByText('QB 1')).toBeNull();
});

test('player award shows reliable NFL opponent, omitting fantasy slot and matchup control',()=>{
 const holder={...rows[0],playerId:10,name:'Player',position:'RB',nflTeam:'BUF',nflOpponent:'NYJ',slot:'BE'};
 render(<RankedRecord record={{...record,id:'player-high',matchupDetails:false,holders:[holder],leaders:[holder]}} Team={Team} Section={Section}/>);
 expect(screen.getByText('BUF · RB · vs. NYJ')).toBeTruthy();expect(screen.queryByText(/Slot/)).toBeNull();expect(screen.queryByRole('button')).toBeNull();
});

test('Team Draft uses actual team/order/position and replaces selections on season changes',async()=>{
 const data={season:2021,picks:[{teamId:1,round:2,pickInRound:7,overallPick:17,playerName:'Second',position:'WR'},
 {teamId:2,round:1,pickInRound:1,overallPick:1,playerName:'Other',position:'RB'},
 {teamId:1,round:1,pickInRound:4,overallPick:4,playerName:'First',position:'RB'}]};
 const loadData=vi.fn(path=>path==='missing' ? Promise.reject(new Error('Unavailable')) : Promise.resolve(path==='2021' ? data : {season:2022,picks:[{teamId:1,round:1,pickInRound:10,overallPick:10,playerName:'New season',position:'TE'}]}));
 const rendered=render(<TeamDraft season={2021} teamId={1} path="2021" loadData={loadData}/>);
 await screen.findByText('First');const entries=screen.getAllByRole('row');expect(within(entries[1]).getByText('First')).toBeTruthy();expect(within(entries[2]).getByText('#17 overall')).toBeTruthy();expect(screen.queryByText('Other')).toBeNull();
 rendered.rerender(<TeamDraft season={2022} teamId={1} path="2022" loadData={loadData}/>);await screen.findByText('New season');expect(screen.queryByText('First')).toBeNull();expect(screen.getByText('#10 overall')).toBeTruthy();
 rendered.rerender(<TeamDraft season={2022} teamId={1} path="missing" loadData={loadData}/>);await screen.findByText('Draft data is unavailable for this season.');
});

test('Record Book excludes incomplete season options and falls back to All-Time',async()=>{
 const empty={teamRecords:[],playerRecords:[],positionRecords:[],champions:[],negativeStarterWeeks:[],allFantasyTeam:[],mvp:{holders:[]}};
 const data={years:[2025,2024],lineupPath:'pocky-football/',allTime:empty,seasons:{2025:empty,2024:empty}};
 const onYearChange=vi.fn();render(<RecordBookPage path="records" loadData={()=>Promise.resolve(data)} year="2026" onYearChange={onYearChange} Team={Team} Section={Section}/>);
 const selector=await screen.findByRole('combobox',{name:'Record Book season'});
 expect(within(selector).getAllByRole('option').map(o=>o.value)).toEqual(['All-Time','2025','2024']);expect(selector.value).toBe('All-Time');expect(screen.queryByText(/Current-season weekly/)).toBeNull();
 fireEvent.change(selector,{target:{value:'2025'}});expect(onYearChange).toHaveBeenCalledWith('2025');
});
