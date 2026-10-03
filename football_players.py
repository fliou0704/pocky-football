"""Compact Players presentation contracts from audited normalized league snapshots."""
import json
from collections import defaultdict
from pathlib import Path
from football_exporter import write_json, ROOT
from football_record_book import STARTERS, numeric, identity
from football_record_rankings import nfl_game
from football_player_games import COLUMNS, game_state, season_stats

PROFILE_FIELDS = ('espnId','entityType','name','position','positionGroup','nflTeam','jerseyNumber',
                  'heightInches','weightPounds','birthDate','college','headshot','logo','rookieSeason','lastSeason','nflDraft')


def summary(rows):
    scored = [r for r in rows if r['status'] == 'final' and numeric(r['points'])]
    starters = [(r, s) for r in rows if r['status'] == 'final' for s in r['rosters']
                if s['slot'] in STARTERS and numeric(s['points'])]
    best = max(scored, key=lambda r: (r['points'], -r['season'], -r['week']), default=None)
    return {'weeks': len(scored), 'points': round(sum(r['points'] for r in scored), 2) if scored else None,
            'average': round(sum(r['points'] for r in scored)/len(scored), 2) if scored else None,
            'high': {k:best[k] for k in ('season','week','points')} if best else None,
            'starts':len(starters), 'starterPoints':round(sum(s['points'] for _,s in starters),2) if starters else None}


