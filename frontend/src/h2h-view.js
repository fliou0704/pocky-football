export function pairFile(first, second) {
  if (first === second || first == null || second == null) return null;
  return [first, second].sort((a, b) => a - b).join('-');
}
export function otherTeamOptions(teams, otherId) {
  return teams.filter(team => team.teamId !== otherId);
}
export function recordText(summary) {
  return summary.ties ? `${summary.wins} – ${summary.ties} – ${summary.losses}` : `${summary.wins} – ${summary.losses}`;
}
export function recordCaption(summary) {
  return summary.ties ? 'Team A wins · Ties · Team B wins' : 'Team A wins · Team B wins';
}
export function h2hHash(mode, first, second) {
  const query = new URLSearchParams();
  if (first != null) query.set('a', first);
  if (second != null) query.set('b', second);
  return `#/h2h/${mode}${query.size ? `?${query}` : ''}`;
}
export function nextExpanded(current, clicked) { return current === clicked ? null : clicked; }
export function loadedView(loaded, key) { return loaded?.key === key ? loaded.data : null; }
