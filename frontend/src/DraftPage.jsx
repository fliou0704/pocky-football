import React, { useEffect, useState } from 'react';
import './draft.css';
import { hydrateDraft } from './draft-view.js';

const fmt = (v, digits = 1) => v == null ? '—' : Number(v).toFixed(digits);
function Value({ value }) { return <span className={value > 0 ? 'draft-positive' : value < 0 ? 'draft-negative' : ''}>{value > 0 ? '+' : ''}{fmt(value)}</span>; }

export function DraftTable({ title, rows, columns, initial = 5, description }) {
  const [expanded, setExpanded] = useState(false);
  return <section className="home-section draft-section"><div className="section-title"><h2>{title}</h2><span>{rows.length} entries</span></div>
    {description && <p className="draft-description">{description}</p>}<div className="content-card table-card">
      {rows.length ? <><div className="draft-scroll"><table><thead><tr>{columns.map(c => <th key={c[0]} scope="col">{c[0]}</th>)}</tr></thead><tbody>{(expanded ? rows : rows.slice(0, initial)).map((row, i) => <tr key={`${row.managerId || row.playerId}-${row.season || ''}-${row.overallPick || i}`}>{columns.map(c => <td key={c[0]}>{c[1](row, i)}</td>)}</tr>)}</tbody></table></div>
      {rows.length > initial && <button className="draft-expand" type="button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? `Show Top ${initial}` : `Show all ${rows.length}`}</button>}</> : <p className="draft-description">No eligible results for this selection.</p>}
    </div></section>;
}
function Player({ pick }) {
  return <div className="draft-player">{pick.headshot && <img src={pick.headshot} width="36" height="36" loading="lazy" alt="" onError={e => { e.currentTarget.hidden = true; }}/>}<span><a href={`#/players/${pick.playerId}/${pick.season}`}>{pick.playerName}</a><small>{pick.position || 'Unknown'} · {pick.nflTeam || 'NFL team unavailable'}{pick.rookie === true ? ' · Rookie' : ''}</small></span></div>;
}
function Methodology() {
  return <details className="content-card draft-method"><summary>How draft analysis works</summary>
    <p><strong>Draft value = 100 × (positional draft order − positional finish among drafted players) ÷ (eligible drafted players at that position − 1).</strong> +25 means gaining a quarter of the positional draft pool. Both orders use the same players with complete scoring coverage. This is a retrospective ordinal measure, not points over replacement or an ADP forecast.</p>
    <p>Season points sum ESPN league-scored actual weekly totals for the league’s configured fantasy weeks, including fantasy playoffs and consolation. Unused NFL weeks are excluded. The player originally drafted earns those points regardless of trades, drops, benching, or starting lineup. Missing scores are never silently replaced by zero: explicit non-participation and schedule-proven byes are allowed; unresolved players are excluded. Real zero and negative scores count.</p>
    <p>Overall and positional final ranks include all players with complete scoring coverage, including undrafted players. The primary value compares drafted players only, so undrafted breakouts appear in final ranks but cannot earn a manager draft credit. Raw overall gain is overall pick minus overall finish; it is secondary because it favors high-scoring positions. Positional gain compares positional draft and finish orders within the eligible drafted cohort.</p>
    <p>Ties receive average ranks. Round score = 100 × (picks in round − round rank) ÷ (picks in round − 1). A round is ranked only when every pick has known points. All tied leaders count as round winners; top-three includes ties at the third-place score. Team averages use eligible picks; totals are volume-sensitive context and do not determine the primary ordering. High value means +25 or more. Success means positive value; consistency is the standard deviation of season-average values (lower is steadier).</p>
    <p>Summary includes completed seasons with complete authoritative boards and conflict-free scoring sources. Incomplete seasons show completed-week points only; final ranks and value are withheld. Source coverage can still omit players, and final ranks describe the covered player pool. Each leaderboard shows sample sizes; fewer than ten evaluated picks or two seasons is marked as a small sample.</p>
    <p>Managers use an explicit season/team membership map checked against the recorded owner name. Unmapped or changed owners remain season-specific. Rookie status uses matched NFL rookie-season metadata, including undrafted NFL rookies; missing metadata stays unknown. D/ST is not classified as rookie. Rookie controls compare non-rookies at the same position, season, and four-round draft band, with at least three controls. Differences are descriptive, not causal.</p>
  </details>;
}
export default function DraftPage({ path, loadData, year = 'Summary', onYearChange, Team }) {
  const [data, setData] = useState(null), [error, setError] = useState(false), [round, setRound] = useState('1');
  useEffect(() => { let active = true; setError(false); setData(null); loadData(path).then(d => { if (active) setData(hydrateDraft(d)); }).catch(() => { if (active) setError(true); }); return () => { active = false; }; }, [path, loadData]);
  if (error) return <p role="alert">Draft analysis is unavailable. Reload to try again.</p>;
  if (!data) return <p role="status">Loading draft analysis…</p>;
  const season = data.seasons[year], summary = data.summary, view = season || summary;
  const teamCell = p => <div><Team team={p.team} season={p.team.season}/><small>{p.manager}</small></div>;
  const evidence = r => <details><summary>View picks</summary><div className="draft-evidence">{r.evidence.map((p, i) => <a key={i} href={`#/draft/${p.season}?pick=${p.overallPick}`}>{p.season} · #{p.overallPick}</a>)}</div></details>;
  const teamColumns = [['Manager / team', teamCell], ['Seasons', r => r.seasons.join(', ')], ['Picks evaluated / drafted', r => `${r.eligiblePicks} / ${r.picks}${r.smallSample ? ' · Small sample' : ''}`], ['Avg value', r => <Value value={r.averageValue}/>], ['Total value', r => <Value value={r.totalValue}/>], ['Avg round rank', r => fmt(r.averageRoundRank)], ['Round score / 100', r => fmt(r.roundScore)], ['Rounds won', r => r.roundWins], ['Top-three rounds', r => r.topThree], ['High-value picks', r => r.highValue], ['Success %', r => fmt(r.successRate)], ['Season spread ↓', r => fmt(r.seasonSpread)], ['Underlying picks', evidence]];
  const pickColumns = [['Player', p => <Player pick={p}/>], ['Manager / team', teamCell], ['Season', p => p.season], ['Pick', p => `#${p.overallPick} · R${p.round}.${p.pickInRound}`], ['Season FPTS', p => fmt(p.points, 2)], ['Final positional rank', p => fmt(p.positionalRank)], ['Draft value', p => <Value value={p.value}/>], ['Positional gain', p => <Value value={p.positionGain}/>], ['Overall finish', p => fmt(p.overallRank)], ['Overall gain', p => <Value value={p.overallGain}/>]];
  const evaluated = season ? season.picks.filter(p => p.value != null) : summary.bestPicks;
  const best = season ? [...evaluated].sort((a,b) => b.value-a.value) : summary.bestPicks;
  const worst = season ? [...evaluated].sort((a,b) => a.value-b.value) : summary.worstPicks;
  const table = (title, rows, columns, description, initial = 5) => <DraftTable key={`${year}-${title}`} {...{title, rows, columns, description, initial}}/>;
  return <div className="draft-page"><label className="select-control">Draft season<select aria-label="Draft season" value={season ? year : 'Summary'} onChange={e => onYearChange(e.target.value)}><option value="Summary">Summary</option>{data.years.map(y => <option key={y} value={y}>{y}</option>)}</select></label>
    <div className="draft-hero content-card"><div><p className="page-eyebrow">{season ? `${year} draft room` : 'The art of the pick'}</p><h2>{season ? 'Every round tells a story.' : 'Who makes their picks count?'}</h2><p>{season ? `${season.teamCount} teams · ${season.picks.length} selections · ${season.completedWeeks.length} completed fantasy weeks` : `${summary.seasons.join(' · ')} · ${summary.teams.length} managers`}</p></div><div className="draft-hero-stat"><strong>{season ? season.picks.length : summary.bestPicks.length}</strong><span>{season ? 'draft selections' : 'evaluated selections'}</span></div></div>
    {season && !season.performanceEligible && <p className="archive-note" role="status"><strong>Provisional season recap.</strong> Final rankings and draft value are withheld until the season, draft board, and scoring sources qualify. Points cover completed fantasy weeks only.</p>}
    {season && <p className="draft-description">Fantasy weeks: {season.weeks.join(', ')}. {season.missingScores} picks have unresolved scoring; their totals and rankings are unavailable.</p>}
    {!season && <p className="draft-description">Completed seasons only. Ordered by average positional draft value; explore complementary metrics and every manager below. Totals are shown for context. Small samples are labeled.</p>}
    <Methodology/>
    <div className="content-card draft-value-chart" aria-label="Average draft value by manager"><h3>Average draft value</h3>{view.teams.filter(r => r.averageValue != null).map(r => <div key={r.managerId}><span>{r.manager}</span><div className="draft-value-track"><i style={{left:r.averageValue < 0 ? `${50+r.averageValue/2}%` : '50%', width:`${Math.abs(r.averageValue)/2}%`, background:r.averageValue < 0 ? '#b63d45' : '#148044'}}/></div><Value value={r.averageValue}/></div>)}</div>
    {table(season ? 'Drafting teams' : 'Best overall drafting managers', view.teams, teamColumns)}
    {table('Total net draft value', [...view.teams].sort((a,b) => (b.totalValue ?? -Infinity)-(a.totalValue ?? -Infinity)), teamColumns, 'Volume-sensitive total. Use average value for comparisons across different numbers of picks or seasons.')}
    {table('Best-value picks', best, pickColumns)}{table('Worst-value picks', worst, pickColumns)}
    {season ? <>
      <label className="select-control">Round<select aria-label="Draft round" value={season.rounds.some(r => String(r.round) === round) ? round : String(season.rounds[0]?.round)} onChange={e => setRound(e.target.value)}>{season.rounds.map(r => <option key={r.round} value={r.round}>Round {r.round}</option>)}</select></label>
      {table(`Round ${round} performance`, (season.rounds.find(r => String(r.round) === round) || season.rounds[0])?.picks || [], [['Round rank', p => fmt(p.roundRank)], ...pickColumns], 'Ranked by season fantasy points. Round score is normalized across league sizes.')}
      <DraftBoard key={year} picks={season.picks} columns={pickColumns} table={table}/>
    </> : <>
      <h2 className="draft-group-title">Positional strengths</h2><p className="draft-description">All six positions, with position-aware value, finish percentile, points, success rate and sample size.</p>
      {Object.entries(summary.positions).map(([pos, rows]) => table(`${pos} drafting`, rows, [...teamColumns.slice(0,5), ['Avg finish percentile', r => fmt(r.averageFinish)], ['Avg FPTS', r => fmt(r.averagePoints)], ['Success %', r => fmt(r.successRate)], ['Best pick', r => r.bestPick ? <Player pick={r.bestPick}/> : '—'], ['Underlying picks', evidence]]))}
      <h2 className="draft-group-title">When managers make their move</h2><p className="draft-description">First-selection timing gives each manager-season one vote, even when several quarterbacks are drafted.</p>
      {Object.entries(summary.tendencies).map(([pos, rows]) => <React.Fragment key={pos}><div className="draft-bars content-card" role="img" aria-label={`${pos} average first-selection round by manager`}>{rows.map(r => <div key={r.managerId}><span>{r.manager}</span><meter min="0" max="16" value={r.averageFirstRound}>{fmt(r.averageFirstRound)}</meter><strong>R{fmt(r.averageFirstRound)}</strong></div>)}</div>{table(`${pos} draft tendencies`, rows, [['Manager / team', teamCell], ['Seasons', r => r.seasons.join(', ')], ['Picks', r => r.picks], ['Avg round', r => fmt(r.averageRound)], ['Normalized pick¹', r => fmt(r.normalizedPick)], ['Earliest', r => `${r.earliest.season} · R${r.earliest.round}.${r.earliest.pickInRound}`], ['Typical first round', r => fmt(r.firstRound)], ['Avg first round', r => fmt(r.averageFirstRound)], ['Pick share %', r => fmt(r.share)], ['First picks', evidence]], '¹ Normalized pick = 1 + (overall pick − 1) ÷ team count. Lower means earlier.')}</React.Fragment>)}
      <Rookies data={summary.rookies} table={table} teamColumns={teamColumns} pickColumns={pickColumns}/>
      <h2 className="draft-group-title">Draft patterns</h2>{Object.entries(summary.trends).map(([title, rows]) => table(title, rows, teamColumns, 'Descriptive results with underlying picks. Check sample sizes before drawing conclusions.'))}
      {table('Most consistent drafting managers', summary.teams.filter(r => r.seasonSpread != null).sort((a,b) => a.seasonSpread-b.seasonSpread), teamColumns, 'Lowest spread in season-average value first. Consistency can describe consistently weak results too; read alongside average value.')}
    </>}
  </div>;
}
function DraftBoard({ picks, columns, table }) {
  const [query, setQuery] = useState('');
  const match = /^\d+$/.test(query) ? picks.filter(p => p.overallPick === Number(query)) : picks.filter(p => `${p.playerName} ${p.manager} ${p.team.name} ${p.position}`.toLowerCase().includes(query.toLowerCase()));
  useEffect(() => { const update = () => { const pick = new URLSearchParams(window.location.hash.split('?')[1]).get('pick'); if (pick) { setQuery(pick); document.getElementById('draft-board')?.scrollIntoView?.(); } }; update(); window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update); }, []);
  return <div id="draft-board"><label className="select-control">Find a draft pick<input aria-label="Find a draft pick" type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Player, manager, position or pick number"/></label>{table('Full draft board', match, [['Overall pick', p => p.overallPick], ['Round', p => p.round], ['Pick in round', p => p.pickInRound], ...columns], 'Authoritative ESPN selection order. Expand to view every matching selection.', 10)}</div>;
}
function Rookies({ data, table, teamColumns, pickColumns }) {
  const picks = [...data.picks].filter(p => p.value != null).sort((a,b) => b.value-a.value);
  return <><h2 className="draft-group-title">Rookie bets</h2><p className="draft-description">{data.picks.length} rookie selections / {data.knownPicks} picks with known classification. {data.unknownPicks} player picks have unknown rookie status. Same-season, same-position, four-round-band comparison: {data.controls.length} matched rookie picks; average {fmt(data.averageControlDifference, 2)} FPTS above non-rookie controls. At least three controls per pick; no causal claim.</p>
    {table('Rookie drafting performance', data.teams, [...teamColumns, ['Avg rookie round', r => fmt(r.averageDraftRound)], ['Avg rookie pick', r => fmt(r.averageDraftPick)], ['Normalized rookie pick', r => fmt(r.averageNormalizedPick)], ['Rookie share %', r => fmt(r.rookieShare)]])}
    {table('Managers drafting the most rookies', [...data.teams].sort((a,b) => b.picks-a.picks), teamColumns, 'Counts reflect opportunity and tenure. Read with seasons and sample size.')}
    {table('Best rookie picks', picks, pickColumns)}{table('Worst rookie picks', [...picks].reverse(), pickColumns)}
  </>;
}
