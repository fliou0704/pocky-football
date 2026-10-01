"""Safe validation of normalized executed activity; no account identifiers."""
from collections import Counter, defaultdict
import json
from football_draft import valid_id


def semantic_key(event):
    """Exact movement identity includes time, so later re-adds remain distinct."""
    identity={k:event.get(k) for k in ('season','timestamp','type','week','faab')}
    identity['teams']=sorted([{'teamId':t['teamId'],**{k:sorted(p['playerId'] for p in t[k]) for k in ('playersAdded','playersDropped')}} for t in event.get('teams',[])],key=lambda t:t['teamId'])
    return json.dumps(identity,sort_keys=True)


def validate_events(events, team_ids):
    issues=[]; ids=Counter(e.get('id') for e in events); semantics=defaultdict(list)
    for e in events:
        semantics[semantic_key(e)].append(e['id'])
        if e.get('status')!='executed' or not e.get('timestamp') or e.get('type') not in ('draft','free_agent_add','waiver_add','drop','trade'):
            issues.append({'eventId':e['id'],'issue':'malformed_event'})
        for t in e.get('teams',[]):
            if t['teamId'] not in team_ids:issues.append({'eventId':e['id'],'issue':'invalid_team'})
            for field in ('playersAdded','playersDropped'):
                rows=t[field]
                if any(not valid_id(p['playerId']) for p in rows) or len({p['playerId'] for p in rows})!=len(rows):
                    issues.append({'eventId':e['id'],'issue':'invalid_or_duplicate_player'})
        if e['type']=='trade':
            edges=e.get('transfers',[])
            expected_add=Counter((x['toTeamId'],x['playerId']) for x in edges)
            expected_drop=Counter((x['fromTeamId'],x['playerId']) for x in edges)
            actual_add=Counter((t['teamId'],p['playerId']) for t in e['teams'] for p in t['playersAdded'])
            actual_drop=Counter((t['teamId'],p['playerId']) for t in e['teams'] for p in t['playersDropped'])
            if not edges or expected_add!=actual_add or expected_drop!=actual_drop or any(x['fromTeamId']==x['toTeamId'] or x['fromTeamId'] not in team_ids or x['toTeamId'] not in team_ids for x in edges):
                issues.append({'eventId':e['id'],'issue':'unbalanced_trade'})
    return {'duplicateEventIds':[k for k,v in ids.items() if v>1],
            'semanticDuplicateGroups':[v for v in semantics.values() if len(v)>1], 'issues':issues}


def ownership_audit(events):
    """Chronological ownership consistency. Simultaneous transfers apply atomically."""
    owners={}; anomalies=[]; counts=Counter(); readds=0; previous=set()
    for e in sorted(events,key=lambda e:(e['timestamp'],e['id'])):
        drops=[(t['teamId'],p['playerId']) for t in e['teams'] for p in t['playersDropped']]
        adds=[(t['teamId'],p['playerId']) for t in e['teams'] for p in t['playersAdded']]
        for team,player in drops:
            counts['departuresChecked']+=1
            if owners.get(player)!=team:anomalies.append({'eventId':e['id'],'playerId':player,'teamId':team,'observedOwner':owners.get(player),'issue':'drop_or_trade_origin_mismatch'})
            owners.pop(player,None)
        for team,player in adds:
            counts['arrivalsChecked']+=1
            if player in owners:anomalies.append({'eventId':e['id'],'playerId':player,'teamId':team,'observedOwner':owners[player],'issue':'already_owned_on_acquisition'})
            if player in previous and e['type']!='trade':readds+=1
            previous.add(player);owners[player]=team
    return {**counts,'reAcquisitionsChecked':readds,'anomalies':anomalies,
            'scope':'Executed movement chain including drafts; internal sanity check, not an independent roster reconstruction.'}


def compare_counters(events, source):
    counts=defaultdict(Counter); weeks=defaultdict(Counter)
    for e in events:
        for t in e['teams']:
            team=t['teamId']
            if e['type'] in ('free_agent_add','waiver_add'):
                counts[team]['acquisitions']+=len(t['playersAdded']);weeks[team][str(e['week'])]+=len(t['playersAdded'])
                counts[team]['drops']+=len(t['playersDropped'])
            elif e['type']=='drop':counts[team]['drops']+=len(t['playersDropped'])
            elif e['type']=='trade':counts[team]['trades']+=1
    rows=[]
    for team,c in sorted(source.items(),key=lambda x:int(x[0])):
        week_source=c.get('matchupAcquisitionTotals',{})
        rows.append({'teamId':int(team),'source':{k:c.get(k) for k in ('acquisitions','drops','trades')},
                     'observed':{k:counts[int(team)][k] for k in ('acquisitions','drops','trades')},
                     'acquisitionPeriodDifferences':[{'period':int(w),'source':week_source.get(w,0),'observed':weeks[int(team)][w]} for w in sorted(set(week_source)|set(weeks[int(team)]),key=int) if week_source.get(w,0)!=weeks[int(team)][w]]})
    return {'available':bool(rows),'allTotalsMatch':bool(rows) and all(r['source']==r['observed'] for r in rows),
            'dropsAndTradesMatch':bool(rows) and all(all(r['source'][k]==r['observed'][k] for k in ('drops','trades')) for r in rows),'teams':rows}


def lineup_window_audit(events, folder):
    """Roster membership must occur somewhere within its scoring-period window.

    ESPN does not timestamp archived roster snapshots precisely. This permits every
    observed owner in that period rather than assuming a Sunday/end-of-week cutoff.
    """
    from pathlib import Path
    owners={}; anomalies=[]; checked=0
    by_week=defaultdict(list)
    for e in events:
        if isinstance(e.get('week'),int):by_week[e['week']].append(e)
    paths=sorted((Path(folder)/'lineups').glob('*.json'),key=lambda p:int(p.stem))
    last=-1
    for path in paths:
        week=int(path.stem);possible=defaultdict(set)
        for period in range(last+1,week+1):
            if period==week:
                for player,team in owners.items():possible[player].add(team)
            for e in sorted(by_week[period],key=lambda e:(e['timestamp'],e['id'])):
                for t in e['teams']:
                    for p in t['playersDropped']:
                        if period==week:possible[p['playerId']].add(t['teamId'])
                        owners.pop(p['playerId'],None)
                for t in e['teams']:
                    for p in t['playersAdded']:
                        owners[p['playerId']]=t['teamId']
                        if period==week:possible[p['playerId']].add(t['teamId'])
        for team,roster in json.loads(path.read_text())['teams'].items():
            for p in roster:
                checked+=1
                if int(team) not in possible[p['playerId']]:
                    anomalies.append({'week':week,'teamId':int(team),'playerId':p['playerId'],'possibleOwners':sorted(possible[p['playerId']])})
        last=week
    return {'rosterEntriesChecked':checked,'weeksChecked':[int(p.stem) for p in paths],'anomalies':anomalies,
            'scope':'Player ownership anywhere within scoring period; precise historical snapshot timestamps are unavailable.'}


def draft_activity_audit(draft, events):
    picks=Counter((p['teamId'],p['playerId']) for p in draft['picks'])
    assignments=Counter((t['teamId'],p['playerId']) for e in events if e['type']=='draft' for t in e['teams'] for p in t['playersAdded'])
    return {'matchesAuthoritativeBoard':picks==assignments,'draftSelections':sum(picks.values()),'activityAssignments':sum(assignments.values())}
