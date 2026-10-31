// A single verified overlay supplies Home, Scoreboard and current rosters.
// No timers: browser auto-refresh is intentionally a later stage.
export async function contentHash(value) {
  const bytes = new TextEncoder().encode(value);
  return Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
}

export async function loadLive(load) {
  try {
    const meta = await load('pocky-football/refresh.json', {cache:'no-store'});
    if (meta.mode !== 'live') return null;
    const path = 'pocky-football/live.json';
    const text = await load(`${path}?generation=${meta.generationId}`, {raw:true, cache:'no-store'});
    const live = JSON.parse(text);
    if (live.baseGenerationId !== meta.baseGenerationId || await contentHash(text) !== meta.liveContentHash) return null;
    return {meta, live};
  } catch { return null; } // A failed optional overlay never breaks the validated full site.
}

export async function loadCurrent(paths, load, bundle) {
  if (bundle) {
    try {
      const texts = await Promise.all(paths.map(path => path ? load(`${path}?generation=${bundle.meta.generationId}`, {raw:true, cache:'no-store'}) : null));
      const matches = await Promise.all(texts.map((text,i) => text == null || contentHash(text).then(hash => hash === bundle.live.sourceFileHashes[paths[i]])));
      if (matches.every(Boolean)) return texts.map((text,i) => text == null ? null : applyLive(paths[i], JSON.parse(text), bundle.live));
    } catch { /* retain the full-snapshot path if any source/overlay is unavailable */ }
  }
  return Promise.all(paths.map(path => path ? load(path) : null));
}

export function applyLive(path, value, live) {
  const prefix = `pocky-football/${live.season}/`;
  if (!path.startsWith(prefix)) return value;
  if (path === `${prefix}home.json` && value.state.currentWeek === live.week) {
    return {...value, currentMatchups:live.matchups};
  }
  if (path === `${prefix}lineups/${live.week}.json`) return live.lineups;
  if (path !== `${prefix}teams.json`) return value;
  const scores = new Map(live.matchups.flatMap(m => [
    [m.homeTeamId, {match:m, score:m.homeScore, opponentScore:m.awayScore}],
    [m.awayTeamId, {match:m, score:m.awayScore, opponentScore:m.homeScore}],
  ]));
  return {...value, matchups:value.matchups.map(m => m.week === live.week ? live.matchups.find(n => n.homeTeamId === m.homeTeamId && n.awayTeamId === m.awayTeamId) || m : m),
    teams:Object.fromEntries(Object.entries(value.teams).map(([tid, team]) => {
      const current = scores.get(Number(tid));
      const roster = live.lineups.teams[tid]?.map(p => ({...team.roster.find(old => old.playerId === p.playerId), ...p, liveWeek:live.week,
        group:p.slot === 'IR' ? 'ir' : ['BE','BN'].includes(p.slot) ? 'bench' : 'starter'}));
      return [tid, {...team, roster:roster || team.roster,
        formerPlayers:team.formerPlayers?.filter(p => !roster?.some(active => active.playerId === p.playerId)),
        weeks:team.weeks.map(w => w.week === live.week && current ? {...w, score:current.score, opponentScore:current.opponentScore,
        status:current.match.status, result:current.match.status !== 'final' ? '—' : current.match.winnerTeamId == null ? 'T' : current.match.winnerTeamId === Number(tid) ? 'W' : 'L'} : w)}];
    }))};
}
