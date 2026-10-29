import React from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import DraftPage from './DraftPage.jsx';
import committed from '../public/data/pocky-football/draft-analysis.json';

afterEach(cleanup);
const Team = ({team}) => <span>{team.name}</span>;

// Reproduce the exact incompatible shape: valid pre-#18 snapshots contain season
// `teams` and canonical picks but no newly added `overallPerformance` array.
for (const missing of [true, false]) {
  for (const year of ['2021','2022','2023','2024','2025','2026']) {
    it(`renders ${year} actual manager statistics and picks with ${missing ? 'pre-#18' : 'current'} JSON`, async () => {
      const snapshot = structuredClone(committed);
      const season = snapshot.seasons[year];
      if (missing) delete season.overallPerformance;
      render(<DraftPage path="draft.json" year={year} Team={Team} loadData={async()=>snapshot}/>);
      const table = await screen.findByRole('table',{name:'Overall Performance'});
      expect(screen.queryByText('No eligible historical selections.')).toBeNull();
      const expand = within(table.closest('section')).queryByRole('button',{name:'Show all managers'});
      if (expand) fireEvent.click(expand);
      const rows = within(table).getAllByRole('row').slice(1);
      expect(rows.length).toBe(season.teams.length);
      expect(rows.length).toBeGreaterThan(0);
      const ranks = rows.map(row => within(row).getAllByRole('cell')[1].textContent);
      if (year !== '2026') {
        expect(ranks.every(rank => rank !== '—')).toBe(true);
        expect(ranks.map(Number)).toEqual(ranks.map(Number).sort((a,b)=>a-b));
      } else expect(ranks.every(rank => rank === '—')).toBe(true);
      const button = within(table).getAllByRole('button')[0];
      const manager = button.getAttribute('aria-label').replace(': historical draft picks','');
      const expected = season.picks.filter(p=>p.manager === manager);
      expect(expected.length).toBeGreaterThan(0);
      if (year !== '2026') {
        const mean = expected.reduce((sum,p)=>sum+p.roundRank,0)/expected.length;
        expect(Number(ranks[0])).toBeCloseTo(mean,0);
      }
      fireEvent.click(button);
      const picks = within(table).getByRole('table',{name:`${manager} picks`});
      const details = within(picks).getAllByRole('row').slice(1);
      expect(details.length).toBe(expected.length);
      expect(details.map(row=>Number(within(row).getAllByRole('cell')[2].textContent)))
        .toEqual(expected.map(p=>p.overallPick));
      expect(details.every(row=>within(row).getAllByRole('cell')[0].textContent === year)).toBe(true);
      fireEvent.click(button);
      expect(within(table).queryByRole('table')).toBeNull();
    });
  }
}
