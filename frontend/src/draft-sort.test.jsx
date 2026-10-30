import React from 'react';
import {afterEach,expect,it} from 'vitest';
import {cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import {sortDraftRows} from './draft-sort.jsx';
import DraftPage,{DraftTable} from './DraftPage.jsx';
import {SummaryTable} from './DraftSummary.jsx';
import data from '../public/data/pocky-football/draft-analysis.json';
afterEach(cleanup);
const Team=({team})=><span>{team.name}</span>;
const Player=({pick})=><span>{pick.playerName}</span>;
const Points=({pick})=><span>{pick.points}</span>;
it('sorts numeric ranks rather than rendered position labels, with null last in both directions and stable ties',()=>{
 const rows=[{playerName:'K12',positionalRank:12,overallPick:2},{playerName:'QB3',positionalRank:3,overallPick:1},
 {playerName:'WR3',positionalRank:3,overallPick:3},{playerName:'Unknown',positionalRank:null,overallPick:4}];
 const before=structuredClone(rows);
 expect(sortDraftRows(rows,['Position finish']).map(p=>p.playerName)).toEqual(['QB3','WR3','K12','Unknown']);
 expect(sortDraftRows(rows,['Position finish'],'descending').map(p=>p.playerName)).toEqual(['K12','QB3','WR3','Unknown']);
 expect(sortDraftRows(rows,['Player']).map(p=>p.playerName)).toEqual(['K12','QB3','Unknown','WR3']);
 expect(rows).toEqual(before);
});
it('sorts all meaningful season columns and preserves Show all state',()=>{
 const rows=[{playerId:1,playerName:'Z',overallPick:12,points:null},{playerId:2,playerName:'A',overallPick:2,points:10},{playerId:3,playerName:'B',overallPick:3,points:2}];
 render(<DraftTable title="Picks" rows={rows} initial={1} columns={[
 ['Player',p=>p.playerName],['Overall pick',p=>p.overallPick],['Season FPTS',p=>p.points??'—']]}/>);
 fireEvent.click(screen.getByRole('button',{name:'Show all 3'}));
 const sort=screen.getByRole('button',{name:'Overall pick'});sort.focus();expect(document.activeElement).toBe(sort);
 fireEvent.click(sort);
 expect(sort.closest('th').getAttribute('aria-sort')).toBe('ascending');
 expect(screen.getAllByRole('row').slice(1).map(r=>r.cells[1].textContent)).toEqual(['2','3','12']);
 fireEvent.click(sort);expect(sort.closest('th').getAttribute('aria-sort')).toBe('descending');
 fireEvent.click(screen.getByRole('button',{name:'Season FPTS'}));
 expect(screen.getAllByRole('row').slice(1).map(r=>r.cells[2].textContent)).toEqual(['2','10','—']);
 fireEvent.click(screen.getByRole('button',{name:'Season FPTS'}));
 expect(screen.getAllByRole('row').slice(1).map(r=>r.cells[2].textContent)).toEqual(['10','2','—']);
});
it('keeps manager expansion when sorting parent rows and sorts underlying picks independently',()=>{
 const rows=['Zoe','Alice'].map((manager,i)=>({managerId:manager,manager,team:{name:manager},averageRoundRank:i+1,evidence:[
 {season:2025,round:1,overallPick:12,playerName:'Second',points:20,roundRank:2},
 {season:2025,round:1,overallPick:2,playerName:'First',points:30,roundRank:1}]}));
 render(<SummaryTable title="Managers" rows={rows} columns={[["Average Round Rank",r=>r.averageRoundRank]]} {...{Team,Player,Points}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Zoe: historical draft picks'}));
 const parent=screen.getByRole('table',{name:'Managers'});
 fireEvent.click(within(parent).getByRole('button',{name:'Manager / team'}));
 const details=screen.getByRole('table',{name:'Zoe picks'});
 fireEvent.click(within(details).getByRole('button',{name:'Overall pick'}));
 expect(within(details).getAllByRole('row').slice(1).map(r=>r.cells[2].textContent)).toEqual(['2','12']);
 expect(screen.getByRole('button',{name:'Zoe: historical draft picks'}).getAttribute('aria-expanded')).toBe('true');
});
for(const year of ['Summary','2025','2026'])it(`every data header has accessible sorting in committed ${year}`,async()=>{
 render(<DraftPage path="draft.json" year={year} Team={Team} loadData={async()=>data}/>);
 await screen.findByLabelText('Draft season');
 const table=screen.getByRole('table',{name:year==='Summary'?'Overall Round Performance':'Overall Performance'});
 fireEvent.click(within(table).getAllByRole('button',{name:/historical draft picks/})[0]);
 for(const header of screen.getAllByRole('columnheader')) {
   expect(header.getAttribute('aria-sort')).toBe('none');
   expect(within(header).getByRole('button')).toBeTruthy();
 }
 if(year==='2026') {
   fireEvent.change(screen.getByRole('searchbox',{name:'Find a draft pick'}),{target:{value:'Breece Hall'}});
   expect(screen.getAllByText(/Qualified by total points/).length).toBeGreaterThan(0);
   expect(screen.getAllByRole('columnheader',{name:'FPPG'}).length).toBeGreaterThan(0);
 }
});
