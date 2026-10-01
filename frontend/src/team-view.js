export const TEAM_TABS = ['Schedule', 'Roster', 'Draft'];
const slotOrder = ['QB', 'RB', 'WR', 'TE', 'FLEX', 'D/ST', 'K', 'BE', 'IR'];
export function slotLabel(slot) {
  return ({'RB/WR/TE': 'FLEX', BN: 'BE'})[slot] || slot;
}
export function orderedRoster(roster) {
  return roster.map((player, index) => ({...player, displaySlot: slotLabel(player.slot), index}))
    .sort((a, b) => {
      const rank = player => { const index = slotOrder.indexOf(player.displaySlot); return index < 0 ? 99 : index; };
      return rank(a) - rank(b) || a.index - b.index;
    });
}
export function validTeamSeasons(manifest, teamId) {
  return manifest.seasons.filter(year => manifest.teamSeasons?.[String(teamId)]?.includes(year));
}
export function resolveTeamSeason(manifest, teamId, requested) {
  const valid = validTeamSeasons(manifest, teamId);
  return valid.includes(requested) ? requested : valid[0] ?? requested;
}

export function teamDraft(draft, season, teamId) {
  return draft?.season === season && Array.isArray(draft.picks) ? draft.picks.filter(p => p.teamId === teamId).sort((a,b) => a.overallPick - b.overallPick) : [];
}
