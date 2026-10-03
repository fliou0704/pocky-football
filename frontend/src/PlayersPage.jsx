import React, {useEffect,useId,useMemo,useState} from 'react';
import {ageOnDate,dateLabel,formatHeight,playerHash,playerPoints as points,searchPlayers,updatedLabel,gamePoints,gameOpponent} from './player-view.js';
import './players.css';

function Portrait({player,large=false}) {
  const [failed,setFailed]=useState(false);
  const image=player.entityType==='team_defense'?player.logo:player.headshot;
  useEffect(()=>setFailed(false),[image]);
  return <span className={large?'player-headshot-wrap':'player-search-portrait'}>{image&&!failed?<img src={image} alt={large?`${player.name} ${player.entityType==='team_defense'?'logo':'headshot'}`:''} loading={large?'eager':'lazy'} onError={()=>setFailed(true)}/>:<span className="player-image-fallback" aria-label="Image unavailable">{player.entityType==='team_defense'?'D/ST':player.name?.split(' ').map(n=>n[0]).slice(0,2).join('')}</span>}</span>;
}
export function PlayerSearch({players,compact=false}) {
  const [query,setQuery]=useState('');
  const inputId=useId();
  const matches=useMemo(()=>searchPlayers(players,query,{type:''}).slice(0,8),[players,query]);
  return <div className={`player-search ${compact?'player-search-compact':''}`}>
    <label htmlFor={inputId}>{compact?'Search for another player':'Find a player'}</label>
    <input id={inputId} type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search Pocky Football players…" autoComplete="off"/>
    {query.trim()&&<div className="player-search-results" role="region" aria-live="polite" aria-label="Player search results">
      {matches.map(player=><a key={player.espnId} className="player-search-result" href={playerHash(player.espnId)} onClick={()=>setQuery('')}><Portrait player={player}/><span><strong>{player.name}</strong><small>{player.position} · Latest NFL team {player.nflTeam||'—'}</small></span></a>)}
      {!matches.length&&<p className="player-empty" role="status">No Pocky Football players found.</p>}
    </div>}
  </div>;
}

