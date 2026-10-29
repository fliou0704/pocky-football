import React from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import DraftPage, { DraftTable } from './DraftPage.jsx';
afterEach(() => { cleanup(); window.location.hash = ''; });

const team = { teamId: 1, name: 'Original Team', season: 2025, logo: '/logo.png' };
const pick = (n, rank) => ({ playerId: n, playerName: `Player ${n}`, season: 2025, team, manager: 'Alice', managerId: 'alice',
  position: 'RB', overallPick: n, pickInRound: n, round: 1, roundRank: rank, points: 100-n,
  overallRank: n+1, overallMovement: -1, draftPositionRank: n, positionalRank: n+1, positionalMovement: -1 });
const Team = ({ team }) => <span><img src={team.logo} alt=""/>{team.name}</span>;
const audit = { fixed: 43, previouslyUnevaluable: 43, remaining: 0 };
const loadSeason = (complete = true) => {
  const picks = [pick(1, 2), pick(2, 1), pick(3, 3), pick(4, 4)];
  return { years: [2026, 2025, 2024, 2023, 2022, 2021], audit, summary: {}, seasons: {
    2025: { performanceEligible: complete, teamCount: 10, picks, completedWeeks: [1, 2], weeks: [1, 2, 3], missingScores: 0,
      teams: [], risers: [], fallers: picks, rounds: [{ round: 1, picks, leaders: [picks[1]] }],
      positions: { RB: { teams: [], picks }, QB: { teams: [], picks: [] } } },
  } };
};
it('expands every entry and collapses accessibly without implying draft order is a top ranking', () => {
  render(<DraftTable title="Managers" rows={Array.from({ length: 14 }, (_, i) => ({ managerId: String(i), manager: `Manager ${i}` }))}
    columns={[["Name", r => r.manager]]}/>);
  expect(screen.queryByText('Manager 13')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Show all 14' }));
  expect(screen.getByText('Manager 13')).toBeTruthy();
  expect(screen.getByRole('button').getAttribute('aria-expanded')).toBe('true');
  fireEvent.click(screen.getByRole('button', { name: 'Show first 5' }));
  expect(screen.queryByText('Manager 13')).toBeNull();
});
it('shows loading and failure states', async () => {
  render(<DraftPage path="draft.json" loadData={() => Promise.reject(new Error())}/>);
  expect(screen.getByRole('status').textContent).toContain('Loading');
  expect((await screen.findByRole('alert')).textContent).toContain('unavailable');
});
it('keeps picks in original round and overall order and expands the whole round', async () => {
  render(<DraftPage path="draft.json" loadData={() => Promise.resolve(loadSeason())} year="2025" Team={Team}/>);
  const round = await screen.findByRole('table', { name: 'Round 1', exact: true });
  let rows = within(round).getAllByRole('row');
  expect(rows.slice(1).map(r => within(r).getAllByRole('cell')[1].textContent)).toEqual(['1', '2', '3']);
  expect(within(rows[1]).getAllByRole('cell')[0].textContent).toBe('2.0');
  const section = round.closest('section');
  fireEvent.click(within(section).getByRole('button', { name: 'Show all 4' }));
  expect(within(round).getAllByRole('row')).toHaveLength(5);
  const board = screen.getByRole('table', { name: 'Full draft board' });
  expect(within(board).getAllByRole('row').slice(1).map(r => within(r).getAllByRole('cell')[2].textContent)).toEqual(['1', '2', '3', '4']);
  expect(screen.queryByText('How draft analysis works')).toBeNull();
  expect(screen.queryByText('Who makes their picks count?')).toBeNull();
  expect(screen.queryByText(/draft value/i)).toBeNull();
  expect(board.querySelectorAll('img')).toHaveLength(4);
});
it('withholds incomplete rankings and supports year switching', async () => {
  const changed = [];
  render(<DraftPage path="draft.json" loadData={() => Promise.resolve(loadSeason(false))} year="2025"
    onYearChange={y => changed.push(y)} Team={Team}/>);
  await screen.findByText('Provisional season recap.');
  expect(screen.getByLabelText('Draft season').options.length).toBe(7);
  fireEvent.change(screen.getByLabelText('Draft season'), { target: { value: 'Summary' } });
  expect(changed).toEqual(['Summary']);
});
it('renders active-only Summary contracts with separate position movement', async () => {
  const data = loadSeason();
  data.summary = { activeSeason: 2026, seasons: [2025], teams: [], positions: { RB: [] }, tendencies: {},
    rookies: { count: 0, unknownPicks: 0, teams: [], positions: {} }, trends: {} };
  render(<DraftPage path="draft.json" loadData={() => Promise.resolve(data)} Team={Team}/>);
  expect(await screen.findByText('Summary only includes current managers')).toBeTruthy();
  expect(screen.getByRole('heading', { name: 'RB drafting' })).toBeTruthy();
  expect(screen.queryByText(/draft value/i)).toBeNull();
});
it('shows complete pick evidence inline with logos and unavailable values', async () => {
  const data = loadSeason();
  const evidence = [pick(1, 1), pick(2, 2)];
  data.summary = { activeSeason: 2026, seasons: [2025], teams: [{ managerId: 'alice', manager: 'Alice', team,
    seasons: [2025], picks: 2, evidence }], positions: {}, tendencies: {},
    rookies: { count: 0, unknownPicks: 0, teams: [], positions: {} }, trends: {} };
  render(<DraftPage path="draft.json" loadData={() => Promise.resolve(data)} Team={Team}/>);
  const managerButton = await screen.findByRole('button', { name: 'Alice: historical draft picks' });
  fireEvent.click(managerButton);
  const table = screen.getByRole('table', { name: 'Alice picks' });
  expect(within(table).getAllByRole('row')).toHaveLength(3);
  expect(within(table).getByText('Player 1')).toBeTruthy();
  expect(screen.getByText('Original Team')).toBeTruthy();
  expect(within(table).getByText('Round rank')).toBeTruthy();
});

import committedDraft from '../public/data/pocky-football/draft-analysis.json';
for (const year of ['Summary', '2021', '2022', '2023', '2024', '2025', '2026']) {
  it(`renders committed Draft ${year} and expands actual evidence without runtime errors`, async () => {
    const errors = [];
    const capture = event => errors.push(event.error);
    window.addEventListener('error', capture);
    try {
      const changed = [];
      render(<DraftPage path="draft-analysis.json" loadData={() => Promise.resolve(committedDraft)}
        year={year} Team={Team} onYearChange={value => changed.push(value)}/>);
      await screen.findByLabelText('Draft season');
      expect(screen.getByRole('heading', { name: year === 'Summary' ? 'Overall Round Performance' : 'Overall Performance' })).toBeTruthy();
      let evidence;
      const managerTable = screen.getByRole('table', { name: year === 'Summary' ? 'Overall Round Performance' : 'Overall Performance' });
      fireEvent.click(within(managerTable).getAllByRole('button')[0]);
      evidence = within(managerTable).getByRole('table');
      expect(within(evidence).getAllByRole('row').length).toBeGreaterThan(1);
      expect(evidence.querySelector('.draft-player')).toBeTruthy();
      fireEvent.change(screen.getByLabelText('Draft season'), { target: { value: year === '2025' ? '2026' : '2025' } });
      expect(changed).toEqual([year === '2025' ? '2026' : '2025']);
      if (year === '2026') expect(screen.getByText('Provisional season recap.')).toBeTruthy();
      expect(errors).toEqual([]);
    } finally { window.removeEventListener('error', capture); }
  });
}
