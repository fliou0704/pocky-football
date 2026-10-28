"""Offline optimal weekly lineups from committed season snapshots; no network calls."""
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
    if set(rosters) != {str(t['teamId']) for t in standings}:
        return None  # Cannot establish weekly ownership without complete roster snapshots.
    players = {}
    for team_id, roster in rosters.items():
        for row in roster:
            if row['playerId'] in players or not numeric(row.get('points')):
                return None
            players[row['playerId']] = dict(row, teamId=int(team_id))
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


def build_team_of_week(output='frontend/public/data', slug='pocky-football', years=None):
    root = Path(output)
    if years is None:
        years = json.loads((root / 'site.json').read_text())['seasons']
    for year in years:
        folder = root / slug / str(year)
        league = json.loads((folder / 'league.json').read_text())
        matches = json.loads((folder / 'teams.json').read_text())['matchups']
        scoring_path = folder / 'player-scoring.json'
        scoring = json.loads(scoring_path.read_text()) if scoring_path.exists() else {}
        weeks = {}
        for week in sorted({m['week'] for m in matches}):
            if not completed([m for m in matches if m['week'] == week]):
                continue
            path = folder / 'lineups' / f'{week}.json'
            pool = weekly_pool(json.loads(path.read_text()), scoring, league['standings'], year, week) if path.exists() else None
            result = optimize(pool) if pool else None
            weeks[str(week)] = dict(result or {}, status='available' if result else 'unavailable',
                                    playerCount=len(pool) if pool else 0,
                                    pool='Recorded weekly rosters (including benches) and additional players with committed weekly scores. Coverage is limited to the committed scoring pool.')
        write_json(folder / 'team-of-week.json', {'schemaVersion': 1, 'season': year, 'weeks': weeks})


if __name__ == '__main__':
    build_team_of_week()
