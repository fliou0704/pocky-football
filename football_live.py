"""One-response current-week overlay. Full historical/derived contracts remain immutable."""
import hashlib
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from football_exporter import read_config, write_json, ROOT
from football_http import get_json

LIVE = 'live.json'


class ReconciliationRequired(ValueError):
    """The fantasy period advanced; use the existing full pipeline."""


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def normalize(raw, league, home, teams, previous=None):
    from espn_api.football.constant import POSITION_MAP, PRO_TEAM_MAP
    season, week = league['league']['season'], home['state']['currentWeek']
    if not week or league['league']['complete']:
        raise ReconciliationRequired('No active fantasy period')
    if raw.get('id') != league['league']['id'] or raw.get('seasonId') != season:
        raise ValueError('Live league identity mismatch')
    if raw.get('status', {}).get('currentMatchupPeriod') != week:
        raise ReconciliationRequired('Fantasy period changed; full reconciliation required')
    if raw.get('scoringPeriodId') != week:
        raise ReconciliationRequired('Scoring and matchup periods require full reconciliation')
    ids = {t['teamId'] for t in league['standings']}
    expected = {(m['homeTeamId'], m['awayTeamId']): m for m in teams['matchups'] if m['week'] == week}
    if not expected:
        raise ValueError('No baseline current matchups')
    prior = previous if previous and previous.get('week') == week else {}
    lineups, matches, seen, global_players, adjustments = {}, [], set(), set(), {}
    for item in raw.get('schedule', []):
        if item.get('matchupPeriodId') != week:
            continue
        home_id, away_id = (item.get(s, {}).get('teamId') for s in ('home', 'away'))
        if home_id == away_id:
            away_id = None
        key = (home_id, away_id)
        if key not in expected or key in seen:
            raise ValueError('Unexpected or duplicate live matchup')
        seen.add(key)
        match = dict(expected[key])
        totals = {}
        for side, tid in [('home', home_id), ('away', away_id)]:
            if tid is None:
                totals[side] = None
                continue
            if tid not in ids or str(tid) in lineups:
                raise ValueError('Duplicate/unknown live team')
            data = item[side]
            total = data.get('totalPointsLive')
            if not number(total):
                raise ValueError('Missing actual team total')
            adjustment = data.get('adjustment', 0)
            if not number(adjustment):
                raise ValueError('Invalid score adjustment')
            adjustments[str(tid)] = adjustment
            totals[side] = round(total, 2)
            entries = data.get('rosterForCurrentScoringPeriod', {}).get('entries')
            if not isinstance(entries, list) or not entries:
                raise ValueError('Missing live lineup')
            players, player_ids = [], set()
            old_rows = {p['playerId']: p for p in prior.get('lineups', {}).get('teams', {}).get(str(tid), [])}
            for entry in entries:
                pid = entry.get('playerId')
                pool = entry.get('playerPoolEntry') or {}
                player = pool.get('player') or {}
                if type(pid) is not int or not pid or pid in player_ids or pid in global_players or player.get('id') != pid:
                    raise ValueError('Invalid live player identity')
                player_ids.add(pid)
                global_players.add(pid)
                slot = POSITION_MAP.get(entry.get('lineupSlotId'))
                if not slot:
                    raise ValueError('Unknown live lineup slot')
                slot = {'RB/WR/TE': 'FLEX', 'BN': 'BE'}.get(slot, slot)
                # appliedStatTotal is ESPN's actual scoring for this response period, including
                # an authoritative zero before a game. Never substitute projected stats.
                points = pool.get('appliedStatTotal')
                if points is not None and not number(points):
                    raise ValueError('Invalid actual player score')
                old = old_rows.get(pid, {})
                if points is None and slot in ('BE','BN','IR'):
                    points = old.get('points')  # Omission cannot erase a verified bench score.
                name = player.get('fullName') or old.get('name')
                position = {1:'QB',2:'RB',3:'WR',4:'TE',5:'K',16:'D/ST'}.get(player.get('defaultPositionId')) or old.get('position')
                if not name or not position:
                    raise ValueError('Missing live player metadata')
                players.append({'playerId':pid, 'name':name, 'slot':slot, 'position':position,
                                'nflTeam':PRO_TEAM_MAP.get(player.get('proTeamId')) or old.get('nflTeam', '—'),
                                'injuryStatus':player.get('injuryStatus') or old.get('injuryStatus'),
                                'points':round(points, 2) if number(points) else None})
            starters = [p for p in players if p['slot'] not in ('BE', 'BN', 'IR')]
            expected_slots = Counter({'RB/WR/TE':'FLEX','BN':'BE'}.get(p['slot'],p['slot']) for p in teams['teams'][str(tid)]['roster'] if p.get('group') == 'starter')
            if expected_slots and Counter(p['slot'] for p in starters) != expected_slots:
                raise ValueError('Incomplete/changed starter assignments; full reconciliation required')
            if not starters or any(p['points'] is None for p in starters):
                raise ValueError('Incomplete actual starter scoring')
            if abs(sum(p['points'] for p in starters)+adjustment-total) > .06:
                raise ValueError('Team total and actual starters disagree')
            lineups[str(tid)] = sorted(players, key=lambda p:p['playerId'])
        winner = item.get('winner')
        match['status'] = ('bye' if away_id is None else 'final' if winner in ('HOME','AWAY','TIE')
                           else 'live' if any(v is not None and v != 0 for v in totals.values()) else 'upcoming')
        match.update(homeScore=totals['home'], awayScore=totals['away'],
                     winnerTeamId=home_id if winner == 'HOME' else away_id if winner == 'AWAY' else None)
        matches.append(match)
    if seen != set(expected) or set(map(int, lineups)) != ids:
        raise ValueError('Incomplete live matchup/team population')
    return {'schemaVersion':1, 'leagueId':raw['id'], 'season':season, 'week':week,
            'matchups':sorted(matches, key=lambda m:m['homeTeamId']),
            'lineups':{'schemaVersion':1, 'season':season, 'week':week, 'teams':lineups},
            'adjustments':adjustments,
            'semantics':'Actual current-period overlay; standings, records and recaps remain full-snapshot data'}


