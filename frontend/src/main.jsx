import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { formatRecord } from './record.js';
import { assetUrl } from './asset-url.js';
import { routeFromHash, selectedTeamId } from './season-route.js';
import './style.css';

const dataBase = `${import.meta.env.BASE_URL}data/`;
async function getData(path) {
  const response = await fetch(`${dataBase}${path}`);
  if (!response.ok) throw new Error('Site data is unavailable');
  const value = await response.json();
  if (value.schemaVersion !== 1) throw new Error('Unsupported site data');
  return value;
}

function Team({ team, link = false, season }) {
  const [logoFailed, setLogoFailed] = useState(false);
  if (!team) return <span className="team-name">Bye</span>;
  const logo = assetUrl(team.logo, import.meta.env.BASE_URL);
  const content = <>
    {logo && !logoFailed ? <img src={logo} width="36" height="36" alt="" loading="lazy" onError={() => setLogoFailed(true)}/> : <span className="team-logo-fallback" aria-hidden="true">{team.name.slice(0, 1)}</span>}
    <span className="team-name">{team.name}</span>
  </>;
  return link ? <a className="team team-link" href={`#/teams/${season}/${team.teamId}`}>{content}</a> : <span className="team">{content}</span>;
}
function Section({ title, meta, children }) {
  return <section className="home-section"><div className="section-title"><h2>{title}</h2>{meta && <span>{meta}</span>}</div>{children}</section>;
}
function Card({ title, className = '', children }) {
  return <div className={`content-card ${className}`}>{title && <h3 className="card-title">{title}</h3>}{children}</div>;
}
function Match({ match, teams }) {
  const home = teams.get(match.homeTeamId), away = teams.get(match.awayTeamId);
  if (match.status === 'bye') return <div className="match"><div className="match-team"><Team team={home || away}/><strong>Bye</strong></div></div>;
  const score = value => match.status === 'upcoming' ? '—' : value?.toFixed(2) ?? '—';
  return <div className="match">
    <div className={`match-team ${match.winnerTeamId != null && match.winnerTeamId === match.awayTeamId ? 'winner' : ''}`}><Team team={away}/><strong>{score(match.awayScore)}</strong></div>
    <div className={`match-team ${match.winnerTeamId != null && match.winnerTeamId === match.homeTeamId ? 'winner' : ''}`}><Team team={home}/><strong>{score(match.homeScore)}</strong></div>
  </div>;
}
const bracketLabel = bracket => ({ championship: 'Championship bracket', placement: 'Placement', consolation: 'Consolation' })[bracket] || 'Matchup';

function Matchups({ home, teams }) {
  if (!home.currentMatchups.length) return null;
  const status = home.currentMatchups.every(match => match.status === 'final' || match.status === 'bye') ? 'Final' : home.currentMatchups.some(match => match.status === 'live') ? 'In progress' : 'Upcoming';
  return <Section title={home.state.phase === 'playoffs' ? 'Playoff Matchups' : 'Current Matchups'} meta={`Week ${home.state.currentWeek} · ${status}`}><Card>
    <div className="scoreboard">{home.currentMatchups.map((match, index) => <div key={index}>
      {home.state.phase === 'playoffs' && <p className="match-label">{bracketLabel(match.bracket)}</p>}
      <Match match={match} teams={teams}/>
    </div>)}</div>
  </Card></Section>;
}

function Recap({ recap, teams }) {
  if (!recap) return null;
  return <Section title={recap.phase === 'playoffs' ? 'Playoff Recap' : 'Weekly Recap'} meta={`Week ${recap.week} · Final`}>
    <div className="recap-highlights">
      {recap.topTeam && <Card title="Top Team" className="accent-card"><div className="team-highlight"><Team team={teams.get(recap.topTeam.teamId)}/><strong>{recap.topTeam.points.toFixed(2)}<small>FPTS</small></strong></div></Card>}
      {recap.closestMatchup && <Card title={`Closest Matchup · ${Math.abs(recap.closestMatchup.homeScore - recap.closestMatchup.awayScore).toFixed(2)} point margin`}><Match match={recap.closestMatchup} teams={teams}/></Card>}
    </div>
    {!!recap.topPlayers.length && <Card title="Top Performances" className="performances-card"><ol className="performances">{recap.topPlayers.map((player, index) => <li key={player.playerId}>
      <span className="performance-rank">{index + 1}</span><div className="performance-body"><strong>{player.name}</strong><span>{teams.get(player.teamId)?.name}{player.bench ? ' · Bench / IR' : ` · ${player.slot}`}</span></div><strong className="performance-points">{player.points.toFixed(2)}<small>FPTS</small></strong>
    </li>)}</ol></Card>}
    {recap.phase === 'playoffs' && !!recap.matches.length && <Card title="Round Results" className="round-results"><div className="scoreboard">{recap.matches.map((match, index) => <div key={index}><p className="match-label">{bracketLabel(match.bracket)}</p><Match match={match} teams={teams}/></div>)}</div></Card>}
  </Section>;
}

