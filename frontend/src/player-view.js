// Search and biography formatting follow Basketball Brawl's sport-agnostic pattern.
export function normalizePlayerSearch(value) {
  return String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/gi,' ').trim().toLowerCase();
}
export function searchPlayers(players, query, {position='',type='player'}={}) {
  const term=normalizePlayerSearch(query);
  return players.filter(p=>(!type||p.entityType===type)&&(!position||p.position===position)&&normalizePlayerSearch(p.name).includes(term));
}
export const playerHash = (id,season='All-Time') => `#/players/${id}${season==='All-Time'?'':`/${season}`}`;
export function ageOnDate(birthDate,now=new Date()) {
  const [year,month,day]=String(birthDate||'').split('-').map(Number);
  if(!year||!month||!day)return null;
  let age=now.getFullYear()-year;
  if(now.getMonth()+1<month||(now.getMonth()+1===month&&now.getDate()<day))age--;
  return age;
}
export function formatHeight(inches) { return inches==null?null:`${Math.floor(inches/12)}′ ${inches%12}″`; }
export function dateLabel(value) {
  if(!value)return null;
  return new Intl.DateTimeFormat('en-US',{year:'numeric',month:'short',day:'numeric',timeZone:'UTC'}).format(new Date(value.length===10?`${value}T12:00:00Z`:value));
}
export const playerPoints = value => value==null?'—':value.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
export function resolvePlayerSeason(seasons,requested) { return seasons.some(s=>String(s.season)===String(requested))?String(requested):'All-Time'; }
