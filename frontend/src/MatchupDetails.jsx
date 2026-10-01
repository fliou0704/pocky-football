import React, { useEffect, useState } from 'react';
import { orderedRoster } from './team-view.js';

export default function MatchupDetails({ row, manifest, loadData, cache, Team }) {
  const [detail, setDetail] = useState(null), [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    const path = `${manifest.lineupPath}${row.season}/lineups/${row.week}.json`;
    if (!cache.current.has(path)) cache.current.set(path, loadData(path));
    cache.current.get(path).then(value => { if (active) setDetail(value); }).catch(() => { cache.current.delete(path); if (active) setError(true); });
    return () => { active = false; };
  }, [row.season, row.week, manifest.lineupPath, loadData, cache]);
  if (error) return <p className="h2h-detail-message" role="status">Matchup lineup detail is unavailable.</p>;
  if (!detail) return <p className="h2h-detail-message" role="status">Loading weekly lineups…</p>;
  return <div className="h2h-lineups">{[row.teamA, row.teamB].map(team => {
    const players = detail.teams?.[String(team.teamId)];
    return <section key={team.teamId} className="h2h-lineup" aria-label={`${team.name} weekly lineup`}><header><Team team={team}/></header>
      {!Array.isArray(players) || !players.length ? <p>No lineup data for this team.</p> : <ul>{orderedRoster(players).map((player,index) => <li key={`${player.playerId}-${index}`}><span className="lineup-slot">{player.displaySlot}</span><div><strong>{player.name}</strong><small>{player.nflTeam} · {player.position}</small></div><strong>{player.points == null ? '—' : player.points.toFixed(2)}</strong></li>)}</ul>}
    </section>;
  })}</div>;
}