function Standings({ league, title = 'Standings', linkTeams = false }) {
  const complete = league.league.complete;
  const divisions = new Set(league.standings.map(team => team.division).filter(Boolean));
  const showDivision = divisions.size > 1;
  return <Section title={title} meta={complete ? 'Regular rank · playoff finish' : 'Regular season'}><div className="content-card table-card">
    <ol className="mobile-standings" aria-label="Standings">{league.standings.map(team => <li key={team.teamId}>
      <div className="mobile-team-heading"><span className="mobile-rank">{team.rank}</span><Team team={team} link={linkTeams} season={league.league.season}/><div className="mobile-record"><span className="stat-label">W–L–T</span><strong>{formatRecord(team)}</strong></div></div>
      <dl className="mobile-stats"><div><dt>PF</dt><dd>{team.pointsFor.toFixed(2)}</dd></div><div><dt>PA</dt><dd>{team.pointsAgainst.toFixed(2)}</dd></div>{showDivision && <div><dt>Division</dt><dd>{team.division}</dd></div>}{complete && <div><dt>Final finish</dt><dd>{team.finalRank ?? '—'}</dd></div>}</dl>
    </li>)}</ol>
    <table className="desktop-standings"><caption className="sr-only">Regular-season standings{complete ? ' and final playoff finish' : ''}</caption><thead><tr><th scope="col" className="rank">#</th><th scope="col">Team</th>{showDivision && <th scope="col">Division</th>}<th scope="col" className="record">W–L–T</th><th scope="col" className="numeric">Points For</th><th scope="col" className="numeric">Points Against</th>{complete && <th scope="col" className="numeric">Final</th>}</tr></thead><tbody>
      {league.standings.map(team => <tr key={team.teamId}><td className="rank">{team.rank}</td><th scope="row"><Team team={team} link={linkTeams} season={league.league.season}/></th>{showDivision && <td>{team.division || '—'}</td>}<td className="record">{formatRecord(team)}</td><td className="numeric">{team.pointsFor.toFixed(2)}</td><td className="numeric">{team.pointsAgainst.toFixed(2)}</td>{complete && <td className="numeric">{team.finalRank ?? '—'}</td>}</tr>)}
    </tbody></table>
  </div></Section>;
}

function Header({ name, page }) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  return <header className="masthead"><div className="header-inner">
    <a className="brand" href="#/" onClick={close}><span className="brand-mark" aria-hidden="true"/>{name}</a>
    <button className="menu-button" type="button" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} aria-controls="site-menu" onClick={() => setOpen(!open)}><span className={`menu-icon ${open ? 'open' : ''}`}><span/><span/><span/></span></button>
    <nav id="site-menu" className={`site-menu ${open ? 'open' : ''}`} aria-label="Main navigation">
      <a href="#/" aria-current={page === 'home' ? 'page' : undefined} onClick={close}>Home</a>
      <a href="#/standings" aria-current={page === 'standings' ? 'page' : undefined} onClick={close}>Standings</a>
      <a href="#/teams" aria-current={page === 'teams' ? 'page' : undefined} onClick={close}>Teams</a><span aria-disabled="true">H2H</span><span aria-disabled="true">Record Book</span><span aria-disabled="true">Players</span>
    </nav>
  </div></header>;
}

const labelBracket = bracket => ({championship: 'Championship', placement: 'Placement', consolation: 'Consolation'})[bracket] || 'Playoffs';
const points = value => value == null ? '—' : value.toFixed(2);

