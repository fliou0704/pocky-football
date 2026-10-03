"""NFL participation/stat allowlist from the existing ESPN actual weekly playercard response."""
from datetime import datetime, timezone
from football_record_book import numeric

STAT_IDS={'passAttempts':0,'passYards':3,'passTD':4,'interceptions':20,'rushAttempts':23,'rushYards':24,
          'rushTD':25,'receptions':53,'recYards':42,'recTD':43,'fgMade':83,'fgAttempts':84,'extraPoints':86,
          'sacks':99,'defInterceptions':95,'fumbleRecoveries':96,'defTD':105,'pointsAllowed':120}
COLUMNS={
 'QB':[('passYards','Pass Yds'),('passTD','Pass TD'),('interceptions','INT'),('rushYards','Rush Yds'),('rushTD','Rush TD')],
 'RB':[('rushAttempts','Rush Att'),('rushYards','Rush Yds'),('rushTD','Rush TD'),('receptions','Rec'),('recYards','Rec Yds'),('recTD','Rec TD')],
 'WR':[('receptions','Rec'),('recYards','Rec Yds'),('recTD','Rec TD'),('rushYards','Rush Yds')],
 'TE':[('receptions','Rec'),('recYards','Rec Yds'),('recTD','Rec TD')],
 'K':[('fgMade','FGM'),('fgAttempts','FGA'),('extraPoints','XP')],
 'D/ST':[('sacks','Sacks'),('defInterceptions','INT'),('fumbleRecoveries','FR'),('defTD','TD'),('pointsAllowed','PA')]}


def normalize_games(raw, season, weeks):
    from espn_api.football.constant import PRO_TEAM_MAP
    players={}
    for pool in raw.get('players',[]):
        weekly={}
        for s in pool['player'].get('stats') or []:
            w=s.get('scoringPeriodId')
            if s.get('seasonId')!=season or s.get('statSourceId')!=0 or s.get('statSplitTypeId')!=1 or w not in weeks:continue
            stats=s.get('stats'); stats=stats if isinstance(stats,dict) else {}
            gp=stats.get('210')
            if gp is not None and gp not in (0,1):raise ValueError('Unexpected weekly ESPN GP')
            # ESPN actual dictionaries are sparse: omitted counting categories mean zero only
            # when explicit GP=1 establishes an actual played-game stat line.
            values={key:stats.get(str(sid),0 if gp==1 else None) for key,sid in STAT_IDS.items()}
            if '53' not in stats and '41' in stats:values['receptions']=stats['41']
            row={'played':True if gp==1 else False if gp==0 else None,'stats':values,
                 'nflTeam':PRO_TEAM_MAP.get(s.get('proTeamId')),'hasActualStats':bool(stats),'eventId':str(s.get('externalId') or ''),
                 'points':s.get('appliedTotal'), 'actualRecord':True}
            if str(w) in weekly and weekly[str(w)]!=row:raise ValueError('Conflicting NFL stat lines')
            weekly[str(w)]=row
        if weekly:players[str(pool['id'])]=weekly
    return {'schemaVersion':2,'season':season,'weeks':sorted(weeks),'source':'ESPN actual weekly playercard stats; participation stat 210',
            'players':players,'coverage':{'actualWeeksRequested':len(weeks),'playersWithActualSeasonRecords':sorted(players)}}


def game_state(week, player_game, nfl_team, schedule, final_week, now=None, defense=False, source_covered=False):
    now=now or datetime.now(timezone.utc)
    scheduled=[g for g in schedule if g['week']==week and nfl_team in (g['home'],g['away'])]
    event_id=(player_game or {}).get('eventId')
    event_games=[g for g in schedule if g['week']==week and str(g.get('id'))==str(event_id)] if event_id else []
    if len(event_games)==1:scheduled=event_games
    played=player_game.get('played') if player_game else None
    if len(scheduled)>1:return 'unknown'
    if not scheduled:
        # Only a real historical week/team and complete per-team schedule establishes BYE.
        team_schedule=[g for g in schedule if nfl_team in (g['home'],g['away'])]
        if nfl_team and nfl_team not in ('None','—','FA') and len(team_schedule)>=min(10,len({g['week'] for g in schedule})):return 'bye'
        if player_game is None and source_covered and final_week:return 'did_not_play'
        return 'unknown'
    game=scheduled[0]
    if game.get('canceled'):return 'did_not_play'
    if game.get('completionUnknown'):return 'unknown'
    if game['kickoff']>now.timestamp()*1000:return 'upcoming'
    if not final_week:return 'played' if played else 'upcoming'
    if defense or played is True:return 'played'
    if played is False:return 'did_not_play'
    # Sparse dictionaries with positive game production independently prove participation.
    if player_game and any(numeric(v) and v!=0 for k,v in player_game['stats'].items() if k!='pointsAllowed'):
        return 'played'
    # An explicit empty actual record for this completed NFL event supports non-participation.
    # Missing records, mismatched events, and absent schedules remain unresolved.
    if player_game and player_game.get('actualRecord') and not player_game.get('hasActualStats') and str(player_game.get('eventId'))==str(game.get('id')):
        return 'did_not_play'
    if player_game is None and source_covered:
        return 'did_not_play'
    return 'unknown'


