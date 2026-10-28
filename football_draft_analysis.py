"""Offline, position-aware draft evaluation from normalized football snapshots."""
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

POSITIONS = ('QB', 'RB', 'WR', 'TE', 'K', 'D/ST')
ROOT = Path(__file__).parent


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def avg(values):
    values = [v for v in values if number(v)]
    return round(mean(values), 3) if values else None


def midranks(rows, key):
    """Average ranks for ties, keyed by player ID; stable and order independent."""
    result = {}
    ordered = sorted(rows, key=lambda p: (-p[key], p['playerId']))
    for i, p in enumerate(ordered):
        ties = [j + 1 for j, other in enumerate(ordered) if other[key] == p[key]]
        result[p['playerId']] = mean(ties)
    return result


def identity_lookup(config):
    result = {}
    for manager_id, manager in config.get('managers', {}).items():
        for membership in manager['memberships']:
            key = (membership['season'], membership['teamId'])
            if key in result:
                raise ValueError('Duplicate manager membership')
            result[key] = (manager_id, manager['name'], membership['expectedOwner'])
    return result


def identify(year, team, identities):
    identity = identities.get((year, team['teamId']))
    if identity and identity[2] == team.get('owner'):
        return identity[:2]
    return (f"season-{year}-team-{team['teamId']}", f"{team['name']} ({year}; unverified manager)")


def rookie_status(metadata, year):
    if metadata.get('entityType') == 'team_defense':
        return None
    rookie = metadata.get('rookieSeason')
    return rookie == year if type(rookie) is int and rookie <= year else None


def season_points(player, weeks, games):
    """Require a score, explicit DNP, or schedule-proven bye for every used week."""
    weekly = player.get('pointsByWeek', {})
    if not weekly:
        return None
    teams = set(player.get('nflTeamsByWeek', {}).values()) - {'—', 'FA', None}
    records = games.get('players', {}).get(str(player['playerId']), {})
    schedule = games.get('games', [])
    for week in weeks:
        if number(weekly.get(str(week))):
            continue
        record = records.get(str(week), {})
        if record.get('played') is False:
            continue
        # A missing point entry for a played game remains missing, never zero.
        team = next(iter(teams)) if len(teams) == 1 else None
        team_games = [g for g in schedule if team and team in (g['home'], g['away'])]
        if team_games and len({g['week'] for g in team_games}) >= 16 and not any(g['week'] == week for g in team_games):
            continue
        return None
    return round(sum(weekly[str(w)] for w in weeks if number(weekly.get(str(w)))), 2)


def aggregate(rows):
    groups = defaultdict(list)
    for p in rows:
        groups[p['managerId']].append(p)
    result = []
    for manager_id, picks in groups.items():
        eligible = [p for p in picks if p['value'] is not None]
        rounds = [p for p in picks if p['roundScore'] is not None]
        season_values = [avg([p['value'] for p in eligible if p['season'] == year]) for year in sorted({p['season'] for p in eligible})]
        last = max(picks, key=lambda p: p['season'])
        result.append({'managerId': manager_id, 'manager': last['manager'], 'team': last['team'],
                       'seasons': sorted({p['season'] for p in picks}), 'picks': len(picks), 'eligiblePicks': len(eligible),
                       'averageValue': avg([p['value'] for p in eligible]), 'totalValue': round(sum(p['value'] for p in eligible), 3) if eligible else None,
                       'averageRoundRank': avg([p['roundRank'] for p in rounds]), 'roundScore': avg([p['roundScore'] for p in rounds]),
                       'roundWins': sum(p['roundWinner'] for p in rounds), 'topThree': sum(p['roundTopThree'] for p in rounds),
                       'highValue': sum(p['value'] >= 25 for p in eligible), 'successRate': avg([100 * (p['value'] > 0) for p in eligible]),
                       'averagePoints': avg([p['points'] for p in eligible]), 'averageDraftRound': avg([p['round'] for p in picks]),
                       'averageDraftPick': avg([p['overallPick'] for p in picks]), 'averageNormalizedPick': avg([p['normalizedPick'] for p in picks]), 'averageFinish': avg([p['finishPercentile'] for p in eligible]),
                       'seasonSpread': round(pstdev(season_values), 3) if len(season_values) >= 2 else None,
                       'smallSample': len(eligible) < 10 or len(season_values) < 2,
                       'bestPick': max(eligible, key=lambda p: p['value']) if eligible else None,
                       'evidence': [{'season': p['season'], 'overallPick': p['overallPick']} for p in picks]})
    return sorted(result, key=lambda r: (-(r['averageValue'] if r['averageValue'] is not None else -1000), r['managerId']))


