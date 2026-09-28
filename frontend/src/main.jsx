import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { formatRecord } from './record.js';
import { assetUrl } from './asset-url.js';
import './style.css';

const dataBase = `${import.meta.env.BASE_URL}data/`;
async function getData(path) {
  const response = await fetch(`${dataBase}${path}`);
  if (!response.ok) throw new Error('Site data is unavailable');
  const value = await response.json();
  if (value.schemaVersion !== 1) throw new Error('Unsupported site data');
  return value;
}

function Team({ team }) {
  const [logoFailed, setLogoFailed] = useState(false);
  if (!team) return <span className="team-name">Bye</span>;
  const logo = assetUrl(team.logo, import.meta.env.BASE_URL);
  return <span className="team">
    {logo && !logoFailed ? <img src={logo} width="36" height="36" alt="" loading="lazy" onError={() => setLogoFailed(true)}/> : <span className="team-logo-fallback" aria-hidden="true">{team.name.slice(0, 1)}</span>}
    <span className="team-name">{team.name}</span>
  </span>;
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

function Standings({ league, title = 'Standings' }) {
  return <Section title={title} meta="Regular season"><div className="content-card table-card">
    <ol className="mobile-standings" aria-label="Standings">{league.standings.map(team => <li key={team.teamId}>
      <div className="mobile-team-heading"><span className="mobile-rank">{team.rank}</span><Team team={team}/><div className="mobile-record"><span className="stat-label">W–L–T</span><strong>{formatRecord(team)}</strong></div></div>
      <dl className="mobile-stats"><div><dt>PF</dt><dd>{team.pointsFor.toFixed(2)}</dd></div><div><dt>PA</dt><dd>{team.pointsAgainst.toFixed(2)}</dd></div></dl>
    </li>)}</ol>
    <table className="desktop-standings"><caption className="sr-only">Regular-season standings</caption><thead><tr><th scope="col" className="rank">#</th><th scope="col">Team</th><th scope="col" className="record">W–L–T</th><th scope="col" className="numeric">Points For</th><th scope="col" className="numeric">Points Against</th></tr></thead><tbody>
      {league.standings.map(team => <tr key={team.teamId}><td className="rank">{team.rank}</td><th scope="row"><Team team={team}/></th><td className="record">{formatRecord(team)}</td><td className="numeric">{team.pointsFor.toFixed(2)}</td><td className="numeric">{team.pointsAgainst.toFixed(2)}</td></tr>)}
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
      <span aria-disabled="true">Teams</span><span aria-disabled="true">H2H</span><span aria-disabled="true">Record Book</span><span aria-disabled="true">Players</span>
    </nav>
  </div></header>;
}

function App() {
  const [data, setData] = useState(null), [error, setError] = useState(null);
  const [page, setPage] = useState(window.location.hash === '#/standings' ? 'standings' : 'home');
  useEffect(() => {
    const route = () => setPage(window.location.hash === '#/standings' ? 'standings' : 'home');
    window.addEventListener('hashchange', route);
    let active = true;
    getData('site.json').then(async manifest => {
      const league = await getData(manifest.leaguePath);
      const home = await getData(manifest.leaguePath.replace(/league\.json$/, 'home.json'));
      return { league, home };
    }).then(result => { if (active) { document.title = result.league.league.name; setData(result); } }).catch(problem => { if (active) setError(problem.message); });
    return () => { active = false; window.removeEventListener('hashchange', route); };
  }, []);
  if (error) return <main className="page-shell"><p role="alert">{error}. Regenerate the league data and reload.</p></main>;
  if (!data) return <main className="page-shell"><p role="status">Loading league…</p></main>;
  const { league, home } = data;
  const teams = new Map(league.standings.map(team => [team.teamId, team]));
  const meta = home.state.phase === 'offseason' ? 'Season complete' : `Week ${home.state.currentWeek}`;
  return <><a className="skip" href="#main">Skip to content</a><Header name={league.league.name} page={page}/><main id="main" className="page-shell homepage">
    <header className="page-header"><div><p className="page-eyebrow">{league.league.name}</p><h1>{page === 'standings' ? 'Standings' : `${league.league.season} Season`}</h1></div><p className="page-meta">{meta}</p></header>
    {page === 'standings' ? <Standings league={league}/> : <><Matchups home={home} teams={teams}/><Recap recap={home.recap} teams={teams}/><Standings league={league} title={home.state.phase === 'offseason' ? 'Final Regular-Season Standings' : 'Standings'}/></>}
  </main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
