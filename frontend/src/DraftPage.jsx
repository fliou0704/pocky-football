import React, { useEffect, useId, useState } from 'react';
import './draft.css';
import { hydrateDraft } from './draft-view.js';

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
  return <details><summary>View picks</summary><div className="draft-evidence">
    {row.evidence.map(p => <a key={`${p.season}/${p.overallPick}`} href={`#/draft/${p.season}?pick=${p.overallPick}`}>
      {p.season} · #{p.overallPick}
    </a>)}
  </div></details>;
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
    ['Avg round rank ↓', r => fmt(r.averageRoundRank)], ['Normalized round score ↑', r => fmt(r.roundScore)],
    ['Rounds won', r => r.roundWins], ['Underlying picks', r => <Evidence row={r}/>],
  ];
  const positionTeamColumns = [
    ['Manager / team', teamCell], ['Seasons', r => r.seasons.join(', ')], sample,
    ['Avg positional movement', r => <Movement value={r.averageMovement}/>],
    ['Total positional movement', r => <Movement value={r.totalMovement}/>],
    ['Avg season FPTS', r => fmt(r.averagePoints, 2)], ['Underlying picks', r => <Evidence row={r}/>],
  ];
  const pickIdentity = [['Player', p => <Player pick={p}/>], ['Fantasy team', teamCell], ['Draft pick', p => p.overallPick]];
  const overallColumns = [...pickIdentity, ['Season FPTS', p => <Points pick={p}/>],
    ['Final overall rank', p => fmt(p.overallRank)], ['Overall movement', p => <Movement value={p.overallMovement}/>]];
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
        'Ordered by normalized round score: 100 × (picks in round − rank) ÷ (picks in round − 1). Higher is better; average raw rank is lower-is-better. Tied highest scores share a round win.')}
      <h2 className="draft-group-title">Round-by-round rankings</h2>
      <p className="draft-description">Rounds and picks stay in original draft order. Performance rank compares season FPTS within that round; ties receive average ranks. A round with unresolved scoring remains unranked.</p>
      {season.rounds.map(round => <div key={`${year}/${round.round}`}>
        {round.leaders?.length > 0 && <p className="draft-standout"><strong>Round {round.round} standout{round.leaders.length > 1 ? 's' : ''}:</strong>{' '}
          {round.leaders.map(p => `${p.playerName} · ${p.team.name} · ${fmt(p.points, 2)} FPTS`).join(' / ')}
        </p>}
        {table(`Round ${round.round}`, round.picks,
          [['Round rank', p => fmt(p.roundRank)], ['Overall pick', p => p.overallPick], ['Pick in round', p => p.pickInRound],
            ['Player', p => <Player pick={p}/>], ['Fantasy team', teamCell], ['Season FPTS', p => <Points pick={p}/>]],
          null, 3, false)}
      </div>)}
      <DraftBoard key={year} picks={season.picks} columns={overallColumns}/>
      {table('Top 10 Risers', season.risers, overallColumns,
        'Overall rank movement = original overall draft pick − final overall fantasy-point rank. Descriptive only: positions have different scoring distributions.', 10)}
      {table('Top 10 Fallers', season.fallers, overallColumns, 'Negative movement means finishing below original draft position. Expand for every eligible faller.', 10)}
      <details className="draft-panel content-card"><summary>Positional rank movement</summary>
        <p className="draft-description">Positional draft order − final positional rank, including undrafted players in final ranks. Each position is compared independently.</p>
        <label className="select-control">Position<select aria-label="Draft position" value={position} onChange={e => setPosition(e.target.value)}>
          {Object.keys(season.positions).map(pos => <option key={pos}>{pos}</option>)}
        </select></label>
        {table(`${position} team movement`, season.positions[position].teams, positionTeamColumns)}
        {table(`${position} picks`, season.positions[position].picks, positionColumns, 'Original overall draft order.', 10, false)}
      </details>
    </> : <>
      <p className="draft-description">Only managers active in {summary.activeSeason}. Historical performance includes completed seasons {summary.seasons.join(', ')}.
        {' '}Overall comparisons use normalized within-round results; positional movement is kept separate for QB, RB, WR, TE, K and D/ST.</p>
      {table('Overall round performance', summary.teams, roundColumns,
        'Higher normalized round score is better across different league sizes. Round wins count tied leaders. Check evaluated samples; no combined positional score is used.')}
      <h2 className="draft-group-title">Positional drafting performance</h2>
      <p className="draft-description">Movement = positional draft order − final positional rank among all eligible players, including undrafted players. Positive means outperforming draft order. Ordered by average movement per pick; totals and sample sizes are context.</p>
      {Object.entries(summary.positions).map(([pos, rows]) => table(`${pos} drafting`, rows, positionTeamColumns))}
      <details className="draft-panel content-card"><summary>Positional draft tendencies</summary>
        <p className="draft-description">First-pick timing counts each manager-season once. Normalized pick = 1 + (overall pick − 1) ÷ team count.</p>
        {Object.entries(summary.tendencies).map(([pos, rows]) => table(`${pos} draft tendencies`, rows,
          [['Manager / team', teamCell], ['Seasons', r => r.seasons.join(', ')], ['Picks', r => r.picks],
            ['Avg round', r => fmt(r.averageRound)], ['Normalized pick', r => fmt(r.normalizedPick)],
            ['Typical first round', r => fmt(r.firstRound)], ['Avg first round', r => fmt(r.averageFirstRound)],
            ['Pick share %', r => fmt(r.share)], ['First picks', r => <Evidence row={r}/>]], null, 5))}
      </details>
      <details className="draft-panel content-card"><summary>Rookie analysis</summary>
        <p className="draft-description">{summary.rookies.count} rookie picks by active managers; {summary.rookies.unknownPicks} player picks have unknown rookie status. Classification uses NFL rookie-season metadata, never missing NFL draft metadata. Movement is compared separately within each position.</p>
        {table('Rookie selections by manager', summary.rookies.teams, [
          ['Manager / team', teamCell], ['Seasons', r => r.seasons.join(', ')], ['Rookie picks', r => r.picks],
          ['Rookie share %', r => fmt(r.rookieShare)], ['Avg rookie round', r => fmt(r.averageDraftRound)],
          ['Normalized pick', r => fmt(r.averageNormalizedPick)], ['Underlying picks', r => <Evidence row={r}/>],
        ], 'Managers shown in normalized round-performance order; counts and share describe selection frequency.')}
        {Object.entries(summary.rookies.positions).filter(([, rows]) => rows.length).map(([pos, rows]) =>
          table(`${pos} rookie movement`, rows, positionTeamColumns))}
      </details>
      <details className="draft-panel content-card"><summary>Historical round patterns</summary>
        {Object.entries(summary.trends).map(([title, rows]) => table(title, rows, roundColumns))}
      </details>
    </>}
    <p className="draft-description">Final ranks include eligible undrafted players and use average ranks for tied FPTS. Missing values display — and never become a manufactured rank. The selected player earns season points regardless of later fantasy ownership.
      {' '}Scoring reconciles normalized weekly totals and actual NFL game records; covered bye/non-participation gaps contribute no points. {data.audit.fixed} of {data.audit.previouslyUnevaluable} previously unresolved completed-season picks were recovered; {data.audit.remaining} remain unresolved.</p>
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
    <DraftTable title="Overall rank movement" rows={match} columns={columns} initial={10}
      description="Entire draft in original pick order. Movement = original overall pick − final overall fantasy rank, including eligible undrafted players. This describes rank movement, not equal value across positions."/>
  </div>;
}