def build_players(output, slug, years):
    folder = Path(output)/slug
    metadata = json.loads((folder/'players.json').read_text())
    profiles = {p['espnId']: {k:p.get(k) for k in PROFILE_FIELDS if k in p} for p in metadata['players']}
    histories = {pid:[] for pid in profiles}; manifest = []
    for year in sorted(years, reverse=True):
        season = folder/str(year)
        league=json.loads((season/'league.json').read_text()); teams=json.loads((season/'teams.json').read_text())
        draft=json.loads((season/'draft.json').read_text()); activity=json.loads((season/'activity.json').read_text())
        scoring=json.loads((season/'player-scoring.json').read_text())
        nfl_games=json.loads((season/'player-games.json').read_text())
        team_map={t['teamId']:identity(t) for t in league['standings']}
        slots=defaultdict(lambda:defaultdict(list)); present=set(); owners=defaultdict(dict)
        def seen(pid, tid, evidence):
            if pid not in profiles: raise ValueError('League player absent from metadata; regenerate identity foundation')
            present.add(pid)
            if tid not in team_map: raise ValueError('Unknown fantasy team')
            owners[pid].setdefault(tid, {'team':team_map[tid], 'weeks':set(), 'evidence':set()})['evidence'].add(evidence)
        for path in sorted((season/'lineups').glob('*.json'),key=lambda p:int(p.stem)):
            data=json.loads(path.read_text()); week=data['week']
            for tid, lineup in data['teams'].items():
                for row in lineup:
                    pid=row['playerId'];seen(pid,int(tid),'weekly_roster')
                    owners[pid][int(tid)]['weeks'].add(week)
                    slots[pid][week].append({'team':team_map[int(tid)], 'slot':row['slot'], 'points':row.get('points'),
                                            'nflTeam':row.get('nflTeam'), 'nflOpponent':row.get('nflOpponent')})
        snapshot=defaultdict(list)
        for tid,team in teams['teams'].items():
            for row in team['roster']:
                seen(row['playerId'],int(tid),'final_roster' if league['league']['complete'] else 'current_roster')
                snapshot[row['playerId']].append(team_map[int(tid)])
        drafts=defaultdict(list)
        for pick in draft['picks']:
            pid=pick['playerId'];seen(pid,pick['teamId'],'draft')
            drafts[pid].append({'timestamp':draft.get('completedAt') or draft.get('startedAt'),'team':team_map[pick['teamId']], **{k:pick.get(k) for k in ('round','pickInRound','overallPick','keeper')}})
        transactions=defaultdict(list)
        for event in activity['events']:
            if event['type']=='draft' or event.get('status')!='executed': continue
            movements=defaultdict(lambda:{'fromTeams':set(),'toTeams':set()})
            for team in event['teams']:
                for field,direction in [('playersAdded','toTeams'),('playersDropped','fromTeams')]:
                    for p in team[field]:
                        seen(p['playerId'],team['teamId'],'transaction')
                        movements[p['playerId']][direction].add(team['teamId'])
            for pid, movement in movements.items():
                transactions[pid].append({'type':event['type'],'timestamp':event.get('timestamp'),
                    'timestampKind':event.get('timestampKind'),'week':event.get('week'),
                    **{field:[team_map[tid] for tid in sorted(tids)] for field,tids in movement.items()}})
        score_map={p['playerId']:p for p in scoring['players']}
        status={}
        for match in teams['matchups']:
            w=match['week']; current=match['status']
            if current not in ('bye','upcoming'):status[w]='live' if current=='live' or status.get(w)=='live' else 'final'
        for pid in sorted(present):
            score=score_map.get(pid,{}); weeks=[]
            represented=set(scoring['weeks'])
            historical_teams={t for t in score.get('nflTeamsByWeek',{}).values() if t not in ('None','—')}
            last_team=None
            for week in sorted(represented):
                roster=slots[pid].get(week,[]); points=score.get('pointsByWeek',{}).get(str(week))
                fallback={r['points'] for r in roster if numeric(r['points'])}
                if not numeric(points):points=next(iter(fallback)) if len(fallback)==1 else None
                if numeric(points) and any(numeric(r['points']) and abs(r['points']-points)>0.011 for r in roster):
                    raise ValueError('Player score conflicts with audited weekly lineup')
                player_game=nfl_games['players'].get(str(pid),{}).get(str(week))
                teams_by_week=score.get('nflTeamsByWeek',{}).get(str(week)) or (player_game or {}).get('nflTeam')
                if teams_by_week in ('None','—'): teams_by_week=None
                week_teams={r.get('nflTeam') for r in roster if r.get('nflTeam') not in (None,'None','—')}
                week_opponents={r.get('nflOpponent') for r in roster if r.get('nflOpponent')}
                teams_by_week=teams_by_week or (next(iter(historical_teams)) if len(historical_teams)==1 else None) or (next(iter(week_teams)) if len(week_teams)==1 else last_team)
                if teams_by_week:last_team=teams_by_week
                game=nfl_game(scoring,{'nflTeamsByWeek':{str(week):teams_by_week}},week)
                opponent=(game['away'] if game['home']==teams_by_week else game['home']) if game else None
                state=game_state(week,player_game,teams_by_week,scoring.get('games',[]),status.get(week)=='final',defense=pid<0)
                weeks.append({'gameState':state,'nflStats':(player_game or {}).get('stats',{}),'season':year,'week':week,'status':status.get(week,'upcoming'),'points':points if numeric(points) else None,
                    'nflTeam':teams_by_week or (next(iter(week_teams)) if len(week_teams)==1 else None),
                    'nflOpponent':opponent or (next(iter(week_opponents)) if len(week_opponents)==1 else None),'rosters':roster})
            ownership=[{'team':o['team'],'weeks':sorted(o['weeks']),'evidence':sorted(o['evidence'])} for _,o in sorted(owners[pid].items())]
            histories[pid].append({'season':year,'complete':league['league']['complete'],'summary':summary(weeks),'seasonStats':season_stats(weeks,COLUMNS.get(profiles[pid].get('position'),[])),'weeks':weeks,
                'ownership':ownership,'rosterSnapshot':snapshot[pid],
                'rosterSnapshotLabel':'Final roster' if league['league']['complete'] else 'Current roster',
                'draft':drafts[pid], 'transactions':sorted(transactions[pid],key=lambda e:e['timestamp'] or '',reverse=True),
                'activityCoverage':{'status':activity['coverage']['status'], 'limitation':activity['coverage'].get('limitation')}})
    for pid,profile in sorted(profiles.items()):
        seasons=histories[pid]
        if not seasons: raise ValueError('Metadata has no league presence')
        payload={'schemaVersion':1,'profile':profile,'metadataGeneratedAt':metadata['generatedAt'],
                 'currentSeason':max(years),'statColumns':[{'key':k,'label':v} for k,v in COLUMNS.get(profile.get('position'),[])],
                 'seasons':seasons,'career':summary([w for s in seasons for w in s['weeks']])}
        write_json(folder/'players'/f'{pid}.json',payload)
        manifest.append({k:profile.get(k) for k in ('espnId','entityType','name','position','nflTeam','headshot','logo')}|
                        {'seasons':[s['season'] for s in seasons],'path':f'{slug}/players/{pid}.json'})
    write_json(folder/'players-index.json',{'schemaVersion':1,'metadataGeneratedAt':metadata['generatedAt'],'players':sorted(manifest,key=lambda p:(p['name'] or '',p['espnId']))})
    return manifest


if __name__=='__main__':
    site=json.loads((ROOT/'frontend/public/data/site.json').read_text())
    result=build_players(ROOT/'frontend/public/data',site['leaguePath'].split('/')[0],site['seasons'])
    print(f'Generated {len(result)} player profiles')
