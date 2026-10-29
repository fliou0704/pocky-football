// Resolve Python-generated references; all analytical metrics are supplied by Python.
export function hydrateDraft(data) {
  const picks = new Map(Object.values(data.seasons).flatMap(s => s.picks.map(p => [`${p.season}/${p.overallPick}`, p])));
  function resolve(value) {
    if (Array.isArray(value)) return value.map(resolve);
    if (value && typeof value === 'object') {
      if (value.pickRef) return picks.get(value.pickRef.join('/'));
      return Object.fromEntries(Object.entries(value).map(([key, v]) => {
        // Manager aggregates store bare references; other analyses use pickRef.
        // Evidence tables need canonical picks, not either reference shape.
        if (key === 'evidence') return [key, (Array.isArray(v) ? v : []).map(ref => {
          if (!ref) return null;
          const pick = picks.get((ref.pickRef || [ref.season, ref.overallPick]).join('/'));
          return pick || (ref.playerId != null ? resolve(ref) : null);
        }).filter(Boolean)];
        return [key, resolve(v)];
      }));
    }
    return value;
  }
  return resolve(data);
}

// `teams` is the established single-season aggregate contract, including snapshots
// cached before PR #18 added `overallPerformance`. Do not apply Summary eligibility.
export function seasonPerformanceRows(season) {
  const rows = Array.isArray(season?.teams) && season.teams.length
    ? season.teams : Array.isArray(season?.overallPerformance) ? season.overallPerformance : [];
  return [...rows].sort((a, b) => {
    const first = a.averageRoundRank, second = b.averageRoundRank;
    const firstKnown = Number.isFinite(first), secondKnown = Number.isFinite(second);
    if (firstKnown !== secondKnown) return firstKnown ? -1 : 1;
    return (firstKnown ? first - second : 0) || String(a.managerId).localeCompare(String(b.managerId));
  });
}
