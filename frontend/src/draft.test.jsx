import React from 'react';
import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import DraftPage, { DraftTable } from './DraftPage.jsx';
afterEach(cleanup);
it('expands every entry and collapses accessibly', () => {
  render(<DraftTable title="Managers" rows={Array.from({length:14},(_,i)=>({managerId:String(i),manager:`Manager ${i}`}))} columns={[["Name", r=>r.manager]]}/>);
  expect(screen.queryByText('Manager 13')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Show all 14'}));
  expect(screen.getByText('Manager 13')).toBeTruthy();
  expect(screen.getByRole('button').getAttribute('aria-expanded')).toBe('true');
  fireEvent.click(screen.getByRole('button'));expect(screen.queryByText('Manager 13')).toBeNull();
});
it('shows loading and a failure state', async () => {
  render(<DraftPage path="draft.json" loadData={()=>Promise.reject(new Error())}/>);
  expect(screen.getByRole('status').textContent).toContain('Loading');
  expect((await screen.findByRole('alert')).textContent).toContain('unavailable');
});
it('withholds incomplete rankings and supports year switching', async () => {
  const changed=[];
  const data={years:[2026,2025,2024,2023,2022,2021],summary:{},seasons:{2026:{performanceEligible:false,teamCount:10,picks:[],completedWeeks:[1,2],weeks:[1,2,3],missingScores:0,teams:[],rounds:[]}}};
  render(<DraftPage path="draft.json" loadData={()=>Promise.resolve(data)} year="2026" onYearChange={y=>changed.push(y)} Team={()=>null}/>);
  await screen.findByText('Provisional season recap.');
  expect(screen.getByLabelText('Draft season').options.length).toBe(7);
  fireEvent.change(screen.getByLabelText('Draft season'),{target:{value:'Summary'}});expect(changed).toEqual(['Summary']);
});