def tendencies(rows):
    result = {}
    for position in POSITIONS:
        groups = defaultdict(list)
        for p in rows:
            if p['position'] == position:
                groups[p['managerId']].append(p)
        leaders = []
        for mid, picks in groups.items():
            first = [min((p for p in picks if p['season'] == y), key=lambda p: p['overallPick']) for y in sorted({p['season'] for p in picks})]
            total = sum(p['managerId'] == mid for p in rows)
            latest = max(picks, key=lambda p: p['season'])
            leaders.append({'managerId': mid, 'manager': latest['manager'], 'team': latest['team'], 'picks': len(picks),
                            'seasons': sorted({p['season'] for p in picks}), 'averageRound': avg([p['round'] for p in picks]),
                            'normalizedPick': avg([p['normalizedPick'] for p in picks]), 'firstRound': median([p['round'] for p in first]),
                            'averageFirstRound': avg([p['round'] for p in first]), 'share': round(100 * len(picks) / total, 2),
                            'earliest': min(picks, key=lambda p: p['normalizedPick']), 'evidence': first})
        result[position] = sorted(leaders, key=lambda p: (p['averageFirstRound'], p['managerId']))
    return result


def analyze_season(year, league, teams, draft, scoring, games, metadata, identities):
    used_weeks = sorted({m['week'] for m in teams['matchups']})
    final_weeks = [w for w in used_weeks if all(m['status'] in ('final', 'bye') for m in teams['matchups'] if m['week'] == w)]
    complete = bool(league['league']['complete'])
    conflicts = scoring.get('coverage', {}).get('conflicts') or scoring.get('coverage', {}).get('lineupComparison', {}).get('scoreConflicts')
    valid = complete and draft.get('coverage', {}).get('complete', False) and not conflicts and set(used_weeks) <= set(scoring.get('weeks', []))
    pool = []
    for player in scoring.get('players', []):
        points = season_points(player, used_weeks if complete else final_weeks, games)
        if points is not None:
            pool.append({**player, 'points': points})
    overall = midranks(pool, 'points')
    positional = {pos: midranks([p for p in pool if p['position'] == pos], 'points') for pos in POSITIONS}
    player_map = {p['playerId']: p for p in pool}
    source_map = {p['playerId']: p for p in scoring.get('players', [])}
    team_map = {t['teamId']: t for t in league['standings']}
    n = len(team_map)
    picks = []
    for original in draft['picks']:
        pid = original['playerId']; meta = metadata.get(pid, {}); player = player_map.get(pid, {}); source = source_map.get(pid, {})
        team = team_map[original['teamId']]; mid, manager = identify(year, team, identities)
        pos = original.get('position') or source.get('position') or meta.get('position')
        picks.append({**original, 'season': year, 'team': {**{k: team.get(k) for k in ('teamId', 'name', 'logo')}, 'season': year}, 'managerId': mid, 'manager': manager,
                      'playerName': original.get('playerName') or source.get('name') or meta.get('name') or str(pid),
                      'position': pos, 'nflTeam': source.get('nflTeam'), 'headshot': meta.get('headshot'),
                      'rookie': rookie_status(meta, year), 'points': player.get('points'),
                      'overallRank': overall.get(pid) if valid else None, 'positionalRank': positional.get(pos, {}).get(pid) if valid else None,
                      'normalizedPick': round((original['overallPick'] - 1) / n + 1, 3),
                      'value': None, 'positionGain': None, 'overallGain': None, 'draftPositionRank': None, 'draftedFinishRank': None,
                      'finishPercentile': None, 'roundRank': None, 'roundScore': None, 'roundWinner': False, 'roundTopThree': False})
    if valid:
        for pos in POSITIONS:
            cohort = sorted([p for p in picks if p['position'] == pos and p['points'] is not None], key=lambda p: p['overallPick'])
            ranks = midranks(cohort, 'points'); size = len(cohort)
            for i, p in enumerate(cohort):
                gain = i + 1 - ranks[p['playerId']]
                p.update(draftPositionRank=i+1, draftedFinishRank=ranks[p['playerId']], positionGain=gain,
                         value=round(100 * gain / (size - 1), 3) if size > 1 else None,
                         finishPercentile=round(100 * (size - ranks[p['playerId']]) / (size - 1), 3) if size > 1 else None,
                         overallGain=p['overallPick'] - p['overallRank'])
        for rnd in sorted({p['round'] for p in picks}):
            cohort = [p for p in picks if p['round'] == rnd]
            # Every selection needs known points for a defensible round comparison.
            if any(p['points'] is None for p in cohort):
                continue
            ranks = midranks(cohort, 'points'); best = max(p['points'] for p in cohort)
            top_three = sorted((p['points'] for p in cohort), reverse=True)[min(2, len(cohort)-1)]
            for p in cohort:
                p.update(roundRank=ranks[p['playerId']], roundScore=round(100 * (len(cohort)-ranks[p['playerId']]) / max(1, len(cohort)-1), 3),
                         roundWinner=p['points'] == best, roundTopThree=p['points'] >= top_three)
    return {'season': year, 'complete': complete, 'performanceEligible': bool(valid), 'weeks': used_weeks, 'completedWeeks': final_weeks,
            'teamCount': n, 'draftCoverage': draft.get('coverage'), 'picks': picks, 'teams': aggregate(picks),
            'missingScores': sum(p['points'] is None for p in picks),
            'rounds': [{'round': rnd, 'picks': sorted([p for p in picks if p['round'] == rnd], key=lambda p: (p['roundRank'] or 1000, p['overallPick']))} for rnd in sorted({p['round'] for p in picks})]}