function BioItem({label,value,featured=false}) {return value!=null&&value!==''?<div className={featured?'bio-item bio-featured':'bio-item'}><dt>{label}</dt><dd>{value}</dd></div>:null;}
function Profile({player,updatedAt}) {
  const defense=player.entityType==='team_defense';
  const draft=player.nflDraft;
  const draftText=draft?.year?[draft.year,draft.round?`Round ${draft.round}`:null,draft.overallPick?`Pick ${draft.overallPick}`:null,draft.team].filter(Boolean).join(' · '):null;
  return <section className="player-profile"><Portrait player={player} large/><div className="player-profile-main"><p className="page-eyebrow">Pocky Football {defense?'Team Defense':'Player'}</p><h2>{player.name}</h2><p className="player-nfl-line">{player.position}{!defense&&player.jerseyNumber!=null?` · #${player.jerseyNumber}`:''}</p><dl className="player-bio"><BioItem label="Latest NFL team" value={player.nflTeam}/>{!defense&&<><BioItem label="Age" value={ageOnDate(player.birthDate)} featured/><BioItem label="Height" value={formatHeight(player.heightInches)}/><BioItem label="Weight" value={player.weightPounds?`${player.weightPounds} lb`:null}/><BioItem label="Born" value={dateLabel(player.birthDate)}/><BioItem label="College" value={player.college}/><BioItem label="NFL Draft" value={draftText}/><BioItem label="Rookie season" value={player.rookieSeason}/></>}</dl>{updatedLabel(updatedAt)&&<p className="player-note player-updated">Last updated: <time dateTime={updatedAt}>{updatedLabel(updatedAt)}</time></p>}</div></section>;
}
function PlayerTable({caption,headers,children}) {return <div className="content-card table-card"><div className="player-table-scroll"><table className="player-table"><caption className="sr-only">{caption}</caption><thead><tr>{headers.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div></div>;}
function TeamList({teams,Team}) {return teams.length?<div className="player-team-list">{teams.map(t=><Team key={t.teamId} team={t}/>)}</div>:<span>—</span>;}
function StatValue({value}) {return value==null?'—':value.toLocaleString('en-US',{maximumFractionDigits:2});}
function GameTable({weeks,columns}) {
  return weeks.length?<PlayerTable caption="NFL game performances" headers={['Week','Opp',...columns.map(c=>c.label),'FPTS']}>{weeks.map(w=><tr key={`${w.season}-${w.week}`}><th scope="row">{w.week}</th><td>{gameOpponent(w)}</td>{columns.map(c=><td className="numeric" key={c.key}><StatValue value={['played','live'].includes(w.gameState)?w.nflStats?.[c.key]:null}/></td>)}<td className="player-fpts numeric">{gamePoints(w)}</td></tr>)}</PlayerTable>:<p className="player-empty">No games recorded.</p>;
}
function GameLog({detail,columns,requestedSeason,Section}) {
  const latest=detail.seasons.find(s=>s.season===detail.currentSeason)||detail.seasons[0];
  const [season,setSeason]=useState(detail.seasons.some(s=>String(s.season)===String(requestedSeason))?String(requestedSeason):String(latest.season));
  const recent=(detail.seasons.find(s=>s.season===detail.currentSeason)?.weeks||[]).filter(w=>w.gameState==='played').sort((a,b)=>b.week-a.week).slice(0,5);
  const selected=detail.seasons.find(s=>String(s.season)===season);
  return <><Section title="Recent Games" meta={`${detail.currentSeason} season`}><GameTable weeks={recent} columns={columns}/></Section><Section title="Complete Game Log"><label className="select-control player-log-season">Season<select aria-label="Game Log season" value={season} onChange={e=>setSeason(e.target.value)}>{detail.seasons.map(s=><option key={s.season}>{s.season}</option>)}</select></label><GameTable weeks={[...(selected?.weeks||[])].sort((a,b)=>b.week-a.week)} columns={columns}/></Section></>;
}
function TransactionDescription({transaction:t,Team}) {
  if(t.type==='draft')return <>Drafted by <TeamList teams={t.toTeams} Team={Team}/> · Round {t.round??'—'} · Overall Pick {t.overallPick??'—'}</>;
  if(t.type==='trade')return <>Traded from <TeamList teams={t.fromTeams} Team={Team}/> to <TeamList teams={t.toTeams} Team={Team}/></>;
  if(t.type==='drop')return <>Dropped by <TeamList teams={t.fromTeams} Team={Team}/></>;
  return <>Added by <TeamList teams={t.toTeams} Team={Team}/>{t.type==='waiver_add'?' via Waivers':' via Free Agency'}</>;
}
export function PlayerDetail({detail,requestedSeason,Section,Team}) {
  const [tab,setTab]=useState('career');
  const columns=detail.statColumns||[];
  const transactions=detail.seasons.flatMap(s=>[...s.transactions.map(t=>({...t,season:s.season})),...s.draft.map(d=>({type:'draft',timestamp:d.timestamp,season:s.season,round:d.round,overallPick:d.overallPick,fromTeams:[],toTeams:[d.team]}))]).sort((a,b)=>b.season-a.season||(b.timestamp||`${b.season}-01-01`).localeCompare(a.timestamp||`${a.season}-01-01`));
  return <><Profile player={detail.profile} updatedAt={detail.metadataGeneratedAt}/>
    <nav className="player-tabs" role="tablist" aria-label="Player sections">{[['career','Career'],['games','Game Log'],['transactions','Transactions']].map(([id,label])=><button key={id} id={`player-tab-${id}`} role="tab" aria-selected={tab===id} aria-controls={`player-panel-${id}`} onClick={()=>setTab(id)}>{label}</button>)}</nav>
    <div role="tabpanel" id={`player-panel-${tab}`} aria-labelledby={`player-tab-${tab}`}>
    {tab==='career'&&<Section title="Pocky Football Career"><PlayerTable caption="Player season totals" headers={['Season','Fantasy Team','GP',...columns.map(c=>c.label),'FPTS','FPPG']}>{detail.seasons.map(s=><tr key={s.season}><th scope="row">{s.season}{!s.complete&&<small>In progress</small>}</th><td><TeamList teams={s.ownership.map(o=>o.team)} Team={Team}/></td><td className="numeric"><StatValue value={s.seasonStats?.gp}/></td>{columns.map(c=><td className="numeric" key={c.key}><StatValue value={s.seasonStats?.nflStats?.[c.key]}/></td>)}<td className="player-fpts numeric">{points(s.seasonStats?.points)}</td><td className="numeric">{points(s.seasonStats?.fppg)}</td></tr>)}</PlayerTable></Section>}
    {tab==='games'&&<GameLog detail={detail} columns={columns} requestedSeason={requestedSeason} Section={Section}/>}
    {tab==='transactions'&&<Section title="Pocky Football Transactions" meta="Most recent first"><ol className="player-transactions">{transactions.map((t,i)=><li key={`${t.season}-${i}`}><div>{t.timestamp?<time dateTime={t.timestamp}>{dateLabel(t.timestamp)}</time>:<time>{t.season}</time>}<small>{t.season} season</small></div><div className="player-transaction-description"><TransactionDescription transaction={t} Team={Team}/></div></li>)}</ol>{!transactions.length&&<p className="player-empty">No transactions recorded.</p>}</Section>}
    </div></>;
}
export default function PlayersPage({path,loadData,playerId,requestedSeason='All-Time',onSeasonChange,Section,Team}) {
  const [index,setIndex]=useState(null),[detail,setDetail]=useState(null),[error,setError]=useState(null);
  useEffect(()=>{let live=true;setIndex(null);setError(null);loadData(path).then(d=>{if(live)setIndex(d);}).catch(()=>{if(live)setError('Player search is unavailable.');});return()=>{live=false;};},[path,loadData]);
  useEffect(()=>{let live=true;setDetail(null);setError(null);if(!index||playerId==null)return;
    const entry=index.players.find(p=>p.espnId===playerId);
    if(!entry){setError('Player not found in Pocky Football history.');return;}
    loadData(entry.path).then(d=>{if(live)setDetail(d);}).catch(()=>{if(live)setError('Player history is unavailable.');});return()=>{live=false;};},[index,playerId,loadData]);
  return <div className="players-page">{index&&<PlayerSearch players={index.players} compact={playerId!=null}/>} {error?<p role="alert">{error}</p>:!index||playerId!=null&&!detail?<p role="status">Loading players…</p>:detail&&playerId!=null?<PlayerDetail key={playerId} detail={detail} requestedSeason={requestedSeason} onSeasonChange={onSeasonChange} Section={Section} Team={Team}/>:null}</div>;
}