function TeamPage({ league, teamsData, selectedId, onTeamChange }) {
  const all = league.standings;
  const selected = all.find(team => team.teamId === selectedTeamId(all, selectedId));
  const data = teamsData.teams[String(selected.teamId)];
  const completed = data.weeks.filter(week => week.phase === 'regular' && week.status === 'final');
  return <>
    <div className="team-identity content-card"><Team team={selected}/><div className="team-identity-copy"><p className="page-eyebrow">{selected.division ? `${selected.division} Division` : 'Fantasy team'}</p><h2>{selected.name}</h2>{selected.owner && <p>Owner · {selected.owner}</p>}</div>
      <label className="select-control">Team<select aria-label="Team" value={selected.teamId} onChange={event => onTeamChange(Number(event.target.value))}>{all.map(team => <option key={team.teamId} value={team.teamId}>{team.name}</option>)}</select></label></div>
    <Section title="Overview" meta={`${league.league.season} season`}><div className="content-card"><dl className="team-overview">
      <div><dt>Record</dt><dd>{formatRecord(selected)}</dd></div><div><dt>Regular rank</dt><dd>{selected.rank}</dd></div>{league.league.complete && <div><dt>Final finish</dt><dd>{selected.finalRank ?? '—'}</dd></div>}
      <div><dt>Points for</dt><dd>{points(selected.pointsFor)}</dd></div><div><dt>Points against</dt><dd>{points(selected.pointsAgainst)}</dd></div>
      <div><dt>Average / game</dt><dd>{points(data.averageScore)}</dd></div><div><dt>High week</dt><dd>{points(data.highScore)}</dd></div><div><dt>Low week</dt><dd>{points(data.lowScore)}</dd></div>
    </dl></div></Section>
    <Section title="Weekly Performance" meta="Regular season and playoffs"><div className="content-card table-card">
      <div className="weekly-table-wrap"><table className="weekly-table"><caption className="sr-only">Weekly performance for {selected.name}</caption><thead><tr><th>Week</th><th>Opponent</th><th>Result</th><th className="numeric">Score</th><th className="numeric">Opp.</th><th>Record</th><th className="numeric">Score rank</th></tr></thead><tbody>
      {data.weeks.map(week => <tr key={week.week} className={week.phase === 'playoffs' ? 'playoff-row' : ''}><td><strong>{week.week}</strong>{week.phase === 'playoffs' && <small>{labelBracket(week.bracket)}</small>}</td><th scope="row">{week.status === 'bye' ? 'Bye' : all.find(team => team.teamId === week.opponentTeamId)?.name || '—'}</th><td>{week.result === '—' && week.status === 'live' ? 'Live' : week.result}</td><td className="numeric">{points(week.score)}</td><td className="numeric">{points(week.opponentScore)}</td><td>{week.cumulativeRecord ? formatRecord(week.cumulativeRecord) : '—'}</td><td className="numeric">{week.scoreRank ?? '—'}</td></tr>)}
      </tbody></table></div><ol className="weekly-mobile">{data.weeks.map(week => <li key={week.week}><div><strong>Week {week.week}{week.phase === 'playoffs' ? ` · ${labelBracket(week.bracket)}` : ''}</strong><span>{week.result === '—' && week.status === 'live' ? 'Live' : week.result}</span></div><p>{week.status === 'bye' ? 'Bye' : `vs ${all.find(team => team.teamId === week.opponentTeamId)?.name || '—'}`}</p><div><strong>{points(week.score)}{week.status === 'bye' ? '' : ` – ${points(week.opponentScore)}`}</strong><span>{week.scoreRank ? `#${week.scoreRank} weekly score` : week.cumulativeRecord ? formatRecord(week.cumulativeRecord) : ''}</span></div></li>)}</ol>
      </div></Section>
    {data.roster && <Section title="Current Roster" meta="Live season membership"><div className="content-card">{[['starter', 'Starters'], ['bench', 'Bench'], ['ir', 'Injured Reserve']].map(([group, title]) => { const rows = data.roster.filter(player => player.group === group); return rows.length > 0 && <div className="roster-group" key={group}><h3>{title}</h3><ul>{rows.map(player => <li key={player.playerId}><div><strong>{player.name}</strong><small>{player.nflTeam} · {player.position} · {player.slot}{player.injuryStatus && player.injuryStatus !== 'ACTIVE' ? ` · ${player.injuryStatus}` : ''}</small></div><strong>{points(player.seasonPoints)}<small>Season FPTS</small></strong></li>)}</ul></div>; })}</div></Section>}
    {league.league.complete && <p className="archive-note">Historical rosters are omitted because a season-end roster does not represent each week's lineup. Weekly results come from that season's matchups.</p>}
  </>;
}

