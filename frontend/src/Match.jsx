import React, { useState } from 'react';
import { assetUrl } from './asset-url.js';
export function Team({ team, link = false, season }) {
  const [failedLogo, setFailedLogo] = useState(null);
  if (!team) return <span className="team-name">Bye</span>;
  const logo = assetUrl(team.logo, import.meta.env.BASE_URL);
  const content = <>
    {logo && failedLogo !== logo ? <img src={logo} width="36" height="36" alt="" loading="lazy" onError={() => setFailedLogo(logo)}/> : <span className="team-logo-fallback" aria-hidden="true">{team.name.slice(0, 1)}</span>}
    <span className="team-name">{team.name}</span>
  </>;
  return link ? <a className="team team-link" href={`#/teams/${season}/${team.teamId}`}>{content}</a> : <span className="team">{content}</span>;
}
export function Match({ match, teams }) {
  const home = teams.get(match.homeTeamId), away = teams.get(match.awayTeamId);
  if (match.status === 'bye') return <div className="match"><div className="match-team"><Team team={home || away}/><strong>Bye</strong></div></div>;
  const outcome = id => match.status !== 'final' ? '' : match.winnerTeamId == null ? ' · Tie' : match.winnerTeamId === id ? ' · W' : ' · L';
  const score = value => match.status === 'upcoming' ? '—' : value?.toFixed(2) ?? '—';
  return <div className="match">
    <div className={`match-team ${match.winnerTeamId != null && match.winnerTeamId === match.awayTeamId ? 'winner' : ''}`}><Team team={away}/><strong>{score(match.awayScore)}<span className="sr-only">{outcome(match.awayTeamId)}</span></strong></div>
    <div className={`match-team ${match.winnerTeamId != null && match.winnerTeamId === match.homeTeamId ? 'winner' : ''}`}><Team team={home}/><strong>{score(match.homeScore)}<span className="sr-only">{outcome(match.homeTeamId)}</span></strong></div>
  </div>;
}
export const bracketLabel = bracket => ({ championship: 'Championship bracket', placement: 'Placement', consolation: 'Consolation' })[bracket] || 'Matchup';
