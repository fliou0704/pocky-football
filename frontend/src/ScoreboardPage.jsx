import React, { useState } from 'react';
import { Match, bracketLabel } from './Match.jsx';

export function availableWeeks(league, matches) {
  // A knockout bracket needs ceil(log2(entrants)) rounds, including first-round byes.
  const configuredEnd = league.regularSeasonWeeks + Math.ceil(Math.log2(Math.max(1, league.playoffTeams)));
  const end = Math.max(configuredEnd, ...matches.map(match => match.week));
  return Array.from({length: end}, (_, i) => i + 1);
}
export function defaultWeek(league, matches, currentWeek) {
  const weeks = availableWeeks(league, matches);
  if (currentWeek && weeks.includes(currentWeek)) return currentWeek;
  if (league.complete) return 1;
  return Math.max(1, ...matches.filter(match => ['final', 'live'].includes(match.status)).map(match => match.week));
}
export default function ScoreboardPage({ league, data, currentWeek }) {
  const weeks = availableWeeks(league.league, data.matchups);
  const [week, setWeek] = useState(() => defaultWeek(league.league, data.matchups, currentWeek));
  const teams = new Map(league.standings.map(team => [team.teamId, team]));
  const matches = data.matchups.filter(match => match.week === week);
  return <section className="home-section" aria-label="Weekly scoreboard">
    <div className="section-title scoreboard-controls">
      <button type="button" aria-label="Previous week" disabled={week === weeks[0]} onClick={() => setWeek(week - 1)}>←</button>
      <label className="select-control">Week<select aria-label="Week" value={week} onChange={event => setWeek(Number(event.target.value))}>{weeks.map(value => <option key={value} value={value}>Week {value}{value > league.league.regularSeasonWeeks ? ' · Playoffs' : ''}</option>)}</select></label>
      <button type="button" aria-label="Next week" disabled={week === weeks.at(-1)} onClick={() => setWeek(week + 1)}>→</button>
    </div>
    <div className="content-card">{matches.length ? <div className="scoreboard">{matches.map((match, index) => <div key={`${week}-${index}`}>
      <p className="match-label">{match.phase === 'playoffs' ? `${bracketLabel(match.bracket)}${match.roundLabel ? ` · ${match.roundLabel}` : ''} · ` : ''}{({final: 'Final', live: 'In Progress', upcoming: 'Upcoming', bye: 'Bye'})[match.status] || 'Upcoming'}</p>
      <Match match={match} teams={teams}/>
    </div>)}</div> : <p role="status">Matchups for this week are not available in the current data.</p>}</div>
  </section>;
}
