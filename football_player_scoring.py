"""League-scored weekly player totals and kickoff boundaries for record calculations."""
import json
from pathlib import Path
from football_exporter import write_json

POSITIONS={1:'QB',2:'RB',3:'WR',4:'TE',5:'K',16:'D/ST'}


def normalize_player_scoring(raw, season, weeks):
    from espn_api.football.constant import PRO_TEAM_MAP
    from football_record_book import numeric
    rows=[];conflicts=[]
    for pool in raw.get('players',[]):
        p=pool.get('player',{});actual={};teams={}
        for s in p.get('stats',[]):
            if s.get('seasonId')!=season or s.get('statSourceId')!=0 or s.get('statSplitTypeId')!=1 or s.get('scoringPeriodId') not in weeks:continue
            if not numeric(s.get('appliedTotal')):continue
            w=str(s['scoringPeriodId']);value=round(s['appliedTotal'],2)
            if w in actual and actual[w]!=value:conflicts.append({'playerId':pool['id'],'week':int(w)})
            actual[w]=value
            teams[w]=PRO_TEAM_MAP.get(s.get('proTeamId'),'—')
        represented=sorted(set(teams.values())-{'—'})
        if actual:rows.append({'playerId':pool['id'],'name':p.get('fullName'),'position':POSITIONS.get(p.get('defaultPositionId'),'—'),
                               'nflTeam':' / '.join(represented) or PRO_TEAM_MAP.get(p.get('proTeamId'),'—'),'pointsByWeek':actual,'nflTeamsByWeek':teams})
    return {'schemaVersion':1,'season':season,'weeks':sorted(weeks),'source':'kona_playercard actual statSplitTypeId=1, statSourceId=0',
            'coverage':{'returnedPlayerCount':len(raw.get('players',[])),'playersWithWeeklyScores':len(rows),'conflicts':conflicts},'players':rows}


def generate_player_scoring(client,folder,season):
    folder=Path(folder);matches=json.loads((folder/'teams.json').read_text())['matchups']
    weeks={m['week'] for m in matches}
    filters={'players':{'filterStatsForTopScoringPeriodIds':{'value':max(weeks),'additionalValue':[f'00{season}',f'10{season}']}}}
    raw=client.league_get(params={'view':'kona_playercard'},headers={'x-fantasy-filter':json.dumps(filters)})
    data=normalize_player_scoring(raw,season,weeks)
    # Pro schedule supplies real kickoff boundaries; no guessed weekly ownership cutoff.
    schedule=client.get_pro_schedule()
    from espn_api.football.constant import PRO_TEAM_MAP
    games={}
    for team in schedule.get('settings',{}).get('proTeams',[]):
        for week,items in team.get('proGamesByScoringPeriod',{}).items():
            if int(week) not in weeks:continue
            for g in items:
                key=str(g['id'])
                games[key]={'week':int(week),'kickoff':g['date'],'home':PRO_TEAM_MAP.get(g['homeProTeamId'],'—'),'away':PRO_TEAM_MAP.get(g['awayProTeamId'],'—')}
    data['games']=list(games.values())
    data['playerPositions']={str(p['id']):POSITIONS.get(p['player'].get('defaultPositionId'),'—') for p in raw.get('players',[])}
    data['coverage']['lineupComparison']=enrich_lineups(folder,data)
    write_json(folder/'player-scoring.json',data)
    # Position is real player position, not the assigned draft lineup slot.
    path=folder/'draft.json'
    if path.exists():
        draft=json.loads(path.read_text());positions={p['id']:POSITIONS.get(p['player'].get('defaultPositionId'),'—') for p in raw.get('players',[])}
        for pick in draft['picks']:pick['position']=positions.get(pick['playerId'])
        write_json(path,draft)
    return data


def enrich_lineups(folder,scoring):
    """Use authoritative weekly NFL team IDs without changing existing fantasy scores."""
    from football_record_rankings import nfl_game
    players={p['playerId']:p for p in scoring['players']};checked=0;conflicts=[];updated=0
    for path in (Path(folder)/'lineups').glob('*.json'):
        detail=json.loads(path.read_text());week=int(path.stem)
        for roster in detail['teams'].values():
            for row in roster:
                p=players.get(row['playerId']);actual=p['pointsByWeek'].get(str(week)) if p else None
                if p is None or actual is None or row['points'] is None:continue
                checked+=1
                if abs(actual-row['points'])>.011:
                    conflicts.append({'week':week,'playerId':row['playerId'],'lineupPoints':row['points'],'sourcePoints':actual});continue
                team=p['nflTeamsByWeek'].get(str(week))
                if team and team!='—':
                    if row['nflTeam']!=team:updated+=1
                    row['nflTeam']=team
                game=nfl_game(scoring,p,week)
                if game:row['nflOpponent']=game['away'] if game['home']==team else game['home']
        write_json(path,detail)
    return {'lineupScoresChecked':checked,'scoreConflicts':conflicts,'historicalNflTeamsCorrected':updated}
