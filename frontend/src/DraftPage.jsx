import React, { useEffect, useId, useState } from 'react';
import './draft.css';
import { hydrateDraft, seasonPerformanceRows } from './draft-view.js';
import DraftSummary, { SummaryTable } from './DraftSummary.jsx';

const fmt = (v, digits = 1) => v == null ? '—' : Number(v).toFixed(digits);
function Movement({ value, digits = 1 }) {
  return <span className={value > 0 ? 'draft-positive' : value < 0 ? 'draft-negative' : ''}>
    {value > 0 ? '+' : ''}{fmt(value, digits)}
  </span>;
}

export function DraftTable({ title, rows, columns, initial = 5, description, ranked = false, showCount = true }) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  return <section className="home-section draft-section">
    <div className="section-title"><h2>{title}</h2>{showCount && <span>{rows.length} entries</span>}</div>
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

export default function DraftPage({ path, loadData, year = 'Summary', onYearChange, Team }) {
  const [data, setData] = useState(null), [error, setError] = useState(false);
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
  const pickIdentity = [['Player', p => <Player pick={p}/>], ['Fantasy team', teamCell], ['Draft pick', p => p.overallPick]];
  const overallColumns = [...pickIdentity, ['Season FPTS', p => <Points pick={p}/>],
    ['Position finish', p => `${p.position} ${fmt(p.positionalRank)}`], ['Benchmark pick', p => p.benchmarkPick ?? '—'], ['Draft position gain', p => <Movement value={p.draftPositionGain}/>]];
  return <div className="draft-page">
    <label className="select-control">Draft season<select aria-label="Draft season" value={season ? year : 'Summary'}
      onChange={e => onYearChange(e.target.value)}>
      <option value="Summary">Summary</option>{data.years.map(y => <option key={y} value={y}>{y}</option>)}
    </select></label>
    {season ? <>
      {!season.performanceEligible && <p className="archive-note" role="status"><strong>Provisional season recap.</strong> Final ranks and rank movement are withheld. Points cover completed fantasy weeks only.</p>}
      <SummaryTable key={`overall-${year}`} title="Overall Performance" rows={seasonPerformanceRows(season)}
        columns={[["Average Round Rank", row => fmt(row.averageRoundRank)]]} {...{Team, Player, Points}}/>
      <h2 className="draft-group-title">Round-by-round draft results</h2>
      <p className="draft-description">Picks stay in draft order. Value standout = positional draft-slot gain ÷ original overall pick. Best positional finish is recognized separately, including elite early picks with zero gain; ties are shared. FPTS rank remains a points-only comparison.</p>
      {season.rounds.map(round => <details className="draft-panel content-card" key={`${year}/${round.round}`} open={undefined}><summary>Round {round.round} · {round.standouts?.valueLeaders?.map(p => p.playerName).join(" / ") || "Value comparison unavailable"}</summary>
        <RoundStandouts standouts={round.standouts} Team={Team}/>
        <DraftTable title={`Round ${round.round}`} rows={round.picks} initial={3} showCount={false}
          columns={[["FPTS rank", p => fmt(p.roundRank)], ["Overall pick", p => p.overallPick], ["Pick in round", p => p.pickInRound],
            ["Player", p => <Player pick={p}/>], ["Fantasy team", teamCell], ["Season FPTS", p => <Points pick={p}/>],
            ["Position finish", p => `${p.position} ${fmt(p.positionalRank)}`], ["Positional draft-slot gain", p => <Movement value={p.draftPositionGain}/>]]}/>

      </details>)}

      {table('Best draft position gains', season.risers, overallColumns,
        'Gain = actual pick − the original pick of the Nth player drafted at this position, where N is final positional rank. Positive means selected later than the benchmark. Missing benchmarks are excluded; averages would favor survivors.', 10)}
      {table('Largest draft position losses', season.fallers, overallColumns, 'Negative means selected earlier than the positional benchmark. Expand to inspect every available loss.', 10)}
      <DraftBoard key={year} picks={season.picks} columns={overallColumns}/>
    </> : <DraftSummary summary={summary} Team={Team} Player={Player} Points={Points}/>}
    {season && <p className="draft-description">Final ranks include eligible undrafted players and use average ranks for tied FPTS. Missing values display — and never become a manufactured rank. The selected player earns season points regardless of later fantasy ownership.
      {' '}Scoring reconciles normalized weekly totals and actual NFL game records; covered bye/non-participation gaps contribute no points. {data.audit.fixed} of {data.audit.previouslyUnevaluable} previously unresolved completed-season picks were recovered; {data.audit.remaining} remain unresolved.</p>}
  </div>;
}

function RoundStandouts({ standouts, Team }) {
  if (!standouts || standouts.status !== 'available') return <p className="draft-description">
    {standouts?.status === 'provisional' ? 'Standouts await final season results.' : 'Standout comparison unavailable until scoring and positional ranks are complete.'}
  </p>;
  const values = standouts.valueLeaders || [], finishes = standouts.finishLeaders || [];
  const valueIds = new Set(values.map(pick => pick.playerId));
  const additionalFinishes = finishes.filter(pick => !valueIds.has(pick.playerId));
  const finishIds = new Set(finishes.map(pick => pick.playerId));
  const card = (pick, value) => <article key={pick.playerId} className="draft-round-standout">
    <Player pick={pick}/><Team team={pick.team} season={pick.season}/>
    <p>{pick.position}{fmt(pick.positionalRank, Number.isInteger(pick.positionalRank) ? 0 : 1)} · {fmt(pick.points, 2)} FPTS
      {value ? <> · <Movement value={pick.draftPositionGain} digits={0}/> picks vs #{pick.benchmarkPick}
        <small>{fmt(standouts.relativeGainPercent)}% relative gain{finishIds.has(pick.playerId) ? ' · Also best positional finish' : ''}</small></>
        : <small>Drafted {pick.position}{pick.draftPositionRank} → {pick.position}{fmt(pick.positionalRank, Number.isInteger(pick.positionalRank) ? 0 : 1)} · Best finish in round</small>}
    </p>
  </article>;
  return <div className="draft-round-standouts">
    {values.length > 0 && <><h3>Draft value standout{values.length > 1 ? 's' : ''}</h3>{values.map(pick => card(pick, true))}</>}
    {additionalFinishes.length > 0 && <><h3>Best positional finish</h3>{additionalFinishes.map(pick => card(pick, false))}</>}
    {standouts.missingBenchmarks > 0 && <p className="draft-description">Some picks have no exact positional benchmark; their draft-slot value is unavailable.</p>}
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
