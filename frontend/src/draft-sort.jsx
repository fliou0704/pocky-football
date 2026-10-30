import React, {useState} from 'react';

const fields = {
  'Player': 'playerName', 'Player / position': 'playerName', 'Fantasy team': r => r.team?.name,
  'Manager / team': r => `${r.manager} ${r.team?.name || ''}`, 'Draft pick': 'overallPick',
  'Overall pick': 'overallPick', 'Pick in round': 'pickInRound', 'Season': 'season', 'Round': 'round',
  'Season FPTS': 'points', 'FPPG': 'fppg', 'NFL games': 'gamesPlayed',
  'Position finish': 'positionalRank', 'Final positional rank': 'positionalRank',
  'Positional rank': 'positionalRank', 'Round Rank': 'roundRank', 'Round rank': 'roundRank',
  'Benchmark pick': 'benchmarkPick', 'Benchmark overall pick': 'benchmarkPick',
  'Draft position gain': 'draftPositionGain', 'Positional draft-slot gain': 'draftPositionGain',
  'Average Round Rank': 'averageRoundRank', 'Avg Positional Draft-Slot Gain': 'averageDraftSlotGain',
  'Avg Round': 'averageRound', 'Avg First Pick': 'averageFirstPick', 'Rookie Picks': 'picks',
};
export function sortValue(row, label, accessor) {
  const field = accessor || fields[label];
  return typeof field === 'function' ? field(row) : row[field];
}
export function sortDraftRows(rows, column, direction = 'ascending') {
  if (!column) return rows;
  const [label,,accessor] = column;
  return rows.map((row,index)=>({row,index})).sort((a,b)=>{
    const x=sortValue(a.row,label,accessor), y=sortValue(b.row,label,accessor);
    const missing = v => v == null || (typeof v === 'number' && !Number.isFinite(v));
    if (missing(x) !== missing(y)) return missing(x) ? 1 : -1;
    let result = missing(x) ? 0 : typeof x === 'number' && typeof y === 'number' ? x-y
      : String(x).localeCompare(String(y),undefined,{numeric:true,sensitivity:'base'});
    if (direction === 'descending') result *= -1;
    // Canonical identifiers stabilize ties independently of prior sorts.
    return result || String(a.row.managerId || '').localeCompare(String(b.row.managerId || ''))
      || (a.row.season || 0)-(b.row.season || 0) || (a.row.overallPick || 0)-(b.row.overallPick || 0) || a.index-b.index;
  }).map(({row})=>row);
}
export function useDraftSort(rows, columns) {
  const [sort,setSort]=useState(null);
  return {rows:sortDraftRows(rows,columns.find(c=>c[0]===sort?.label),sort?.direction),sort,
    toggle:label=>setSort(previous=>({label,direction:previous?.label===label && previous.direction==='ascending'?'descending':'ascending'}))};
}
export function SortHeaders({columns,sorting}) {
  return <tr>{columns.map(([label,,accessor])=>{
    const sortable=Boolean(accessor || fields[label]);
    const active=sorting.sort?.label===label;
    return <th key={label} scope="col" aria-sort={sortable ? active?sorting.sort.direction:'none':undefined}>
      {sortable ? <button type="button" className="draft-sort" onClick={()=>sorting.toggle(label)}>{label}<span aria-hidden="true">{active?(sorting.sort.direction==='ascending'?' ↑':' ↓'):' ↕'}</span></button>:label}
    </th>;
  })}</tr>;
}