def season_stats(rows, columns):
    completed=[r for r in rows if r['status']=='final' and r['gameState'] not in ('bye','upcoming')]
    played=[r for r in completed if r['gameState']=='played']
    nfl_reliable=all(r['gameState'] in ('played','did_not_play') for r in completed)
    from football_record_book import STARTERS
    starts=[(r,roster) for r in rows if r.get('fantasyStatus',r['status'])=='final'
            for roster in r.get('rosters',[]) if roster['slot'] in STARTERS]
    # Fantasy GP counts completed active-slot starts, including a started inactive player.
    # Bench/IR and NFL-only weeks never count. Zero is a real fantasy start score.
    gp=len(starts)
    scores=[roster['points'] for _,roster in starts]
    fpts=round(sum(scores),2) if all(numeric(v) for v in scores) else None
    totals={k:round(sum(r['nflStats'][k] for r in played),3) if nfl_reliable and all(numeric(r['nflStats'].get(k)) for r in played) else None for k,_ in columns}
    return {'gp':gp,'points':fpts,'fppg':round(fpts/gp,2) if gp and fpts is not None else None,'nflStats':totals,
            'participationComplete':nfl_reliable,'scope':'Fantasy totals: completed active-slot starts; NFL stats: full regular season'}



def enrich_participation(data, player_ids, cache, refresh=False):
    """Bounded public ESPN fallback only where weekly stat 210 is absent."""
    import json
    import requests
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    season=data['season']
    def enrich(pid):
        rows=data['players'].get(str(pid),{})
        missing=[r for r in rows.values() if r['played'] is None and r.get('eventId')]
        if pid<0 or not missing:return
        path=cache/f'{season}-{pid}.json'
        if refresh or not path.exists():
            try:
                response=requests.get(f'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{season}/athletes/{pid}/eventlog',params={'limit':100},timeout=20)
                response.raise_for_status();raw=response.json()
                events=raw.get('events',{})
                if events.get('pageCount',1)>1:return
                safe={item['event']['$ref'].split('/events/')[1].split('?')[0]:item['played']
                      for item in events.get('items',[]) if type(item.get('played')) is bool}
                path.write_text(json.dumps(safe))
            except (requests.RequestException,ValueError,KeyError):return
        flags=json.loads(path.read_text())
        for r in missing:
            if r['eventId'] in flags:
                r['played']=flags[r['eventId']];r['participationSource']='espn_eventlog'
                if r['played'] and r['hasActualStats']:
                    r['stats']={k:0 if v is None else v for k,v in r['stats'].items()}
    with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(enrich,sorted(player_ids)))
    return data


def normalize_nfl_schedule(raw, games):
    """All regular-season NFL weeks, independent of league matchup boundaries."""
    from espn_api.football.constant import PRO_TEAM_MAP
    now=datetime.now(timezone.utc).timestamp()*1000
    evidence={r['eventId'] for rows in games['players'].values() for r in rows.values()
              if r['played'] is True or any(numeric(v) and v!=0 for v in r['stats'].values())}
    schedule={}
    for team in raw.get('settings',{}).get('proTeams',[]):
        for week,items in (team.get('proGamesByScoringPeriod') or {}).items():
            if int(week) not in games['weeks']:continue
            for g in items:
                eid=str(g['id'])
                schedule[eid]={'id':eid,'week':int(week),'kickoff':g['date'],
                    'home':PRO_TEAM_MAP.get(g['homeProTeamId']),'away':PRO_TEAM_MAP.get(g['awayProTeamId']),
                    'complete':g['date']<now and (g.get('statsOfficial') is True or (eid in evidence and g['date']<now-24*3600000)),
                    'completionUnknown':g['date']<now-24*3600000 and eid not in evidence}
    return sorted(schedule.values(),key=lambda g:(g['week'],g['kickoff'],g['id']))


def generate_player_games(client,folder,season,raw=None,schedule=None):
    import json
    from pathlib import Path
    from football_player_metadata import universe
    from football_exporter import ROOT,write_json
    folder=Path(folder)
    # ESPN's 2021+ regular seasons have 18 weeks, even for shorter fantasy schedules.
    weeks=set(range(1,19))
    if raw is None:
        filters={'players':{'filterStatsForTopScoringPeriodIds':{'value':18,'additionalValue':[f'00{season}',f'10{season}']}}}
        raw=client.league_get(params={'view':'kona_playercard'},headers={'x-fantasy-filter':json.dumps(filters)})
    data=normalize_games(raw,season,weeks)
    data['games']=normalize_nfl_schedule(schedule or client.get_pro_schedule(),data)
    enrich_schedule_status(data,ROOT/'.cache/player-games/game-status')
    known,_,_=universe(folder.parent,season,season)
    data['players']={pid:rows for pid,rows in data['players'].items() if int(pid) in known}
    data['coverage']['playersWithActualSeasonRecords']=sorted(data['players'])
    enrich_participation(data,known,ROOT/'.cache/player-games/participation',refresh=not json.loads((folder/'league.json').read_text())['league']['complete'])
    write_json(folder/'player-games.json',data)
    return data


def enrich_schedule_status(data,cache):
    """Only scheduled past events lacking all NFL stat evidence need a status probe."""
    import requests,json
    from pathlib import Path
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    for game in data['games']:
        if not game.get('completionUnknown'):continue
        path=cache/f"{game['id']}.json"
        try:
            if not path.exists():
                eid=game['id']
                response=requests.get(f'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{eid}/competitions/{eid}/status',timeout=20)
                response.raise_for_status();status=response.json()['type']
                path.write_text(json.dumps({'name':status.get('name'),'completed':status.get('completed')}))
            status=json.loads(path.read_text())
            game['canceled']=status['name']=='STATUS_CANCELED'
            game['complete']=status['completed'] is True
            game['completionUnknown']=not (game['canceled'] or game['complete'])
        except (requests.RequestException,KeyError,ValueError):
            game['complete']=False
    return data
