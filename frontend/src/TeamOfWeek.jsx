import React, { useEffect, useState } from 'react';
import { Team } from './Match.jsx';

export default function TeamOfWeek({ season, week, matches, teams, path, loadData }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    let active = true;
    setData(null);
    if (path && loadData) loadData(path).then(value => { if (active && value.season === season) setData(value); }).catch(() => {});
    return () => { active = false; };
  }, [path, loadData, season]);
  const completed = matches.length > 0 && matches.some(m => m.status === 'final') && matches.every(m => ['final', 'bye'].includes(m.status));
  if (!completed) return null;
  const result = data?.weeks?.[week];
  const available = result?.status === 'available' && result.lineup?.length === 9;
  return <section className="home-section team-of-week" aria-label="Team of the Week">
    <div className="section-title"><h2>Team of the Week</h2><span>{season} · Week {week}</span></div>
    <div className="content-card">
      {available ? <>
        <h3 className="card-title">{result.totalPoints.toFixed(2)} FPTS</h3>
        <ol className="totw-lineup">{result.lineup.map(player => <li className="lineup-row" key={player.playerId}>
          <span className="lineup-slot">{player.slot}</span>
          <div className="lineup-player"><strong>{player.name}</strong><small>{player.position} · {player.nflTeam}</small>
            {teams.has(player.teamId) ? <Team team={teams.get(player.teamId)}/> : <small>Free agent · not on recorded weekly rosters</small>}
          </div>
          <strong>{player.points.toFixed(2)}<small>FPTS</small></strong>
        </li>)}</ol>
        <p className="archive-note">{result.pool}</p>
      </> : <p>Team of the Week data is unavailable for this completed week.</p>}
    </div>
  </section>;
}
