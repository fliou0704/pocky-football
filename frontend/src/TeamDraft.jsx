import React, { useEffect, useState } from 'react';
import { teamDraft } from './team-view.js';

export default function TeamDraft({ season, teamId, path, loadData }) {
  const [loaded,setLoaded]=useState(null),[failed,setFailed]=useState(false);
  useEffect(()=>{let active=true;setLoaded(null);setFailed(false);loadData(path).then(value=>{if(active)setLoaded(value);}).catch(()=>{if(active)setFailed(true);});return()=>{active=false;};},[path,loadData]);
  if(failed) return <p role="status">Draft data is unavailable for this season.</p>;
  if(!loaded || loaded.season!==season) return <p role="status">Loading draft…</p>;
  const picks=teamDraft(loaded,season,teamId);
  if(!picks.length) return <p role="status">No draft selections are available for this team.</p>;
  return <div className="content-card table-card draft-card"><table className="draft-table"><caption className="sr-only">{season} team draft selections in overall pick order</caption><thead><tr><th>Rd</th><th>Pick</th><th>Player</th><th>Pos</th></tr></thead><tbody>{picks.map(p=><tr key={p.overallPick}><td>{p.round}</td><td>{p.pickInRound}<small>#{p.overallPick} overall</small></td><th scope="row">{p.playerName || 'Player unavailable'}{p.keeper && <small>Keeper</small>}</th><td>{p.position || '—'}</td></tr>)}</tbody></table></div>;
}
