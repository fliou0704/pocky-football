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

export function resolveTeamBranding(team, season = 'All-Time', config = configuration) {
  const periods = config.teams[String(team.teamId)] || [];
  const allTime = season === 'All-Time' || season == null;
  const period = [...periods].sort((a, b) => b.startSeason - a.startSeason)
    .find(p => allTime || (Number(season) >= p.startSeason && Number(season) <= (p.endSeason ?? Infinity)));
  const automaticLogo = team.logo || null;
  const logoOverride = period?.logoOverride || null;
  return {
    primaryColor: period?.primaryColor || DEFAULT_TEAM_COLOR,
    logoOverride,
    logo: logoOverride || automaticLogo,
    logoCandidates: [...new Set([logoOverride, automaticLogo].filter(Boolean))],
    initials: (team.name || '').slice(0, 1),
  };
}
