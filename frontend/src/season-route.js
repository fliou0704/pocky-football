export function routeFromHash(hash, currentSeason) {
  const parts = hash.replace(/^#\/?/, '').split('/');
  const page = ['standings', 'teams'].includes(parts[0]) ? parts[0] : 'home';
  const year = Number(parts[1]);
  return { page, season: Number.isInteger(year) && year > 2000 ? year : currentSeason,
           teamId: page === 'teams' && /^\d+$/.test(parts[2] || '') ? Number(parts[2]) : null };
}

export function selectedTeamId(standings, requestedId) {
  return standings.find(team => team.teamId === requestedId)?.teamId ?? standings[0]?.teamId ?? null;
}
