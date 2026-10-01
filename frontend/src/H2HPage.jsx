import React, { useEffect, useState } from 'react';
import { defaultPair, pairFile, otherTeamOptions } from './h2h-view.js';

const record = summary => `${summary.wins} – ${summary.losses} – ${summary.ties}`;
export default function H2HPage({ mode, path, loadData, Team, Section }) {
  const [manifest, setManifest] = useState(null), [first, setFirst] = useState(null), [second, setSecond] = useState(null);
  const [view, setView] = useState(null), [season, setSeason] = useState('Summary'), [error, setError] = useState(null);
  useEffect(() => {
    let active = true;
    loadData(path).then(value => { if (active) { setManifest(value); const ids = defaultPair(value.teams); setFirst(ids[0]); setSecond(ids[1]); } }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [path, loadData]);
  useEffect(() => {
    let active = true; setView(null); setSeason('Summary');
    const file = pairFile(first, second);
    if (manifest && file) {
      setError(null);
      loadData(`${manifest.pairPath}${file}.json`).then(value => { if (active) setView(value[mode][String(first)]); }).catch(e => { if (active) setError(e.message); });
    }
    return () => { active = false; };
  }, [manifest, first, second, mode, loadData]);
  const theoretical = mode === 'theoretical';
  if (error) return <p role="alert">H2H unavailable. {error}</p>;
  if (!manifest) return <p role="status">Loading H2H…</p>;
  const a = manifest.teams.find(team => team.teamId === first), b = manifest.teams.find(team => team.teamId === second);
  const rows = view ? view.rows.filter(row => season === 'Summary' || row.season === Number(season)) : [];
  const summary = view && (season === 'Summary' ? view.summary : view.seasonSummaries[season]);
  return <>
    {theoretical && <p className="h2h-intro">What if these two teams played each other every single week? Compare their finalized regular-season performances from the same actual week.</p>}
    <div className="content-card h2h-selector">{[{label:'Team A',id:first,other:second,set:setFirst,team:a},{label:'Team B',id:second,other:first,set:setSecond,team:b}].map((side,index) => <React.Fragment key={side.label}>{index === 1 && <div className="h2h-versus" aria-hidden="true">VS</div>}<div className="h2h-side"><Team team={side.team}/><label className="select-control">{side.label}<select aria-label={side.label} value={side.id ?? ''} onChange={event => side.set(Number(event.target.value))}>{otherTeamOptions(manifest.teams,side.other).map(team => <option key={team.teamId} value={team.teamId}>{team.name}</option>)}</select></label></div></React.Fragment>)}</div>
    <p className="archive-note">History follows ESPN team IDs within each season. Reused IDs may represent different owners or teams; no permanent franchise mapping is assumed.</p>
    {!view ? <p role="status">Loading comparison…</p> : <>
      {theoretical && <label className="select-control h2h-season">Season<select aria-label="H2H season" value={season} onChange={event => setSeason(event.target.value)}><option value="Summary">Summary</option>{view.seasons.map(year => <option key={year} value={year}>{year}</option>)}</select></label>}
      <Section title={theoretical ? 'Theoretical H2H Record' : 'All-Time H2H Record'} meta={`${summary.total} ${theoretical ? 'comparable weeks' : 'meetings'}`}>
        <div className="content-card h2h-record"><Team team={a}/><div><strong>{record(summary)}</strong><small>Team A wins · Team B wins · Ties</small></div><Team team={b}/></div>
        {!theoretical && <dl className="h2h-splits">{[['Regular Season',view.regularSummary],['Playoffs',view.playoffSummary]].map(([label,value]) => <div key={label}><dt>{label}</dt><dd>{record(value)}</dd></div>)}</dl>}
      </Section>
      <Section title={theoretical ? 'Week-by-Week Results' : 'Matchup History'} meta="Newest first"><div className="content-card h2h-history">
        {!rows.length && <p>{theoretical ? 'These teams do not have any comparable completed weeks.' : 'These teams have no completed meetings.'}</p>}
        {rows.map(row => <div className="h2h-result" key={`${row.season}-${row.week}`}>
          <div className={row.result === 'W' ? 'h2h-winner' : ''}><Team team={row.teamA}/></div>
          <div className="h2h-score"><strong>{row.teamAScore.toFixed(2)} – {row.teamBScore.toFixed(2)}</strong><small>{row.season} · Week {row.week} · {row.isPlayoff ? row.roundLabel || 'Playoffs' : 'Regular season'}</small><span>{row.result === 'T' ? 'Tie' : `${row.result === 'W' ? row.teamA.name : row.teamB.name} wins`}{theoretical && row.actualMeeting ? ' · Actual meeting' : ''}</span></div>
          <div className={row.result === 'L' ? 'h2h-winner' : ''}><Team team={row.teamB}/></div>
        </div>)}
      </div></Section>
    </>}
  </>;
}
