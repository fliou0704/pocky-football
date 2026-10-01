import React, { useEffect, useRef, useState } from 'react';
import { pairFile, otherTeamOptions, recordText, recordCaption, nextExpanded, loadedView } from './h2h-view.js';
import { orderedRoster } from './team-view.js';

function MatchupDetails({ row, manifest, loadData, cache, Team }) {
  const [detail, setDetail] = useState(null), [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    const path = `${manifest.lineupPath}${row.season}/lineups/${row.week}.json`;
    if (!cache.current.has(path)) cache.current.set(path, loadData(path));
    cache.current.get(path).then(value => { if (active) setDetail(value); }).catch(() => { cache.current.delete(path); if (active) setError(true); });
    return () => { active = false; };
  }, [row.season, row.week, manifest.lineupPath, loadData, cache]);
  if (error) return <p className="h2h-detail-message" role="status">Matchup lineup detail is unavailable.</p>;
  if (!detail) return <p className="h2h-detail-message" role="status">Loading weekly lineups…</p>;
  return <div className="h2h-lineups">{[row.teamA, row.teamB].map(team => {
    const players = detail.teams?.[String(team.teamId)];
    return <section key={team.teamId} className="h2h-lineup" aria-label={`${team.name} weekly lineup`}><header><Team team={team}/></header>
      {!Array.isArray(players) || !players.length ? <p>No lineup data for this team.</p> : <ul>{orderedRoster(players).map((player,index) => <li key={`${player.playerId}-${index}`}><span className="lineup-slot">{player.displaySlot}</span><div><strong>{player.name}</strong><small>{player.nflTeam} · {player.position}</small></div><strong>{player.points == null ? '—' : player.points.toFixed(2)}</strong></li>)}</ul>}
    </section>;
  })}</div>;
}

export default function H2HPage({ mode, path, loadData, Team, Section, selectedFirst, selectedSecond, onPairChange }) {
  const [manifest, setManifest] = useState(null), [loaded, setLoaded] = useState(null);
  const [season, setSeason] = useState('Summary'), [expanded, setExpanded] = useState(null), [error, setError] = useState(null);
  const cache = useRef(new Map());
  useEffect(() => {
    let active = true;
    loadData(path).then(value => { if (active) setManifest(value); }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [path, loadData]);
  const first = manifest?.teams.some(t => t.teamId === selectedFirst) ? selectedFirst : null;
  const second = manifest?.teams.some(t => t.teamId === selectedSecond) && selectedSecond !== first ? selectedSecond : null;
  const file = pairFile(first, second), key = `${mode}/${first}/${second}`;
  useEffect(() => {
    let active = true; setSeason('Summary'); setExpanded(null); setError(null);
    if (manifest && file) loadData(`${manifest.pairPath}${file}.json`).then(value => {
      const data = value[mode]?.[String(first)];
      if (!data?.summary || !Array.isArray(data.rows)) throw new Error('Comparison data is unavailable');
      if (active) setLoaded({key, data});
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [manifest, file, first, mode, key, loadData]);
  const theoretical = mode === 'theoretical', view = loadedView(loaded, key);
  if (!manifest) return error ? <p role="alert">H2H unavailable. {error}</p> : <p role="status">Loading H2H…</p>;
  const a = manifest.teams.find(team => team.teamId === first), b = manifest.teams.find(team => team.teamId === second);
  const validSeason = theoretical && view?.seasonSummaries?.[season] ? season : 'Summary';
  const rows = view ? view.rows.filter(row => validSeason === 'Summary' || row.season === Number(validSeason)) : [];
  const summary = view && (validSeason === 'Summary' ? view.summary : view.seasonSummaries[validSeason]);
  return <>
    {theoretical && <p className="h2h-intro">What if these two teams played each other every single week? Compare their finalized regular-season performances from the same actual week.</p>}
    <div className="content-card h2h-selector">{[{label:'Team A',id:first,other:second,team:a},{label:'Team B',id:second,other:first,team:b}].map((side,index) => <React.Fragment key={side.label}>{index === 1 && <div className="h2h-versus" aria-hidden="true">VS</div>}<div className="h2h-side">{side.team ? <Team key={side.id} team={side.team}/> : <strong>{side.label}</strong>}<label className="select-control">{side.label}<select aria-label={side.label} value={side.id ?? ''} onChange={event => { const id = event.target.value ? Number(event.target.value) : null; onPairChange(index === 0 ? id : first, index === 1 ? id : second); }}><option value="">Choose a team</option>{otherTeamOptions(manifest.teams,side.other).map(team => <option key={team.teamId} value={team.teamId}>{team.name}</option>)}</select></label></div></React.Fragment>)}</div>
    {!file ? <p className="h2h-selection-prompt">Choose two teams to begin.</p> : error ? <p role="alert">H2H unavailable. {error}</p> : !view ? <p role="status">Loading comparison…</p> : <>
      {theoretical && <label className="select-control h2h-season">Season<select aria-label="H2H season" value={validSeason} onChange={event => { setSeason(event.target.value); setExpanded(null); }}><option value="Summary">Summary</option>{view.seasons.map(year => <option key={year} value={year}>{year}</option>)}</select></label>}
      <Section title={theoretical ? 'Theoretical H2H Record' : 'All-Time H2H Record'} meta={`${summary.total} ${theoretical ? 'comparable weeks' : 'meetings'}`}>
        <div className="content-card h2h-record"><Team key={first} team={a}/><div><strong>{recordText(summary)}</strong><small>{recordCaption(summary)}</small></div><Team key={second} team={b}/></div>
        {!theoretical && <dl className="h2h-splits">{[['Regular Season',view.regularSummary],['Playoffs',view.playoffSummary]].map(([label,value]) => <div key={label}><dt>{label}</dt><dd>{recordText(value)}</dd></div>)}</dl>}
      </Section>
      <Section title={theoretical ? 'Week-by-Week Results' : 'Matchup History'}><div className="content-card h2h-history">
        {!rows.length && <p>{theoretical ? 'These teams do not have any comparable completed weeks.' : 'These teams have no completed meetings.'}</p>}
        {rows.map(row => { const id = `${key}/${row.season}-${row.week}`, open = expanded === id; return <div className="h2h-entry" key={id}>
          <button type="button" className="h2h-result" aria-expanded={open} aria-controls={`detail-${row.season}-${row.week}`} onClick={() => setExpanded(nextExpanded(expanded,id))}>
            <div className={row.result === 'W' ? 'h2h-winner' : ''}><Team team={row.teamA}/></div>
            <div className="h2h-score"><strong>{row.teamAScore.toFixed(2)} – {row.teamBScore.toFixed(2)}</strong><small>{row.season} · Week {row.week} · {row.isPlayoff ? row.roundLabel || 'Playoffs' : 'Regular season'}</small>{theoretical && row.actualMeeting && <span>Actual meeting</span>}</div>
            <div className={row.result === 'L' ? 'h2h-winner' : ''}><Team team={row.teamB}/></div>
          </button>
          {open && <div id={`detail-${row.season}-${row.week}`} className="h2h-details"><MatchupDetails row={row} manifest={manifest} loadData={loadData} cache={cache} Team={Team}/></div>}
        </div>; })}
      </div></Section>
    </>}
  </>;
}