def collect(root, slug, metrics=None, fetch=get_json):
    from dotenv import load_dotenv
    root = Path(root)
    config = read_config(slug)
    folder = root/slug
    read = lambda p: json.loads(p.read_text())
    meta = read(folder/'refresh.json')
    season = config['season']
    league, home, teams = (read(folder/str(season)/(name+'.json')) for name in ('league','home','teams'))
    week = home['state']['currentWeek']
    if not week:
        raise ReconciliationRequired('No active fantasy week')
    load_dotenv(ROOT/'.env', override=False)
    names = config['credentials']
    cookies = {'espn_s2':os.environ.get(names['espnS2Env']), 'SWID':os.environ.get(names['swidEnv'])}
    if not all(cookies.values()):
        raise ValueError('Required ESPN credentials missing')
    raw = fetch(f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{config["leagueId"]}',
                params={'view':['mMatchupScore','mScoreboard','mStatus'], 'scoringPeriodId':week},
                headers={'x-fantasy-filter':json.dumps({'schedule':{'filterMatchupPeriodIds':{'value':[week]}}})},
                cookies=cookies, metrics=metrics)
    previous = read(folder/LIVE) if (folder/LIVE).exists() else None
    data = normalize(raw, league, home, teams, previous)
    data['baseGenerationId'] = meta.get('baseGenerationId', meta['generationId']) if meta.get('mode') == 'live' else meta['generationId']
    data['sourceFileHashes'] = {f'{slug}/{season}/{name}.json':hashlib.sha256((folder/str(season)/(name+'.json')).read_bytes()).hexdigest()
                               for name in ('league','home','teams')}
    data['snapshotId'] = digest(data)
    if previous and previous.get('snapshotId') == data['snapshotId']:
        return False
    data['fetchedAt'] = datetime.now(timezone.utc).isoformat()
    write_json(folder/LIVE, data)
    return True


def validate_live(root, slug, meta=None):
    folder = Path(root)/slug
    path = folder/LIVE
    if not path.exists():
        if meta and meta.get('mode') == 'live':
            raise ValueError('Live release missing overlay')
        return
    data = json.loads(path.read_text())
    content = {k:v for k,v in data.items() if k not in ('fetchedAt','snapshotId')}
    if digest(content) != data.get('snapshotId'):
        raise ValueError('Live snapshot digest mismatch')
    year, week = data['season'], data['week']
    league = json.loads((folder/str(year)/'league.json').read_text())
    home = json.loads((folder/str(year)/'home.json').read_text())
    ids = {t['teamId'] for t in league['standings']}
    if data['leagueId'] != league['league']['id'] or week != home['state']['currentWeek'] or set(map(int,data['lineups']['teams'])) != ids:
        raise ValueError('Live snapshot identity mismatch')
    baseline = json.loads((folder/str(year)/'teams.json').read_text())
    expected = {(m['homeTeamId'],m['awayTeamId']) for m in baseline['matchups'] if m['week'] == week}
    actual = {(m['homeTeamId'],m['awayTeamId']) for m in data['matchups']}
    if actual != expected or len(actual) != len(data['matchups']) or data['lineups']['week'] != week or data['lineups']['season'] != year:
        raise ValueError('Live matchup/lineup coverage mismatch')
    seen = set()
    for match in data['matchups']:
        if match['week'] != week or match['status'] not in ('upcoming','live','final','bye'):
            raise ValueError('Invalid live matchup')
        for side in ('home','away'):
            tid = match[side+'TeamId']
            if tid is None: continue
            rows = data['lineups']['teams'][str(tid)]
            for row in rows:
                if row['playerId'] in seen or (row['points'] is not None and not number(row['points'])):
                    raise ValueError('Duplicate/invalid live player')
                seen.add(row['playerId'])
            starters = [r for r in rows if r['slot'] not in ('BE','BN','IR')]
            if not starters or any(not number(r['points']) for r in starters) or not number(match[side+'Score']):
                raise ValueError('Invalid live starter scoring')
            if abs(sum(r['points'] for r in starters)+data['adjustments'][str(tid)]-match[side+'Score']) > .06:
                raise ValueError('Live starter totals disagree')
    datetime.fromisoformat(data['fetchedAt'])
    if meta and (meta.get('mode') != 'live' or meta.get('baseGenerationId') != data['baseGenerationId']):
        raise ValueError('Live overlay/full generation mismatch')
    for name, expected in data['sourceFileHashes'].items():
        if name not in {f'{slug}/{year}/{n}.json' for n in ('league','home','teams')} or hashlib.sha256((Path(root)/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Live overlay source mismatch')
    if meta and meta.get('liveContentHash') != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('Live content hash mismatch')