function App() {
  const [manifest, setManifest] = useState(null), [data, setData] = useState(null), [home, setHome] = useState(null), [error, setError] = useState(null);
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => { const update = () => setHash(window.location.hash); window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update); }, []);
  useEffect(() => { let active = true; getData('site.json').then(value => { if (active) setManifest(value); }).catch(problem => { if (active) setError(problem.message); }); return () => { active = false; }; }, []);
  const currentSeason = manifest?.seasons?.[0];
  const route = routeFromHash(hash, currentSeason);
  const season = manifest?.seasons?.includes(route.season) ? route.season : currentSeason;
  useEffect(() => {
    if (!manifest || !season) return;
    let active = true; setData(null); setError(null);
    const prefix = manifest.leaguePath.replace(/\d+\/league\.json$/, `${season}/`);
    Promise.all([getData(`${prefix}league.json`), route.page === 'teams' ? getData(`${prefix}teams.json`) : Promise.resolve(null),
                 season === currentSeason ? getData(`${prefix}home.json`) : Promise.resolve(null)])
      .then(([league, teamsData, homeData]) => { if (active) { setData({league, teamsData}); if (homeData) setHome(homeData); document.title = league.league.name; } })
      .catch(problem => { if (active) setError(problem.message); });
    return () => { active = false; };
  }, [manifest, season, route.page, currentSeason]);
  useEffect(() => {
    if (route.page === 'teams' && season != null && data && data.league.league.season === season &&
        !data.league.standings.some(team => team.teamId === route.teamId)) {
      window.location.hash = `#/teams/${season}/${data.league.standings[0].teamId}`;
    }
  }, [data, route.page, route.teamId, season]);
  if (error) return <main className="page-shell"><p role="alert">{error}. Regenerate the league data and reload.</p></main>;
  if (!data || !manifest || route.page === 'home' && !home) return <main className="page-shell"><p role="status">Loading league…</p></main>;
  const {league, teamsData} = data;
  const teams = new Map(league.standings.map(team => [team.teamId, team]));
  const page = route.page;
  const meta = page === 'home' ? home.state.phase === 'offseason' ? 'Season complete' : `Week ${home.state.currentWeek}` : league.league.complete ? 'Season complete' : 'Current season';
  const changeSeason = year => { window.location.hash = page === 'teams' ? `#/teams/${year}/${route.teamId || ''}` : `#/standings/${year}`; };
  return <><a className="skip" href="#main">Skip to content</a><Header name={league.league.name} page={page}/><main id="main" className="page-shell homepage">
    <header className="page-header"><div><p className="page-eyebrow">{league.league.name}</p><h1>{page === 'home' ? `${league.league.season} Season` : page === 'teams' ? 'Teams' : 'Standings'}</h1></div>
      {page === 'home' ? <p className="page-meta">{meta}</p> : <label className="select-control">Season<select aria-label="Season" value={season} onChange={event => changeSeason(Number(event.target.value))}>{manifest.seasons.map(year => <option key={year} value={year}>{year}</option>)}</select></label>}</header>
    {page === 'standings' ? <Standings league={league} linkTeams/> : page === 'teams' ? teamsData && <TeamPage league={league} teamsData={teamsData} selectedId={route.teamId} onTeamChange={id => { window.location.hash = `#/teams/${season}/${id}`; }}/> : <><Matchups home={home} teams={teams}/><Recap recap={home.recap} teams={teams}/><Standings league={league} title={home.state.phase === 'offseason' ? 'Final Regular-Season Standings' : 'Standings'} linkTeams/></>}
  </main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
