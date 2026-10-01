export function defaultPair(teams) {
  return teams.map(team => team.teamId).sort((a, b) => a - b).slice(0, 2);
}
export function pairFile(first, second) {
  if (first === second || first == null || second == null) return null;
  return [first, second].sort((a, b) => a - b).join('-');
}
export function otherTeamOptions(teams, otherId) {
  return teams.filter(team => team.teamId !== otherId);
}
