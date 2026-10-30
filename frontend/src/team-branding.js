import configuration from './team-branding.json' with { type: 'json' };

export const DEFAULT_TEAM_COLOR = '#1a9f54';

// Inclusive ranges; omitted endSeason continues indefinitely. Fields do not
// inherit across periods: omitting a logo always retains the automatic logo.
export function validateBranding(config) {
  if (!config?.teams || typeof config.teams !== 'object' || Array.isArray(config.teams)) throw new Error('Branding must contain a teams map');
  for (const [id, periods] of Object.entries(config.teams)) {
    if (!/^[1-9]\d*$/.test(id) || !Array.isArray(periods)) throw new Error('Branding needs positive ESPN team IDs and arrays of periods');
    let previousEnd = 0;
    for (const period of [...periods].sort((a, b) => a.startSeason - b.startSeason)) {
      if (!period || Object.keys(period).some(key => !['startSeason', 'endSeason', 'primaryColor', 'logoOverride'].includes(key))) throw new Error('Unknown branding field');
      const end = period.endSeason ?? Infinity;
      if (!Number.isInteger(period.startSeason) || period.startSeason < 2000 || (end !== Infinity && !Number.isInteger(end)) || end < period.startSeason || period.startSeason <= previousEnd) throw new Error('Branding ranges must be valid, nonoverlapping seasons');
      if (period.primaryColor !== undefined && !/^#[0-9a-f]{6}$/i.test(period.primaryColor)) throw new Error('primaryColor must be a six-digit hex color');
      if (period.logoOverride !== undefined && !/^team-logos\/[A-Za-z0-9_-]+\.(png|jpe?g|webp|svg)$/i.test(period.logoOverride)) throw new Error('logoOverride must be a local team-logos image path');
      previousEnd = end;
    }
  }
  return config;
}

validateBranding(configuration);

export function resolveTeamBranding(team, season = 'All-Time', config = configuration, catalog = {}, logoSeason = season) {
  const periods = config.teams[String(team.teamId)] || [];
  const allTime = season === 'All-Time' || season == null;
  const period = [...periods].sort((a, b) => b.startSeason - a.startSeason)
    .find(p => allTime || (Number(season) >= p.startSeason && Number(season) <= (p.endSeason ?? Infinity)));
  const automaticLogo = team.logo || null;
  const seasons = catalog.seasons || {};
  let archived;
  if (Number.isInteger(Number(logoSeason))) archived = seasons[String(logoSeason)]?.[String(team.teamId)];
  else {
    const records = Object.entries(seasons).sort(([a],[b])=>Number(b)-Number(a)).map(([,teams])=>teams[String(team.teamId)]).filter(Boolean);
    // Unknown season is not evidence of current franchise identity. Preserve a
    // known source match, otherwise keep the supplied source/badge.
    archived = records.find(record => automaticLogo && [record.asset, record.sourceUrl].includes(automaticLogo));
  }
  const logoOverride = period?.logoOverride || null;
  return {
    primaryColor: period?.primaryColor || DEFAULT_TEAM_COLOR,
    logoOverride,
    logo: logoOverride || archived?.asset || automaticLogo,
    logoCandidates: [...new Set([logoOverride, archived?.asset, automaticLogo].filter(Boolean))],
    logoSources: {...(automaticLogo ? {[automaticLogo]:'source-url'} : {}),
      ...(archived?.asset ? {[archived.asset]:archived.provenance} : {}),
      ...(logoOverride ? {[logoOverride]:'manual-override'} : {})},
    provenance: logoOverride ? 'manual-override' : archived?.provenance || (automaticLogo ? 'source-url' : 'generated-badge'),
    initials: (team.abbreviation || archived?.abbreviation || (team.name || '').split(/\s+/).map(word=>word.replace(/[^\p{L}\p{N}]/gu,'')[0] || '').join('')).slice(0,3).toUpperCase() || 'PF',
  };
}
