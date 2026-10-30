import React, { useId, useState } from 'react';
import {useDraftSort, SortHeaders} from './draft-sort.jsx';

const fmt = value => value == null ? '—' : Number(value).toFixed(1);
const signed = value => value == null ? '—' : `${value > 0 ? '+' : ''}${fmt(value)}`;

function PickDetails({ picks, title, Player, Points, positional }) {
  const provisional = picks.some(p=>p.evaluationStatus === 'provisional');
  const columns = ['Season', 'Round', 'Overall pick', 'Player / position', 'Season FPTS', ...(provisional ? ['FPPG', 'NFL games'] : []), 'Round rank',
    ...(positional ? ['Positional rank', 'Benchmark overall pick', 'Positional draft-slot gain'] : [])].map(label=>[label]);
  const sorting = useDraftSort(picks, columns);
  return <div className="draft-inline-detail"><table aria-label={`${title} picks`}>
    <thead><SortHeaders columns={columns} sorting={sorting}/></thead>
    <tbody>{sorting.rows.map(pick => <tr key={`${pick.season}/${pick.overallPick}`}>
      <td>{pick.season}</td><td>{pick.round}</td><td>{pick.overallPick}</td>
      <td><Player pick={pick}/></td><td><Points pick={pick}/></td><>{provisional && <><td>{pick.fppg == null ? "—" : pick.fppg.toFixed(2)}</td><td>{pick.gamesPlayed ?? "—"}</td></>}<td>{pick.roundRank ?? "—"}</td></>
      {positional && <><td>{pick.positionalRank ?? "—"}</td><td>{pick.benchmarkPick ?? '—'}{pick.benchmarkStatus === 'below_drafted_range' && <small>Below drafted positional range</small>}</td>
        <td>{signed(pick.draftPositionGain)}{pick.draftPositionGain == null && <small>{pick.benchmarkStatus}</small>}</td></>}
    </tr>)}</tbody>
  </table>{!picks.length && <p>No historical selections available.</p>}</div>;
}

export function SummaryTable({ title, rows, columns, Team, Player, Points, positional = false, initial = 5 }) {
  const [expanded, setExpanded] = useState(null), [all, setAll] = useState(false);
  const id = useId();
  const sorting = useDraftSort(rows, [['Manager / team'], ...columns]);
  return <section className="home-section draft-section">
    <div className="section-title"><h2>{title}</h2></div>
    <div className="content-card table-card"><div className="draft-scroll">
      <table className="draft-summary-table" aria-label={title}>
        <colgroup><col style={{width: columns.length === 1 ? '65%' : '50%'}}/>{columns.map(([label]) => <col key={label}/>)}</colgroup>
        <thead><SortHeaders columns={[["Manager / team"], ...columns]} sorting={sorting}/></thead>
        <tbody>{(all ? sorting.rows : sorting.rows.slice(0, initial)).map(row => {
          const open = expanded === row.managerId, detailId = `${id}-${row.managerId}`;
          const toggle = () => setExpanded(open ? null : row.managerId);
          return <React.Fragment key={row.managerId}>
            <tr className={`draft-manager-row ${open ? 'is-expanded' : ''}`} onClick={toggle} aria-expanded={open}>
              <td><button className="draft-manager-toggle" type="button" aria-expanded={open} aria-controls={detailId}
                aria-label={`${row.manager}: historical draft picks`} onClick={event => { event.stopPropagation(); toggle(); }}>
                <span><Team team={row.team} season={row.team.season}/><small>{row.manager}</small></span>
                <span aria-hidden="true">{open ? '⌃' : '⌄'}</span>
              </button></td>
              {columns.map(([label, cell]) => <td key={label}>{cell(row)}</td>)}
            </tr>
            {open && <tr className="draft-detail-row" id={detailId}><td colSpan={columns.length + 1}>
              <PickDetails picks={row.evidence || []} title={row.manager} {...{ Player, Points, positional }}/>
            </td></tr>}
          </React.Fragment>;
        })}</tbody>
      </table>
    </div>{!rows.length && <p className="draft-description">No eligible historical selections.</p>}
      {rows.length > initial && <button className="draft-expand" type="button" aria-expanded={all}
        onClick={() => { setAll(!all); setExpanded(null); }}>{all ? 'Show fewer managers' : 'Show all managers'}</button>}
    </div>
  </section>;
}

export default function DraftSummary({ summary, Team, Player, Points }) {
  const roundColumns = [['Average Round Rank', row => fmt(row.averageRoundRank)]];
  const table = (title, rows, columns, positional = false, initial = 5) =>
    <SummaryTable key={title} {...{ title, rows, columns, Team, Player, Points, positional, initial }}/>;
  return <div className="draft-summary">
    <p className="draft-description">Summary only includes current managers</p><p className="draft-description">Finalized seasons only. Round Rank measures positional draft-slot gain, greatest first; manager averages are better when lower.</p>
    {table('Overall Round Performance', summary.teams, roundColumns)}
    <h2 className="draft-group-title">Positional Drafting Performance</h2>
    {Object.entries(summary.positions).map(([position, rows]) => table(`${position} drafting`, rows,
      [['Avg Positional Draft-Slot Gain', row => signed(row.averageDraftSlotGain)]], true))}
    <details className="draft-panel content-card"><summary>Draft Tendencies</summary>
      {Object.entries(summary.tendencies).map(([position, rows]) => table(`${position} draft tendencies`, rows,
        [['Avg Round', row => fmt(row.averageRound)], ['Avg First Pick', row => fmt(row.averageFirstPick)]]))}
      {table('Rookie Selections by Manager', summary.rookies.teams, [['Rookie Picks', row => row.picks]])}
    </details>
    <details className="draft-panel content-card"><summary>Historical Round Patterns</summary>
      {Object.entries(summary.trends).map(([round, rows]) => <details className="draft-panel draft-history-round" key={round}>
        <summary>{round}</summary>{table(`${round} manager performance`, rows, roundColumns, false, rows.length)}
      </details>)}
    </details>
  </div>;
}
