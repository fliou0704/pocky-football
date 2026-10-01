export function routeFromHash(hash, currentSeason) {
  const [pathname, query] = hash.replace(/^#\/?/, '').split('?');
  const params = new URLSearchParams(query);
  const id = key => /^[1-9]\d*$/.test(params.get(key) || '') ? Number(params.get(key)) : null;
  const parts = pathname.split('/');
  const page = ['standings', 'teams', 'h2h'].includes(parts[0]) ? parts[0] : 'home';
  const year = Number(parts[1]);
  return { page, ...(page === 'h2h' ? {mode: parts[1] === 'theoretical' ? 'theoretical' : 'historical', firstId: id('a'), secondId: id('b')} : {}), season: Number.isInteger(year) && year > 2000 ? year : currentSeason,
           teamId: page === 'teams' && /^\d+$/.test(parts[2] || '') ? Number(parts[2]) : null };
}

export function selectedTeamId(standings, requestedId) {
  return standings.find(team => team.teamId === requestedId)?.teamId ?? standings[0]?.teamId ?? null;
}
