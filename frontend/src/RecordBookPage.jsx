import React, { useEffect, useRef, useState } from 'react';
import { recordValue, recordView, rankedEntryKey } from './record-book-view.js';
import { nextExpanded } from './h2h-view.js';
import MatchupDetails from './MatchupDetails.jsx';
import './record-book.css';

function Holder({ holder, Team, seasonOnly = false }) {
  return <div className="rb-holder">{holder.name && <strong className="rb-player">{holder.name}</strong>}{holder.team && <Team team={holder.team}/>}
    {holder.teams?.length > 1 && <small>Contributions for {holder.teams.map(t => t.name).join(', ')}</small>}
    <small>{holder.season}{!seasonOnly && holder.week ? ` · Week ${holder.week}` : ''}{holder.startWeek ? ` · Weeks ${holder.startWeek}–${holder.endWeek}` : ''}{holder.isPlayoff ? ` · ${holder.roundLabel || 'Playoffs'}` : ''}</small>
    {holder.name && <small>{holder.nflTeam} · {holder.position}{!seasonOnly && holder.nflOpponent ? ` · vs. ${holder.nflOpponent}` : ''}</small>}
    {!seasonOnly && !holder.name && holder.opponent && <small>{holder.isTie ? 'Tied with' : 'vs.'} {holder.opponent.name}{holder.opponentScore != null ? ` · ${(holder.score ?? holder.value).toFixed(2)}–${holder.opponentScore.toFixed(2)}` : ''}</small>}
    {holder.acquiredAt && <small>{holder.acquisitionType === 'waiver_add' ? 'Waiver' : 'Free Agent'} · {new Date(holder.acquiredAt).toLocaleDateString()} · Week {holder.acquisitionWeek}{holder.faab != null ? ` · $${holder.faab} FAAB` : ''}</small>}
  </div>;
}

export function RankedRecord({ record, Team, Section, manifest, loadData, cache }) {
  const [expanded,setExpanded]=useState(false),[open,setOpen]=useState(null);
  const leaders=record.leaders || record.holders;
  const shown=expanded ? leaders : leaders.slice(0,1);
  return <Section title={record.label}><article className="content-card rb-record">
    {!shown.length ? <p className="rb-pending">No eligible performances available.</p> : <>
      <ol className="rb-ranking">{shown.map(holder=>{const key=rankedEntryKey(holder), active=open===key;
        const content=<><span className="rb-rank">#{holder.rank || 1}</span><Holder holder={holder} Team={Team}/><strong className="rb-value">{recordValue(record,holder)}{record.matchupDetails && <small>{active ? 'Close lineup' : 'View lineup'} <span aria-hidden="true">{active ? '⌃' : '⌄'}</span></small>}</strong></>;
        return <li key={key}>{record.matchupDetails ? <button type="button" className="rb-ranked-row" aria-expanded={active} aria-controls={`${record.id}-${key}`} onClick={()=>setOpen(nextExpanded(open,key))}>{content}</button> : <div className="rb-ranked-row">{content}</div>}
          {active && record.matchupDetails && <div id={`${record.id}-${key}`} className="h2h-details"><MatchupDetails key={key} row={holder.matchup} manifest={manifest} loadData={loadData} cache={cache} Team={Team}/></div>}
        </li>;
      })}</ol>
      {!expanded && record.holders.length>1 && <p className="rb-tie">{record.holders.length} tied record holders</p>}
      {leaders.length>1 && <button type="button" className="rb-expand" aria-expanded={expanded} onClick={()=>{setExpanded(!expanded);setOpen(null);}}>{expanded ? 'Show record holder' : `View Top ${record.limit}`} <span aria-hidden="true">{expanded ? '⌃' : '⌄'}</span></button>}
    </>}
  </article></Section>;
}

export default function RecordBookPage({ path, loadData, year, onYearChange, Team, Section }) {
  const [data,setData] = useState(null), [error,setError] = useState(false);
  const cache=useRef(new Map());
  useEffect(() => { let active=true;setError(false);setData(null);loadData(path).then(value=>{if(active)setData(value);}).catch(()=>{if(active)setError(true);}); return()=>{active=false;}; },[path,loadData]);
  if(error) return <p role="alert">Record Book is unavailable. Please reload to try again.</p>;
  if(!data) return <p role="status">Loading Record Book…</p>;
  const view=recordView(data,year),selected=data.seasons[String(year)] ? String(year) : 'All-Time';
  const manifest={lineupPath:data.lineupPath};
  return <div className="record-book">
    <label className="select-control rb-season">Season<select aria-label="Record Book season" value={selected} onChange={event=>onYearChange(event.target.value)}><option value="All-Time">All-Time</option>{data.years.map(y=><option key={y} value={y}>{y}</option>)}</select></label>
    {selected === 'All-Time' ? <Section title="Championship History"><div className="content-card rb-timeline"><ol>{view.champions.map(c=><li key={c.season}><span>{c.season}</span><span aria-hidden="true">♛</span><Team team={c.team}/></li>)}</ol></div></Section> : <>
      <Section title={`${selected} Honors`}><div className="rb-premier"><article className="content-card rb-award"><p className="rb-kicker">Champion</p>{view.champions.length ? <Team team={view.champions[0].team}/> : <p>Unavailable</p>}</article>
        <article className="content-card rb-award"><p className="rb-kicker">Most Valuable Player</p>{view.mvp.holders.map((h,i)=><div key={i} className="rb-leader"><Holder holder={h} Team={Team} seasonOnly/><strong className="rb-value">{h.value.toFixed(2)} <small>FPTS</small></strong></div>)}</article></div></Section>
      <Section title="All-Fantasy Team" meta="9 starters · 7 bench"><div className="content-card rb-roster">{[['Starters',false],['Bench',true]].map(([label,bench])=><div className="rb-roster-group" key={label}><h3>{label}</h3><ol>{view.allFantasyTeam.filter(p=>(p.awardSlot==='BE')===bench).map((p,index)=><li key={p.playerId}><span className="lineup-slot">{p.awardSlot}{bench ? ` ${index+1}` : ''}</span><div><Holder holder={p} Team={Team} seasonOnly/>{p.tiedAlternates.length>0 && <small>Tied: {p.tiedAlternates.map(a=>a.name).join(', ')}</small>}</div><strong>{p.value.toFixed(2)} <small>FPTS</small></strong></li>)}</ol></div>)}</div></Section>
    </>}
    {[...view.teamRecords,...view.playerRecords,...view.positionRecords].map(record=><RankedRecord key={`${selected}/${record.id}`} record={record} Team={Team} Section={Section} manifest={manifest} loadData={loadData} cache={cache}/>)}
    {selected==='All-Time' && <Section title="Players with Negative Point Weeks"><div className="content-card rb-position"><details><summary>View performances <span>{view.negativeStarterWeeks.length} <span aria-hidden="true">⌄</span></span></summary><ul>{view.negativeStarterWeeks.map((h,i)=><li key={i}><span>{h.season}<small>Week {h.week}</small></span><div className="rb-leader"><Holder holder={h} Team={Team}/><strong>{h.value.toFixed(2)}</strong></div></li>)}</ul>{!view.negativeStarterWeeks.length && <p>No negative player weeks.</p>}</details></div></Section>}
  </div>;
}
