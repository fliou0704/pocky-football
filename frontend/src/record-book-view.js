export function recordView(data, year) {
  return data.seasons[String(year)] || data.allTime;
}
export function recordValue(record, holder) {
  if (record.unit === 'record') return `${holder.wins}-${holder.losses}${holder.ties ? `-${holder.ties}` : ''} · ${(holder.value * 100).toFixed(1)}%`;
  if (record.unit === 'games') return `${holder.value} games`;
  return `${holder.value.toFixed(2)} FPTS`;
}
export function rankedEntryKey(holder) {
  return [holder.season,holder.week || holder.endWeek || '',holder.team?.teamId || '',holder.playerId || '',holder.acquiredAt || ''].join('-');
}