def build_draft_analysis(output='frontend/public/data', slug='pocky-football', years=None):
    root = Path(output) / slug
    read = lambda path: json.loads(path.read_text()) if path.exists() else {}
    identities = identity_lookup(read(ROOT / 'draft-manager-identities.json'))
    metadata = {p['espnId']: p for p in read(root/'players.json').get('players', [])}
    years = sorted(years or [int(p.name) for p in root.iterdir() if p.name.isdigit()])
    seasons = {str(y): analyze_season(y, read(root/f'{y}/league.json'), read(root/f'{y}/teams.json'), read(root/f'{y}/draft.json'),
                                    read(root/f'{y}/player-scoring.json'), read(root/f'{y}/player-games.json'), metadata, identities) for y in years}
    rows = [p for s in seasons.values() if s['performanceEligible'] for p in s['picks']]
    rookies = [p for p in rows if p['rookie'] is True]
    all_counts = {r['managerId']: r['picks'] for r in aggregate(rows)}
    rookie_teams = aggregate(rookies)
    for team in rookie_teams:
        team['rookieShare'] = round(100 * team['picks'] / all_counts[team['managerId']], 2)
    controlled = []
    for p in rookies:
        band = (p['round'] - 1) // 4
        controls = [q for q in rows if q['rookie'] is False and q['season'] == p['season'] and q['position'] == p['position'] and (q['round']-1)//4 == band and q['points'] is not None]
        if p['points'] is not None and len(controls) >= 3:
            controlled.append({'season': p['season'], 'overallPick': p['overallPick'], 'controls': len(controls), 'pointsAboveControl': round(p['points']-mean(q['points'] for q in controls), 2)})
    trends = {}
    for label, predicate in [('First-round performance', lambda p: p['round'] == 1), ('Early-round performance', lambda p: p['round'] <= 3), ('Late-round performance', lambda p: p['round'] >= 10)]:
        trends[label] = aggregate([p for p in rows if predicate(p)])
    summary = {'seasons': [int(y) for y, s in seasons.items() if s['performanceEligible']], 'teams': aggregate(rows),
               'positions': {pos: aggregate([p for p in rows if p['position'] == pos]) for pos in POSITIONS},
               'tendencies': tendencies(rows), 'rookies': {'picks': rookies, 'teams': rookie_teams, 'knownPicks': sum(p['rookie'] is not None for p in rows),
                    'unknownPicks': sum(p['rookie'] is None and p['position'] != 'D/ST' for p in rows), 'controls': controlled,
                    'averageControlDifference': avg([p['pointsAboveControl'] for p in controlled])}, 'trends': trends,
               'bestPicks': sorted([p for p in rows if p['value'] is not None], key=lambda p: (-p['value'], p['season'], p['overallPick'])),
               'worstPicks': sorted([p for p in rows if p['value'] is not None], key=lambda p: (p['value'], p['season'], p['overallPick']))}
    data = {'schemaVersion': 1, 'years': list(reversed(years)), 'seasons': seasons, 'summary': summary}
    from football_exporter import write_json
    # Store canonical picks once; all leaderboard/round evidence uses compact references.
    def compact(value):
        if isinstance(value, dict):
            if 'playerId' in value and 'overallPick' in value and 'season' in value:
                return {'pickRef': [value['season'], value['overallPick']]}
            return {k: compact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [compact(v) for v in value]
        return value
    saved = compact(data)
    for year, season in seasons.items():
        saved['seasons'][year]['picks'] = season['picks']
    write_json(root/'draft-analysis.json', saved)
    return data


if __name__ == '__main__':
    build_draft_analysis()
