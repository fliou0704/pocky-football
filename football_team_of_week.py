"""Offline optimal weekly lineups from committed season snapshots; no network calls."""
import hashlib
import json
import math
from pathlib import Path
from football_exporter import write_json

SLOTS = ('QB', 'RB', 'RB', 'WR', 'WR', 'TE', 'FLEX', 'D/ST', 'K')


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def optimize(players):
    """Slot-mask dynamic programming, processing each distinct player once."""
    unique = {}
    for player in players:
        identity = player['playerId']
        if identity in unique and unique[identity] != player:
            return None  # Conflicting evidence must not silently choose a source.
        unique[identity] = player
    # At most nine players from any identical eligibility group can be selected.
    groups = {}
    for player in unique.values():
        if not numeric(player.get('points')):
            return None
        positions = set(player.get('eligiblePositions', [player['position']]))
        eligible = tuple(i for i, slot in enumerate(SLOTS) if slot in positions or slot == 'FLEX' and positions & {'RB', 'WR', 'TE'})
        groups.setdefault(eligible, []).append(player)
    candidates = []
    for eligible, rows in groups.items():
        candidates.extend((p, eligible) for p in sorted(rows, key=lambda p: (-p['points'], p['playerId']))[:9])
    candidates.sort(key=lambda pair: pair[0]['playerId'])
    states = {0: (0, (None,) * 9)}
    def key(state):
        return (-state[0], tuple(p['playerId'] if p else float('inf') for p in state[1]))
    for player, eligible in candidates:
        for mask, (score, lineup) in list(states.items()):
            for slot in eligible:
                if mask & (1 << slot):
                    continue
                next_mask = mask | (1 << slot)
                next_lineup = list(lineup)
                next_lineup[slot] = player
                candidate = (score + round(player['points'] * 100), tuple(next_lineup))
                if next_mask not in states or key(candidate) < key(states[next_mask]):
                    states[next_mask] = candidate
    result = states.get(511)
    if result is None:
        return None
    return {'totalPoints': result[0] / 100,
            'lineup': [dict(player, slot=slot) for slot, player in zip(SLOTS, result[1])]}


def completed(matches):
    return bool(matches) and any(m['status'] == 'final' for m in matches) and all(m['status'] in ('final', 'bye') for m in matches)


def weekly_pool(detail, scoring, standings, season, week):
    """Weekly roster identity wins; scoring pool adds recorded unrostered players."""
    if detail.get('season') != season or detail.get('week') != week or scoring.get('season') != season:
        return None
    rosters = detail.get('teams', {})
    if set(rosters) != {str(t['teamId']) for t in standings} or not all(rosters.values()):
        return None  # Cannot establish weekly ownership without complete roster snapshots.
    players = {}
    seen = set()
    actual = {p['playerId']: p.get('pointsByWeek', {}).get(str(week)) for p in scoring.get('players', [])}
    for team_id, roster in rosters.items():
        for row in roster:
            if row['playerId'] in seen:
                return None
            seen.add(row['playerId'])
            points = row.get('points')
            if not numeric(points):
                points = actual.get(row['playerId'])
            if not numeric(points):
                # Bye/inactive/unknown is not a fabricated zero and cannot poison
                # other players' reliable actual scoring. Only scored players compete.
                continue
            players[row['playerId']] = dict(row, points=points, teamId=int(team_id))
    for row in scoring.get('players', []):
        points = row.get('pointsByWeek', {}).get(str(week))
        if not numeric(points):
            continue
        identity = row['playerId']
        if identity in players:
            if abs(players[identity]['points'] - points) > .011:
                return None
        else:
            players[identity] = {'playerId': identity, 'name': row['name'], 'position': row['position'],
                                 'nflTeam': row.get('nflTeamsByWeek', {}).get(str(week), '—'),
                                 'points': points, 'teamId': None}
    if any(c.get('week') == week for c in scoring.get('coverage', {}).get('conflicts', [])):
        return None
    return list(players.values())


def season_team_of_week(folder, metadata=None):
    """Pure derivation shared by generation and release validation."""
    folder = Path(folder)
    read = lambda path: json.loads(path.read_text())
    league = read(folder/'league.json')
    year = league['league']['season']
    matches = read(folder/'teams.json')['matchups']
    scoring = read(folder/'player-scoring.json')
    metadata = metadata if metadata is not None else (read(folder.parent/'players.json').get('players', [])
                if (folder.parent/'players.json').exists() else [])
    identities = {p['espnId']: p for p in metadata}
    weeks = {}
    inputs = {'league': league, 'matches': matches, 'scoring': scoring, 'metadata': metadata, 'lineups': {}}
    for week in sorted({m['week'] for m in matches}):
        if not completed([m for m in matches if m['week'] == week]):
            continue
        path = folder/'lineups'/f'{week}.json'
        detail = read(path) if path.exists() else None
        inputs['lineups'][str(week)] = detail
        pool = weekly_pool(detail, scoring, league['standings'], year, week) if detail else None
        result = optimize(pool) if pool else None
        if result:
            for player in result['lineup']:
                identity = identities.get(player['playerId'], {})
                player.update({key: identity.get(key) for key in ('headshot', 'logo', 'entityType')})
                player['hasProfile'] = bool(identity)
        excluded = sum(not numeric(p.get('points')) and not numeric(next(
            (s.get('pointsByWeek', {}).get(str(week)) for s in scoring['players'] if s['playerId'] == p['playerId']), None))
            for roster in (detail or {}).get('teams', {}).values() for p in roster)
        weeks[str(week)] = dict(result or {}, status='available' if result else 'unavailable',
                playerCount=len(pool) if pool else 0, excludedUnscoredPlayers=excluded,
                pool='Players with reliable recorded actual weekly scores, including benches and unrostered players.',
                **({'unavailableReason': 'Reliable scores and complete roster coverage are needed to fill all nine slots.'} if not result else {}))
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return {'schemaVersion': 1, 'algorithmVersion': 2, 'season': year, 'sourceHash': fingerprint, 'weeks': weeks}


def build_team_of_week(output='frontend/public/data', slug='pocky-football', years=None):
    root = Path(output)
    if years is None:
        years = json.loads((root/'site.json').read_text())['seasons']
    for year in years:
        folder = root/slug/str(year)
        write_json(folder/'team-of-week.json', season_team_of_week(folder))


if __name__ == '__main__':
    build_team_of_week()
    # Offline derived-data repairs keep the real ESPN fetch timestamp unchanged.
    from data_refresh import update_derived_metadata, validate
    update_derived_metadata(Path('frontend/public/data'))
    validate(Path('frontend/public/data'))
