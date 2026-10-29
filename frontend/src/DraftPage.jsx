import React, { useEffect, useId, useState } from 'react';
import './draft.css';
import { hydrateDraft } from './draft-view.js';
import DraftSummary from './DraftSummary.jsx';

const fmt = (v, digits = 1) => v == null ? '—' : Number(v).toFixed(digits);
function Movement({ value }) {
  return <span className={value > 0 ? 'draft-positive' : value < 0 ? 'draft-negative' : ''}>
    {value > 0 ? '+' : ''}{fmt(value)}
  </span>;
}

export function DraftTable({ title, rows, columns, initial = 5, description, ranked = false }) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  return <section className="home-section draft-section">
    <div className="section-title"><h2>{title}</h2><span>{rows.length} entries</span></div>
    {description && <p className="draft-description">{description}</p>}
    <div className="content-card table-card">
      {rows.length ? <>
        <div className="draft-scroll" id={id}><table aria-label={title}>
          <thead><tr>{columns.map(([label]) => <th key={label} scope="col">{label}</th>)}</tr></thead>
          <tbody>{(expanded ? rows : rows.slice(0, initial)).map((row, i) =>
            <tr key={`${row.managerId || row.playerId}-${row.season || ''}-${row.overallPick || i}`}>
              {columns.map(([label, cell]) => <td key={label}>{cell(row, i)}</td>)}
            </tr>)}</tbody>
        </table></div>
        {rows.length > initial && <button className="draft-expand" type="button" aria-controls={id}
          aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
          {expanded ? `Show ${ranked ? 'Top' : 'first'} ${initial}` : `Show all ${rows.length}`}
        </button>}
      </> : <p className="draft-description">No finalized eligible results for this selection.</p>}
    </div>
  </section>;
}

function Player({ pick }) {
  return <div className="draft-player">
    {pick.headshot && <img src={pick.headshot} width="36" height="36" loading="lazy" alt=""
      onError={e => { e.currentTarget.hidden = true; }}/>}
    <span><a href={`#/players/${pick.playerId}/${pick.season}`}>{pick.playerName}</a>
      <small>{pick.position || 'Unknown'} · {pick.nflTeam || 'NFL team unavailable'}{pick.rookie === true ? ' · Rookie' : ''}</small>
    </span>
  </div>;
}

function Evidence({ row }) {
  const picks = row.evidence || [];
  return <details><summary>View {picks.length} picks</summary><div className="draft-scroll draft-evidence">
    <table aria-label="Supporting draft picks"><thead><tr>{['Season', 'Round / pick', 'Player', 'Fantasy team', 'Season FPTS', 'Position finish', 'FPTS above expectation', 'Draft position gain'].map(c => <th key={c}>{c}</th>)}</tr></thead>
    <tbody>{picks.map(p => <tr key={`${p.season}/${p.overallPick}`}>
      <td>{p.season}</td><td>{p.round} / #{p.overallPick}</td><td><Player pick={p}/></td>
      <td>{p.team?.logo && <img src={p.team.logo} width="28" height="28" alt=""/>}{p.team?.name || 'Team unavailable'}<small>{p.manager}</small></td>
      <td><Points pick={p}/></td><td>{p.position}{fmt(p.positionalRank)}</td>
      <td><Movement value={p.pointsSurplus}/></td><td><Movement value={p.draftPositionGain}/><small>{p.draftPositionGain == null ? p.benchmarkStatus : ''}</small></td>
    </tr>)}</tbody></table>
  </div>{!picks.length && <p className="draft-description">No supporting picks available.</p>}</details>;
}

