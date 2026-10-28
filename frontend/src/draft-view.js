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
