import React from 'react';
import { readFileSync } from 'node:fs';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { App } from './main.jsx';
import { BrandingSeason, Team, TeamLogoCatalog } from './Match.jsx';
import configuration from './team-branding.json' with { type: 'json' };

afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.location.hash = ''; delete configuration.teams['11']; });
it('shares the branding context and override / automatic / initial fallback across components', () => {
  configuration.teams['11'] = [{ startSeason: 2021, endSeason: 2025, logoOverride: 'team-logos/historical.png' },
    { startSeason: 2026, logoOverride: 'team-logos/current.png' }];
  const view = render(<TeamLogoCatalog.Provider value={{}}><BrandingSeason.Provider value={2021}><Team team={{teamId:11,name:'Team',logo:'https://example.com/automatic.png'}}/></BrandingSeason.Provider></TeamLogoCatalog.Provider>);
  expect(view.container.querySelector('img').src).toContain('historical.png');
  fireEvent.error(view.container.querySelector('img'));
  expect(view.container.querySelector('img').src).toContain('automatic.png');
  fireEvent.error(view.container.querySelector('img'));
  expect(view.container.querySelector('.team-logo-fallback')).toBeTruthy();
  view.rerender(<TeamLogoCatalog.Provider value={{}}><BrandingSeason.Provider value={2021}><Team season={2026} team={{teamId:11,name:'Team',logo:'https://example.com/automatic.png'}}/></BrandingSeason.Provider></TeamLogoCatalog.Provider>);
  expect(view.container.querySelector('img').src).toContain('current.png');
});
for (const [route,heading] of [['#/', '2026 Season'], ['#/scoreboard/2021','Scoreboard'], ['#/teams/2026/1','Teams'], ['#/draft','Draft']]) {
  it(`renders integrated ${route} from existing snapshots`, async () => {
    vi.stubGlobal('fetch', vi.fn(async url => ({ok:true,json:async()=>JSON.parse(readFileSync(`${process.cwd()}/public/data/${String(url).split('data/')[1]}`,'utf8'))})));
    window.location.hash = route; render(<App/>);
    await screen.findByRole('heading',{name:heading,exact:true});
    if (heading === 'Scoreboard') expect(await screen.findByRole('heading',{name:'Team of the Week'})).toBeTruthy();
    if (heading === 'Draft') expect(await screen.findByLabelText('Draft season')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });
}
