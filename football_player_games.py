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
                 'nflTeam':PRO_TEAM_MAP.get(s.get('proTeamId')),'hasActualStats':bool(stats),'eventId':str(s.get('externalId') or '')}
            if str(w) in weekly and weekly[str(w)]!=row:raise ValueError('Conflicting NFL stat lines')
            weekly[str(w)]=row
        if weekly:players[str(pool['id'])]=weekly
    return {'schemaVersion':1,'season':season,'source':'ESPN actual weekly playercard stats; participation stat 210',
            'players':players}


def game_state(week, player_game, nfl_team, schedule, final_week, now=None, defense=False):
    now=now or datetime.now(timezone.utc)
    scheduled=[g for g in schedule if g['week']==week and nfl_team in (g['home'],g['away'])]
    played=player_game.get('played') if player_game else None
    if len(scheduled)>1:return 'unknown'
    if not scheduled:
        # Only a real historical week/team and complete per-team schedule establishes BYE.
        team_schedule=[g for g in schedule if nfl_team in (g['home'],g['away'])]
        return 'bye' if nfl_team and nfl_team not in ('None','—','FA') and len(team_schedule)>=min(10,len({g['week'] for g in schedule})) else 'unknown'
    game=scheduled[0]
    if game['kickoff']>now.timestamp()*1000:return 'upcoming'
    if not final_week:return 'live' if played else 'pending'
    if defense or played is True:return 'played'
    if played is False:return 'did_not_play'
    # Sparse dictionaries with positive game production independently prove participation.
    if player_game and any(numeric(v) and v!=0 for k,v in player_game['stats'].items() if k!='pointsAllowed'):
        return 'played'
    return 'unknown'


def season_stats(rows, columns):
    completed=[r for r in rows if r['status']=='final' and r['gameState'] not in ('bye','upcoming')]
    played=[r for r in completed if r['gameState']=='played']
    reliable=all(r['gameState'] in ('played','did_not_play') for r in completed)
    gp=len(played) if reliable else None
    # Fantasy totals remain independently reliable even when participation is unknown.
    scores=[r['points'] for r in completed]
    fpts=round(sum(scores),2) if all(numeric(v) for v in scores) else None
    totals={k:round(sum(r['nflStats'][k] for r in played),3) if reliable and all(numeric(r['nflStats'].get(k)) for r in played) else None for k,_ in columns}
    return {'gp':gp,'points':fpts,'fppg':round(fpts/gp,2) if gp and fpts is not None else None,'nflStats':totals,
            'participationComplete':reliable,'scope':'NFL weeks covered by this fantasy season'}


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