export default function DraftPage({ path, loadData, year = 'Summary', onYearChange, Team }) {
  const [data, setData] = useState(null), [error, setError] = useState(false);
  const [position, setPosition] = useState('QB');
  useEffect(() => {
    let active = true; setError(false); setData(null);
    loadData(path).then(d => { if (active) setData(hydrateDraft(d)); }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [path, loadData]);
  if (error) return <p role="alert">Draft analysis is unavailable. Reload to try again.</p>;
  if (!data) return <p role="status">Loading draft analysis…</p>;
  const season = data.seasons[year], summary = data.summary;
  const teamCell = r => <div><Team team={r.team} season={r.team.season}/><small>{r.manager}</small></div>;
  const table = (title, rows, columns, description, initial = 5, ranked = true) =>
    <DraftTable key={`${year}-${title}`} {...{ title, rows, columns, description, initial, ranked }}/>;
  const sample = ['Evaluated / drafted', r => `${r.eligiblePicks} / ${r.picks}${r.smallSample ? ' · Small sample' : ''}`];
  const roundColumns = [
    ['Manager / team', teamCell], ['Seasons', r => r.seasons.join(', ')],
    ['Picks with round ranks', r => `${r.roundsEvaluated} / ${r.picks}`],
    ['Avg round rank ↓', r => fmt(r.averageRoundRank)], ['Avg FPTS above expectation', r => <Movement value={r.averageSurplus}/>],
    ['Rounds won', r => r.roundWins], ['Sleepers', r => r.sleepers], ['Picks above expectation %', r => fmt(r.successRate)], ['Underlying picks', r => <Evidence row={r}/>],
  ];
  const positionTeamColumns = [
    ['Manager / team', teamCell], ['Seasons', r => r.seasons.join(', ')], sample,
    ['Avg FPTS above expectation', r => <Movement value={r.averageSurplus}/>],
    ['Picks above expectation %', r => fmt(r.successRate)],
    ['Avg season FPTS', r => fmt(r.averagePoints, 2)], ['Underlying picks', r => <Evidence row={r}/>],
  ];
  const pickIdentity = [['Player', p => <Player pick={p}/>], ['Fantasy team', teamCell], ['Draft pick', p => p.overallPick]];
  const overallColumns = [...pickIdentity, ['Season FPTS', p => <Points pick={p}/>],
    ['Position finish', p => `${p.position} ${fmt(p.positionalRank)}`], ['Benchmark pick', p => p.benchmarkPick ?? '—'], ['Draft position gain', p => <Movement value={p.draftPositionGain}/>]];
  const positionColumns = [...pickIdentity, ['Positional draft order', p => p.draftPositionRank],
    ['Final positional rank', p => fmt(p.positionalRank)], ['Positional movement', p => <Movement value={p.positionalMovement}/>],
    ['Season FPTS', p => <Points pick={p}/>]];
  return <div className="draft-page">
    <label className="select-control">Draft season<select aria-label="Draft season" value={season ? year : 'Summary'}
      onChange={e => onYearChange(e.target.value)}>
      <option value="Summary">Summary</option>{data.years.map(y => <option key={y} value={y}>{y}</option>)}
    </select></label>
    {season ? <>
      {!season.performanceEligible && <p className="archive-note" role="status"><strong>Provisional season recap.</strong> Final ranks and rank movement are withheld. Points cover completed fantasy weeks only.</p>}
      <p className="draft-description">{season.teamCount} teams · {season.picks.length} picks · {season.completedWeeks.length} completed fantasy weeks.
        {' '}{season.missingScores} unresolved scoring totals. Season FPTS use ESPN league scoring through the fantasy season, including playoffs; unused NFL weeks are excluded.</p>
      {table('Team round performance', season.teams, roundColumns,
        'Round wins count tied leaders. Raw round ranks depend on league size; compare samples alongside results.')}
      <h2 className="draft-group-title">Round-by-round draft results</h2>
      <p className="draft-description">Rounds and picks stay in original draft order. Performance rank compares season FPTS within that round; ties receive average ranks. A round with unresolved scoring remains unranked.</p>
      {season.rounds.map(round => <details className="draft-panel content-card" key={`${year}/${round.round}`} open={undefined}><summary>Round {round.round} · {round.leaders?.map(p => p.playerName).join(" / ") || "Results unavailable"}</summary>
        {round.leaders?.length > 0 && <p className="draft-standout"><strong>Round {round.round} standout{round.leaders.length > 1 ? 's' : ''}:</strong>{' '}
          {round.leaders.map(p => `${p.playerName} · ${p.team.name} · ${fmt(p.points, 2)} FPTS`).join(' / ')}
        </p>}
        {table(`Round ${round.round}`, round.picks,
          [['Round rank', p => fmt(p.roundRank)], ['Overall pick', p => p.overallPick], ['Pick in round', p => p.pickInRound],
            ['Player', p => <Player pick={p}/>], ['Fantasy team', teamCell], ['Season FPTS', p => <Points pick={p}/>]],
          null, 3, false)}
      </details>)}

      {table('Best draft position gains', season.risers, overallColumns,
        'Gain = actual pick − the original pick of the Nth player drafted at this position, where N is final positional rank. Positive means selected later than the benchmark. Missing benchmarks are excluded; averages would favor survivors.', 10)}
      {table('Largest draft position losses', season.fallers, overallColumns, 'Negative means selected earlier than the positional benchmark. Expand to inspect every available loss.', 10)}
      <DraftBoard key={year} picks={season.picks} columns={overallColumns}/>
      <details className="draft-panel content-card"><summary>Positional rank movement (diagnostic)</summary>
        <p className="draft-description">Positional draft order − final positional rank, including undrafted players in final ranks. Each position is compared independently.</p>
        <label className="select-control">Position<select aria-label="Draft position" value={position} onChange={e => setPosition(e.target.value)}>
          {Object.keys(season.positions).map(pos => <option key={pos}>{pos}</option>)}
        </select></label>
        {table(`${position} team movement`, season.positions[position]?.teams || [], positionTeamColumns)}
        {table(`${position} picks`, season.positions[position]?.picks || [], positionColumns, 'Original overall draft order.', 10, false)}
      </details>
    </> : <DraftSummary summary={summary} Team={Team} Player={Player} Points={Points}/>}
    {season && <p className="draft-description">Final ranks include eligible undrafted players and use average ranks for tied FPTS. Missing values display — and never become a manufactured rank. The selected player earns season points regardless of later fantasy ownership.
      {' '}Scoring reconciles normalized weekly totals and actual NFL game records; covered bye/non-participation gaps contribute no points. {data.audit.fixed} of {data.audit.previouslyUnevaluable} previously unresolved completed-season picks were recovered; {data.audit.remaining} remain unresolved.</p>}
  </div>;
}

function Points({ pick }) {
  return <span>{fmt(pick.points, 2)}{pick.points == null && <small>Unresolved scoring{pick.missingWeeks?.length ? ` · Weeks ${pick.missingWeeks.map(w => w.week).join(', ')}` : ''}</small>}</span>;
}

function DraftBoard({ picks, columns }) {
  const [query, setQuery] = useState('');
  const match = /^\d+$/.test(query) ? picks.filter(p => p.overallPick === Number(query))
    : picks.filter(p => `${p.playerName} ${p.manager} ${p.team.name} ${p.position}`.toLowerCase().includes(query.toLowerCase()));
  useEffect(() => {
    const update = () => {
      const pick = new URLSearchParams(window.location.hash.split('?')[1]).get('pick');
      if (pick) { setQuery(pick); document.getElementById('draft-board')?.scrollIntoView?.(); }
    };
    update(); window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  return <div id="draft-board">
    <label className="select-control">Find a draft pick<input aria-label="Find a draft pick" type="search" value={query}
      onChange={e => setQuery(e.target.value)} placeholder="Player, manager, position or pick number"/></label>
    <DraftTable title="Full draft board" rows={match} columns={columns} initial={10}
      description="Entire draft in original pick order. Unavailable gains include missing scores, fractional tied ranks, and finishes beyond the drafted positional pool. Zero scores remain real outcomes; incomplete seasons have no final gains."/>
  </div>;
}
