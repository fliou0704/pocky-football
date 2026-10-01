import React, { useEffect, useState } from 'react';
import { recordValue, recordView } from './record-book-view.js';
import './record-book.css';

function Holder({ holder, Team, seasonOnly = false }) {
  return <div className="rb-holder"><div>{holder.name && <strong className="rb-player">{holder.name}</strong>}<Team team={holder.team}/>
    {holder.teams?.length > 1 && <small>Contributions for {holder.teams.map(t => t.name).join(', ')}</small>}
    <small>{holder.season}{!seasonOnly && holder.week ? ` · Week ${holder.week}` : ''}{holder.startWeek ? ` · Weeks ${holder.startWeek}–${holder.endWeek}` : ''}{holder.isPlayoff ? ` · ${holder.roundLabel || 'Playoffs'}` : ''}</small>
    {holder.name && <small>{holder.nflTeam} · {holder.position} · Slot {holder.slot}</small>}
    {!seasonOnly && holder.opponent && <small>{holder.isTie ? 'Tied with' : 'vs.'} {holder.opponent.name}{holder.opponentScore != null ? ` · ${holder.score != null ? holder.score.toFixed(2) + '–' : ''}${holder.opponentScore.toFixed(2)}` : ''}</small>}
    {holder.games != null && <small>{holder.games} regular-season games</small>}
  </div></div>;
}

function RecordCard({ record, Team }) {
  const first = record.holders[0];
  return <article className="content-card rb-record"><p className="rb-kicker">{record.label}</p>
    {first ? <><div className="rb-leader"><Holder holder={first} Team={Team}/><strong className="rb-value">{recordValue(record, first)}</strong></div>
      {record.holders.length > 1 && <p className="rb-tie">{record.holders.length} tied holders</p>}
      <details><summary>View record details <span aria-hidden="true">⌄</span></summary><p className="rb-rule">{record.rule}</p><ul>{record.holders.map((holder,index) => <li key={index}><Holder holder={holder} Team={Team}/><strong>{recordValue(record,holder)}</strong></li>)}</ul></details>
    </> : <p className="rb-pending">No eligible completed {record.unit === 'record' || record.id.startsWith('season-') ? 'regular seasons' : 'performances'}.</p>}
  </article>;
}

export default function RecordBookPage({ path, loadData, year, Team, Section }) {
  const [data,setData] = useState(null), [error,setError] = useState(false);
  useEffect(() => { let active=true; loadData(path).then(value=>{if(active)setData(value);}).catch(()=>{if(active)setError(true);}); return()=>{active=false;}; },[path,loadData]);
  if(error) return <p role="alert">Record Book is unavailable. Please reload to try again.</p>;
  if(!data) return <p role="status">Loading Record Book…</p>;
  const view = recordView(data,year), selected = data.seasons[String(year)] ? String(year) : 'All-Time';
  const current = view.coverage.some(c=>!c.complete), partial = view.coverage.some(c=>c.missingLineupWeeks.length || c.missingPlayerPoints);
  return <div className="record-book">
    {current && <p className="rb-notice">{selected === 'All-Time' ? 'Current-season weekly records and streaks are included.' : 'Season in progress: weekly records, streaks and starter honors are season-to-date.'} Full-season records require a completed regular season.</p>}
    {partial && <p className="rb-notice">Player records include available actual weekly points only; missing lineups or points are excluded.</p>}
    {selected === 'All-Time' ? <Section title="Championship History"><div className="content-card rb-timeline"><ol>{view.champions.map(c=><li key={c.season}><span>{c.season}</span><span aria-hidden="true">♛</span><Team team={c.team}/></li>)}</ol></div></Section> : <>
      <Section title={`${selected} Honors`}><div className="rb-premier"><article className="content-card rb-award"><p className="rb-kicker">Champion</p>{view.champions.length ? <Team team={view.champions[0].team}/> : <p>Season in progress</p>}</article>
        <article className="content-card rb-award"><p className="rb-kicker">Most Valuable Player · Starter Points{current ? ' to Date' : ''}</p>{view.mvp.holders.length ? view.mvp.holders.map((h,i)=><div key={i} className="rb-leader"><Holder holder={h} Team={Team} seasonOnly/><strong className="rb-value">{h.value.toFixed(2)} <small>FPTS</small></strong></div>) : <p>No starter performances available.</p>}</article></div></Section>
      <Section title="All-Fantasy Team" meta="Regular-season starter contributions"><div className="content-card rb-roster"><p className="rb-rule">Season lineup slots; players ranked by actual starter points. FLEX uses RB/WR/TE. Each player appears once; equal totals use player ID order and list tied alternatives.</p><ol>{view.allFantasyTeam.map((p,index)=><li key={index}><span className="lineup-slot">{p.awardSlot}</span><div><Holder holder={p} Team={Team} seasonOnly/>{p.tiedAlternates.length > 0 && <small>Tied: {p.tiedAlternates.map(a=>a.name).join(', ')}</small>}</div><strong>{p.value.toFixed(2)} <small>FPTS</small></strong></li>)}</ol></div></Section>
    </>}
    <Section title="Team Records"><div className="rb-records">{view.teamRecords.map(record=><RecordCard key={record.id} record={record} Team={Team}/>)}</div></Section>
    <Section title="Player Records"><div className="rb-records">{view.playerRecords.map(record=><RecordCard key={record.id} record={record} Team={Team}/>)}</div></Section>
    <section className="content-card rb-position"><details><summary>Players with Negative Point Weeks <span>{view.negativeStarterWeeks.length} performances <span aria-hidden="true">⌄</span></span></summary><p className="rb-rule">Historical starter slots only; bench, IR and missing actual points excluded.</p><ul>{view.negativeStarterWeeks.map((h,i)=><li key={i}><span>{h.season}<small>Week {h.week}</small></span><div className="rb-leader"><Holder holder={h} Team={Team}/><strong>{h.value.toFixed(2)}</strong></div></li>)}</ul>{!view.negativeStarterWeeks.length && <p>No negative starter weeks.</p>}</details></section>
    <section className="content-card rb-position"><details><summary>Single-Week Position Leaders <span aria-hidden="true">⌄</span></summary><p className="rb-rule">Actual weekly points in all roster slots, including bench and IR; completed matchups only.</p><ul>{view.positionRecords.map(record=><li key={record.id}><strong>{record.label}</strong><div>{record.holders.length ? record.holders.map((h,i)=><div className="rb-leader" key={i}><Holder holder={h} Team={Team}/><strong>{h.value.toFixed(2)}</strong></div>) : <p>No eligible performances.</p>}</div></li>)}</ul></details></section>
  </div>;
}
