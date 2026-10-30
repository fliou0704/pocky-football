import React from 'react';
import {afterEach,expect,it} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {Team} from './Match.jsx';
import catalog from '../public/data/pocky-football/team-logos.json';
afterEach(cleanup);
it('renders the correct archived current and historical logos even when normalized metadata lacks them',()=>{
 const view=render(<Team team={{teamId:6,name:'Tee Time',logo:null}} season={2024}/>);
 expect(view.container.querySelector('img').getAttribute('src')).toContain(catalog.seasons['2024']['6'].asset);
 view.rerender(<Team team={{teamId:6,name:'LOVE MEEEE',logo:null}} season={2026}/>);
 expect(view.container.querySelector('img').getAttribute('src')).toContain(catalog.seasons['2026']['6'].asset);
 expect(view.container.querySelector('img').dataset.logoProvenance).toBe('exact-espn-season');
});
it('uses an explicit verified alternate for deleted historical uploads',()=>{
 const view=render(<Team team={{teamId:16,name:'CMC',logo:null}} season={2025}/>);
 expect(view.container.querySelector('img').getAttribute('src')).toContain(catalog.seasons['2025']['16'].asset);
 expect(view.container.querySelector('img').dataset.logoProvenance).toBe('same-franchise-fallback');
});
it('has a fixed-size green badge after an image error without a broken image icon',()=>{
 const view=render(<Team team={{teamId:999,name:'Green Bay Example',abbreviation:'GB',logo:'https://example.com/broken.svg'}} season={2026}/>);
 const image=view.container.querySelector('img');expect(image.width).toBe(36);expect(image.height).toBe(36);
 fireEvent.error(image);
 expect(view.container.querySelector('img')).toBeNull();
 expect(screen.getByText('GB').dataset.logoProvenance).toBe('generated-badge');
 expect(screen.getByText('Green Bay Example')).toBeTruthy();
});

it('deduplicates normalized archive references and reaches the badge after one failure',()=>{
 const asset=catalog.seasons['2026']['6'].asset;
 const view=render(<Team team={{teamId:6,name:'LOVE MEEEE',logo:asset}} season={2026}/>);
 fireEvent.error(view.container.querySelector('img'));
 expect(view.container.querySelector('img')).toBeNull();
 expect(view.container.querySelector('[data-logo-provenance="generated-badge"]')).toBeTruthy();
});
