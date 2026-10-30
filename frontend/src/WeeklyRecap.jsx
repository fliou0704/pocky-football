import React, { useEffect, useState } from 'react';
import TeamOfWeek from './TeamOfWeek.jsx';
import { Team, Match } from './Match.jsx';

export function useWeekly(path, loadData, season) {
  const [loaded, setLoaded] = useState(null);
  useEffect(() => {
    let active = true;
    if (path && loadData) loadData(path).then(data => {
      if (active) setLoaded({path, data: data?.season === season ? data : null});
    }).catch(() => { if (active) setLoaded({path, data:null}); });
    return () => { active = false; };
  }, [path, loadData, season]);
  return loaded?.path === path && loaded?.data?.season === season ? loaded.data : null;
}
export const weeklyPath = path => path?.replace(/(?:team-of-week|league)\.json$/, 'weekly.json');
export const matchupId = (season, match) => `${season}-${match.week}-${[match.homeTeamId, match.awayTeamId].sort((a,b)=>a-b).join('-')}`;
export function PreviewIndicators({ match, season, weekly }) {
  if (!['upcoming', 'live'].includes(match.status)) return null;
  const labels = weekly?.previews?.[match.week]?.[matchupId(season, match)] || [];
  return labels.length ? <div className="preview-indicators" aria-label="Matchup previews">{labels.map(label => <span key={label} title={label.startsWith('Rivalry') ? 'Prior meetings between verified managers, including playoffs. Record includes ties when present.' : 'Entering this week'}><span aria-hidden="true">✧ </span>{label}</span>)}</div> : null;
}
export default function WeeklyRecap({ recap, teams, season, teamOfWeekPath, loadData }) {
  const [expanded, setExpanded] = useState(false);
  if (!recap) return null;
  const awards = recap.awards || (recap.closestMatchup ? [{id:'closest', match:recap.closestMatchup, labels:['Closest Matchup']}] : []);
  return <section className="home-section weekly-recap" aria-label="Weekly Recap">
    <div className="section-title"><h2>{recap.phase === 'playoffs' ? 'Playoff Recap' : 'Weekly Recap'}</h2><span>Week {recap.week} · Final</span></div>
    <TeamOfWeek embedded completedWeek season={season} week={recap.week} teams={teams} path={teamOfWeekPath} loadData={loadData}/>
    {!!recap.topPlayers?.length && <div className="content-card performances-card"><h3 className="card-title">Top Performers</h3><ol className="performances">{recap.topPlayers.map((p,i) => <li key={p.playerId}><span className="performance-rank">{i+1}</span><div className="performance-body"><strong>{p.name}</strong><span>{teams.get(p.teamId)?.name}{p.bench ? ' · Bench / IR' : ` · ${p.slot || p.position}`}</span></div><strong className="performance-points">{p.points.toFixed(2)}<small>FPTS</small></strong></li>)}</ol></div>}
    {recap.topTeam && <div className="content-card accent-card"><h3 className="card-title">Top Team{recap.leaderboard?.[1]?.points === recap.topTeam.points ? ' · Tied' : ''}</h3><div className="team-highlight"><Team team={teams.get(recap.topTeam.teamId)} link season={season}/><strong>{recap.topTeam.points.toFixed(2)}<small>FPTS</small></strong></div>
      {!!recap.leaderboard?.length && <><button className="recap-toggle" aria-expanded={expanded} onClick={()=>setExpanded(!expanded)}>{expanded ? 'Hide full leaderboard' : 'View full leaderboard'}</button>{expanded && <ol className="weekly-leaderboard" aria-label="Weekly team scoring leaderboard">{recap.leaderboard.map(row=><li key={row.teamId}><span>{row.rank}</span><Team team={teams.get(row.teamId)} link season={season}/><strong>{row.points.toFixed(2)}</strong></li>)}</ol>}</>}
    </div>}
    {awards.map(award=><div className="content-card" key={award.id}><h3 className="card-title">{award.labels.join(' · ')}</h3>{award.labels.includes('Closest Matchup') && <p className="match-label">{Math.abs(award.match.homeScore-award.match.awayScore).toFixed(2)} point margin</p>}<Match match={award.match} teams={teams}/></div>)}
    {!!recap.stories?.length && <div className="content-card weekly-stories"><h3 className="card-title">Around the League</h3><ul>{recap.stories.map(s=><li key={`${s.teamId}-${s.kind}`}><strong>{teams.get(s.teamId)?.name}</strong>{s.kind === 'firstWin' ? ' earned their first win of the season.' : ` extended their win streak to ${s.count}.`}</li>)}</ul></div>}
  </section>;
}
