import React, { useEffect, useState } from 'react';
import PlayerPortrait from './PlayerPortrait.jsx';
import { playerHash } from './player-view.js';

export default function TeamOfWeek({ season, week, matches = [], completedWeek = false, path, loadData, embedded = false }) {
  const [loaded, setLoaded] = useState(null);
  useEffect(() => {
    let active = true;
    setLoaded(null);
    if (path && loadData) loadData(path).then(value => {
      if (active) setLoaded({ path, season, data: value?.season === season ? value : null });
    }).catch(() => { if (active) setLoaded({ path, season, data: null }); });
    else setLoaded({ path, season, data: null });
    return () => { active = false; };
  }, [path, loadData, season]);
  const completed = completedWeek || (matches.length > 0 && matches.some(m => m.status === 'final') && matches.every(m => ['final', 'bye'].includes(m.status)));
  if (!completed) return null;
  const data = loaded?.path === path && loaded?.season === season ? loaded.data : null;
  const result = data?.weeks?.[week];
  const available = result?.status === 'available' && result.lineup?.length === 9 && Number.isFinite(result.totalPoints)
    && result.lineup.every(player => Number.isFinite(player.points) && typeof player.name === 'string');
  const Heading = embedded ? 'h3' : 'h2';
  return <section className={`team-of-week ${embedded ? 'totw-embedded' : 'home-section'}`} aria-label="Team of the Week">
    <div className="totw-header">
      <div><Heading>Team of the Week</Heading><p>{season} · Week {week}</p></div>
      {available && <div className="totw-total"><span>Total Fantasy Points</span><strong>{result.totalPoints.toFixed(2)}<small> FPTS</small></strong></div>}
    </div>
    {available ? <ol className="totw-lineup">{result.lineup.map(player => <li className="totw-row" key={player.playerId}>
      <span className="totw-slot" aria-label={`Lineup position ${player.slot}`}>{player.slot}</span>
      <PlayerPortrait player={player}/>
      <div className="totw-identity">
        {player.hasProfile ? <a href={playerHash(player.playerId, season)}>{player.name}</a> : <strong>{player.name}</strong>}
        <span>{player.nflTeam || '—'} · {player.position}</span>
      </div>
      <strong className="totw-points" aria-label={`${player.points.toFixed(2)} fantasy points`}>{player.points.toFixed(2)}<small>FPTS</small></strong>
    </li>)}</ol> : <p className="totw-unavailable" role="status">{!loaded ? 'Loading Team of the Week…' : 'Team of the Week is unavailable for this completed week. Reliable scoring coverage is needed.'}</p>}
  </section>;
}
