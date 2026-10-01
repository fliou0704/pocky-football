"""Ranked football awards and scoring-period ownership stints."""
from collections import defaultdict
from datetime import datetime


def ranked(rows, limit, minimum=False):
    def stable(r):return (r['season'],r.get('week',r.get('endWeek',0)),r.get('team',{}).get('teamId',0),r.get('playerId',0),r.get('acquiredAt',''))
    ordered=sorted(rows,key=lambda r:((r['value'] if minimum else -r['value']),stable(r)))
    result=[];previous=None;rank=0
    for index,row in enumerate(ordered):
        if row['value']!=previous:rank=index+1;previous=row['value']
        if rank>limit:break
        result.append({**row,'value':float(row['value']),'rank':rank})
    return result


def player_seasons(year, scoring, complete):
    """Only complete per-game actual coverage qualifies; explicit NFL byes need no score."""
    if not complete or not scoring or scoring['coverage'].get('conflicts') or scoring['coverage'].get('lineupComparison',{}).get('scoreConflicts'):return []
    weeks=set(scoring['weeks']);games=scoring.get('games',[]);rows=[]
    for p in scoring['players']:
        points=p['pointsByWeek'];teams=set(p.get('nflTeamsByWeek',{}).values())-{'—'}
        missing=weeks-set(map(int,points))
        # A single represented NFL team and no scheduled game establishes a bye.
        if missing and (len(teams)!=1 or any(any(g['week']==w and next(iter(teams)) in (g['home'],g['away']) for g in games) for w in missing) or not games):continue
        rows.append({**{k:p[k] for k in ('playerId','name','nflTeam','position')},'season':year,
                     'value':round(sum(points[str(w)] for w in weeks if str(w) in points),2),'weeksScored':sum(str(w) in points for w in weeks)})
    return rows


def nfl_game(scoring,player,week):
    team=player.get('nflTeamsByWeek',{}).get(str(week))
    games=[g for g in scoring.get('games',[]) if g['week']==week and team in (g['home'],g['away'])]
    return games[0] if len(games)==1 else None


def pickup_rows(year,activity,scoring,teams):
    if not activity or activity['coverage'].get('status') not in ('likely_complete','independently_verified_counts') or not scoring or not scoring.get('games') or scoring['coverage'].get('conflicts') or scoring['coverage'].get('lineupComparison',{}).get('scoreConflicts'):return []
    players={p['playerId']:p for p in scoring['players']};active={};stints=[]
    for e in sorted(activity['events'],key=lambda e:(e['timestamp'],e['id'])):
        for team in e['teams']:
            for p in team['playersDropped']:
                old=active.pop(p['playerId'],None)
                if old:old['endedAt']=e['timestamp']
        for team in e['teams']:
            for p in team['playersAdded']:
                if e['type'] in ('free_agent_add','waiver_add'):
                    stint={'playerId':p['playerId'],'teamId':team['teamId'],'acquiredAt':e['timestamp'],
                           'endedAt':None,'acquisitionType':e['type'],'acquisitionWeek':e['week'],'faab':e['faab'],'eventId':e['id']}
                    active[p['playerId']]=stint;stints.append(stint)
    rows=[]
    for s in stints:
        p=players.get(s['playerId'])
        if not p or s['teamId'] not in teams:continue
        start=datetime.fromisoformat(s['acquiredAt']).timestamp()*1000
        end=datetime.fromisoformat(s['endedAt']).timestamp()*1000 if s['endedAt'] else float('inf')
        points=[];valid=True;scored_weeks=[]
        represented=set(p.get('nflTeamsByWeek',{}).values())-{'—'}
        for week in scoring['weeks']:
            game=nfl_game(scoring,p,week)
            if game is None:
                # Missing scoring in a played week cannot become an implicit zero.
                possible_teams=represented or set(p['nflTeam'].split(' / '))
                fallback=[g for g in scoring['games'] if g['week']==week and possible_teams.intersection((g['home'],g['away']))]
                if any(start<=g['kickoff']<end for g in fallback):valid=False
                continue
            if start<=game['kickoff']<end:
                value=p['pointsByWeek'].get(str(week))
                if value is None:valid=False;break
                points.append(value);scored_weeks.append(week)
        if valid and points:
            rows.append({**s,**{k:p[k] for k in ('name','nflTeam','position')},'team':teams[s['teamId']],
                         'season':year,'value':round(sum(points),2),'creditedWeeks':scored_weeks})
    return rows
