import React from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import DraftPage from './DraftPage.jsx';
import data from '../public/data/pocky-football/draft-analysis.json';
afterEach(cleanup);
const Team = ({team}) => <span>{team.name}</span>;
const loadData = async () => data;

it('uses only manager and average round rank with inline single-manager details', async () => {
  render(<DraftPage path="draft.json" {...{loadData,Team}} year="2025"/>);
  const table = await screen.findByRole('table',{name:'Overall Performance'});
  expect(within(table).getAllByRole('columnheader').map(c=>c.textContent.replace(/ [↕↑↓]$/, ''))).toEqual(['Manager / team','Average Round Rank']);
  const buttons = within(table).getAllByRole('button', {name:/historical draft picks/});
  fireEvent.click(buttons[0]);
  const first = within(table).getByRole('table');
  const rows = within(first).getAllByRole('row');
  expect(rows.length).toBe(17);
  expect(within(first).getByRole('columnheader',{name:/^Round rank/})).toBeTruthy();
  fireEvent.click(buttons[1]);
  expect(within(table).getAllByRole('table')).toHaveLength(1);
  expect(buttons[0].getAttribute('aria-expanded')).toBe('false');
  fireEvent.click(buttons[1]);expect(within(table).queryByRole('table')).toBeNull();
  expect(screen.queryByText(/completed fantasy weeks/)).toBeNull();
  expect(screen.queryByText(/diagnostic/i)).toBeNull();
  expect(screen.queryByRole('columnheader',{name:'Underlying picks'})).toBeNull();
});

it('shows JSN as value standout and Allen/McBride separately, in original Round 3 order', async () => {
  render(<DraftPage path="draft.json" {...{loadData,Team}} year="2025"/>);
  await screen.findByLabelText('Draft season');
  const title = screen.getByText('Round 3 · Jaxon Smith-Njigba',{exact:true});
  fireEvent.click(title);
  const panel = title.closest('details');
  expect(within(panel).getByRole('heading',{name:'Draft value standout'})).toBeTruthy();
  expect(within(panel).getByText(/Greatest positional draft-slot gain/)).toBeTruthy();
  expect(within(panel).getByRole('heading',{name:'Best positional finish'})).toBeTruthy();
  const table = within(panel).getByRole('table',{name:'Round 3'});
  fireEvent.click(within(table.closest('section')).getByRole('button',{name:'Show all 10'}));
  expect(within(table).getAllByRole('row').slice(1).map(r=>within(r).getAllByRole('cell')[1].textContent))
    .toEqual(['21','22','23','24','25','26','27','28','29','30']);
  expect(within(panel).queryByText(/entries/)).toBeNull();
});

it('preserves protected gain/loss/board labels, headers and pick ordering', async () => {
  render(<DraftPage path="draft.json" {...{loadData,Team}} year="2025"/>);
  await screen.findByLabelText('Draft season');
  const headers = ['Player','Fantasy team','Draft pick','Season FPTS','Position finish','Benchmark pick','Draft position gain'];
  for (const label of ['Best draft position gains','Largest draft position losses','Full draft board']) {
    const table = screen.getByRole('table',{name:label});
    expect(within(table).getAllByRole('columnheader').map(c=>c.textContent.replace(/ [↕↑↓]$/, ''))).toEqual(headers);
    const expected = label === 'Full draft board' ? data.seasons['2025'].picks.slice(0,10).map(p=>p.overallPick)
      : data.seasons['2025'][label.startsWith('Best') ? 'risers' : 'fallers'].slice(0,10).map(p=>p.pickRef[1]);
    expect(within(table).getAllByRole('row').slice(1).map(r=>Number(within(r).getAllByRole('cell')[2].textContent))).toEqual(expected);
  }
});

it('renders missing positional benchmarks and provisional standouts safely', async () => {
  const fixture = structuredClone(data);
  const round = fixture.seasons['2025'].rounds[0];
  round.standouts = {status:'available', valueLeaders:[], finishLeaders:round.picks.slice(0,1), relativeGainPercent:null, missingBenchmarks:10};
  const view = render(<DraftPage path="draft.json" loadData={async()=>fixture} Team={Team} year="2025"/>);
  await screen.findByLabelText('Draft season');
  const title = screen.getByText('Round 1 · Value comparison unavailable',{exact:true});
  fireEvent.click(title);
  expect(within(title.closest('details')).getByText(/Partial round comparison/)).toBeTruthy();
  view.rerender(<DraftPage path="draft.json" loadData={loadData} Team={Team} year="2026"/>);
  await screen.findByText('Provisional season recap.');
  expect(screen.queryByText(/diagnostic/i)).toBeNull();
});
