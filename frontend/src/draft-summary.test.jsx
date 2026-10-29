import React from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { SummaryTable } from './DraftSummary.jsx';
afterEach(cleanup);
const Team = ({team}) => <span><img src={team.logo} alt=""/>{team.name}</span>;
const Player = ({pick}) => <span>{pick.playerName} · {pick.position}</span>;
const Points = ({pick}) => <span>{pick.points}</span>;
const rows = ['Alice','Bob'].map((manager,i) => ({managerId:manager,manager,team:{name:`Current ${manager}`,logo:`/${manager}.png`,season:2026},
  averageRoundRank:i+1,evidence:[{season:2024,round:2,overallPick:i+10,playerName:`Pick ${manager}`,position:'RB',points:123,roundRank:3}]}));
const columns = [['Average Round Rank',row => row.averageRoundRank]];
it('clicking any row cell toggles inline picks and closes the previous manager', () => {
  render(<SummaryTable title="Overall" {...{rows,columns,Team,Player,Points}}/>);
  const table = screen.getByRole('table',{name:'Overall'});
  const cells = within(table).getAllByRole('cell');
  fireEvent.click(cells[1]);
  expect(screen.getByRole('table',{name:'Alice picks'})).toBeTruthy();
  expect(screen.getByText('Pick Alice · RB')).toBeTruthy();
  const bob = screen.getByRole('button',{name:'Bob: historical draft picks'});
  fireEvent.click(bob);
  expect(screen.queryByRole('table',{name:'Alice picks'})).toBeNull();
  expect(screen.getByRole('table',{name:'Bob picks'})).toBeTruthy();
  expect(bob.getAttribute('aria-expanded')).toBe('true');
  bob.focus(); expect(document.activeElement).toBe(bob);
  expect(document.getElementById(bob.getAttribute('aria-controls'))).toBeTruthy();
  fireEvent.click(bob);
  expect(screen.queryByRole('table',{name:'Bob picks'})).toBeNull();
});
it('each table keeps its own single expanded row and omits entry counts and evidence columns', () => {
  render(<><SummaryTable title="QB" {...{rows,columns,Team,Player,Points}}/><SummaryTable title="RB" {...{rows,columns,Team,Player,Points}}/></>);
  const qb = screen.getByRole('table',{name:'QB'}), rb = screen.getByRole('table',{name:'RB'});
  fireEvent.click(within(qb).getByRole('button',{name:'Alice: historical draft picks'}));
  fireEvent.click(within(rb).getByRole('button',{name:'Bob: historical draft picks'}));
  expect(within(qb).getByRole('table',{name:'Alice picks'})).toBeTruthy();
  expect(within(rb).getByRole('table',{name:'Bob picks'})).toBeTruthy();
  expect(screen.queryByText(/entries/)).toBeNull();
  expect(screen.queryByRole('columnheader',{name:'Underlying Picks'})).toBeNull();
});
