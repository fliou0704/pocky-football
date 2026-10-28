"""Offline, position-aware draft evaluation from normalized football snapshots."""
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

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


def previous_coverage_points(player, weeks, games):
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


def scoring_details(player, weeks, games):
    """Reconcile the same league-scored actual records used by the Players page.

    Covered season-record gaps mean no actual production (bye/DNP), as defined by
    football_player_games.game_state. An absent dataset/player is never coverage.
    """
    from football_player_games import game_state
    pid = str(player['playerId'])
    weekly = player.get('pointsByWeek', {})
    records = games.get('players', {}).get(pid, {})
    covered = (pid in games.get('coverage', {}).get('playersWithActualSeasonRecords', [])
               and set(weeks) <= set(games.get('weeks', [])))
    teams = {int(w): r.get('nflTeam') for w, r in records.items() if r.get('nflTeam')}
    teams.update({int(w): t for w, t in player.get('nflTeamsByWeek', {}).items() if t not in (None, '—', 'FA')})
    evidence = []; unresolved = []; total = 0
    for week in weeks:
        record = records.get(str(week))
        points = weekly.get(str(week))
        fallback = (record or {}).get('points')
        if number(points):
            if number(fallback) and abs(points - fallback) > .011:
                unresolved.append({'week': week, 'reason': 'conflicting_actual_scores'})
            else:
                total += points
            continue
        if number(fallback):
            total += fallback
            evidence.append({'week': week, 'reason': 'actual_game_score', 'points': fallback})
            continue
        if str(week) in weekly:
            unresolved.append({'week': week, 'reason': 'invalid_actual_score'})
            continue
        if record and record.get('played') is False:
            evidence.append({'week': week, 'reason': 'explicit_did_not_play', 'points': 0})
            continue
        nearest = min(teams, key=lambda w: (abs(w-week), w > week)) if teams else None
        team = teams.get(nearest)
        schedule = games.get('games', [])
        team_schedule = [g for g in schedule if team and team in (g['home'], g['away'])]
        if len({g['week'] for g in team_schedule}) >= 16:
            state = game_state(week, record, team, schedule, True,
                               defense=int(pid) < 0, source_covered=covered)
        else:
            # An absent/partial schedule cannot itself prove a bye.
            state = 'did_not_play' if record is None and covered else 'unknown'
        if state in ('bye', 'did_not_play'):
            scheduled = [g for g in games.get('games', []) if g['week'] == week and team in (g['home'], g['away'])]
            reason = ('canceled_game' if any(g.get('canceled') for g in scheduled)
                      else 'schedule_bye' if state == 'bye' else 'covered_no_actual_record')
            evidence.append({'week': week, 'reason': reason, 'points': 0})
        else:
            unresolved.append({'week': week, 'reason': 'played_without_score' if record else 'missing_actual_coverage'})
    # No selected weeks or no source evidence must not become a manufactured zero.
    if not weeks or not (weekly or records or covered):
        return {'points': None, 'evidence': evidence, 'unresolved': unresolved,
                'reason': 'missing_player_scoring_source'}
    return {'points': None if unresolved else round(total, 2), 'evidence': evidence,
            'unresolved': unresolved, 'reason': unresolved[0]['reason'] if unresolved else 'complete'}


def season_points(player, weeks, games):
    return scoring_details(player, weeks, games)['points']


def aggregate(rows, sort_by='roundScore'):
    """Separate round and position movement statistics; never combine positions into a score."""
    groups = defaultdict(list)
    for pick in rows:
        groups[pick['managerId']].append(pick)
    result = []
    for manager_id, picks in groups.items():
        eligible = [p for p in picks if p['positionalMovement'] is not None]
        rounds = [p for p in picks if p['roundScore'] is not None]
        last = max(picks, key=lambda p: p['season'])
        result.append({
            'managerId': manager_id, 'manager': last['manager'], 'team': last['team'],
            'seasons': sorted({p['season'] for p in picks}), 'picks': len(picks),
            'eligiblePicks': len(eligible), 'roundsEvaluated': len(rounds),
            'averageMovement': avg([p['positionalMovement'] for p in eligible]),
            'totalMovement': round(sum(p['positionalMovement'] for p in eligible), 3) if eligible else None,
            'averageRoundRank': avg([p['roundRank'] for p in rounds]),
            'roundScore': avg([p['roundScore'] for p in rounds]),
            'roundWins': sum(p['roundWinner'] for p in rounds),
            'averagePoints': avg([p['points'] for p in picks]),
            'averageDraftRound': avg([p['round'] for p in picks]),
            'averageNormalizedPick': avg([p['normalizedPick'] for p in picks]),
            'smallSample': len(eligible) < 10,
            'evidence': [{'season': p['season'], 'overallPick': p['overallPick']} for p in picks],
        })
    return sorted(result, key=lambda r: (-(r[sort_by] if r[sort_by] is not None else -1e9), r['managerId']))


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
    selected_weeks = used_weeks if complete else final_weeks
    source_map = {int(p['playerId']): p for p in scoring.get('players', [])}
    # Include game-record-only zero scorers and drafted IDs; metadata supplies identity,
    # never a fabricated score. Negative D/ST IDs remain signed ESPN identifiers.
    candidates = set(source_map) | {int(pid) for pid in games.get('players', {})} | {p['playerId'] for p in draft['picks']}
    details = {}; pool = []
    for pid in sorted(candidates):
        source = source_map.get(pid, {})
        pos = source.get('position') or scoring.get('playerPositions', {}).get(str(pid)) or metadata.get(pid, {}).get('position')
        player = {**source, 'playerId': pid, 'position': pos}
        detail = scoring_details(player, selected_weeks, games)
        details[pid] = detail
        if detail['points'] is not None and pos in POSITIONS:
            pool.append({**player, 'points': detail['points']})
    overall = midranks(pool, 'points')
    positional = {pos: midranks([p for p in pool if p['position'] == pos], 'points') for pos in POSITIONS}
    player_map = {p['playerId']: p for p in pool}
    team_map = {t['teamId']: t for t in league['standings']}
    n = len(team_map)
    picks = []
    for original in sorted(draft['picks'], key=lambda p: p['overallPick']):
        pid = original['playerId']; meta = metadata.get(pid, {}); player = player_map.get(pid, {}); source = source_map.get(pid, {})
        team = team_map[original['teamId']]; mid, manager = identify(year, team, identities)
        pos = original.get('position') or source.get('position') or meta.get('position')
        picks.append({**original, 'season': year, 'team': {**{k: team.get(k) for k in ('teamId', 'name', 'logo')}, 'season': year}, 'managerId': mid, 'manager': manager,
                      'playerName': original.get('playerName') or source.get('name') or meta.get('name') or str(pid),
                      'position': pos, 'nflTeam': source.get('nflTeam'), 'headshot': meta.get('headshot'),
                      'rookie': rookie_status(meta, year), 'points': details[pid]['points'],
                      'overallRank': overall.get(pid) if valid else None, 'positionalRank': positional.get(pos, {}).get(pid) if valid else None,
                      'normalizedPick': round((original['overallPick'] - 1) / n + 1, 3),
                      'positionalMovement': None, 'overallMovement': None, 'draftPositionRank': None,
                      'scoringStatus': details[pid]['reason'], 'scoreEvidence': details[pid]['evidence'],
                      'missingWeeks': details[pid]['unresolved'],
                      'evaluationStatus': ('missing_scoring' if details[pid]['points'] is None else 'unknown_position' if not player else 'final' if valid else 'provisional'),
                      'roundRank': None, 'roundScore': None, 'roundWinner': False})
    # Draft order includes every original selection at this position, even a
    # missing scorer. Final positional rank includes eligible UNDRAFTED players.
    for pos in POSITIONS:
        cohort = [p for p in picks if p['position'] == pos]
        for i, pick in enumerate(cohort):
            pick['draftPositionRank'] = i + 1
            if pick['positionalRank'] is not None:
                pick['positionalMovement'] = i + 1 - pick['positionalRank']
    if valid:
        for pick in picks:
            if pick['overallRank'] is not None:
                pick['overallMovement'] = pick['overallPick'] - pick['overallRank']
        for rnd in sorted({p['round'] for p in picks}):
            cohort = [p for p in picks if p['round'] == rnd]
            # Every selection needs known points for a defensible round comparison.
            if any(p['points'] is None for p in cohort):
                continue
            ranks = midranks(cohort, 'points'); best = max(p['points'] for p in cohort)
            for p in cohort:
                p.update(roundRank=ranks[p['playerId']], roundScore=round(100 * (len(cohort)-ranks[p['playerId']]) / max(1, len(cohort)-1), 3),
                         roundWinner=p['points'] == best)
    return {'season': year, 'complete': complete, 'performanceEligible': bool(valid), 'weeks': used_weeks, 'completedWeeks': final_weeks,
            'teamCount': n, 'draftCoverage': draft.get('coverage'), 'picks': picks, 'teams': round_aggregates(picks),
            'risers': sorted([p for p in picks if p['overallMovement'] is not None and p['overallMovement'] > 0], key=lambda p: (-p['overallMovement'], p['overallPick'])),
            'fallers': sorted([p for p in picks if p['overallMovement'] is not None and p['overallMovement'] < 0], key=lambda p: (p['overallMovement'], p['overallPick'])),
            'positions': {pos: {'teams': aggregate([p for p in picks if p['position'] == pos], 'averageMovement'),
                                'picks': [p for p in picks if p['position'] == pos]} for pos in POSITIONS},
            'missingScores': sum(p['points'] is None for p in picks),
            'rounds': [{'round': rnd, 'picks': [p for p in picks if p['round'] == rnd],
                        'leaders': [p for p in picks if p['round'] == rnd and p['roundWinner']]} for rnd in sorted({p['round'] for p in picks})]}


def round_aggregates(rows):
    return [{k: v for k, v in r.items() if k not in ('averageMovement', 'totalMovement')}
            for r in aggregate(rows)]


def build_summary(seasons, active_ids, latest):
    rows = [p for season in seasons.values() if season['performanceEligible']
            for p in season['picks'] if p['managerId'] in active_ids]
    rookies = [p for p in rows if p['rookie'] is True]
    rookie_teams = aggregate(rookies)
    for team in rookie_teams:
        team['rookieShare'] = round(100 * team['picks'] / sum(p['managerId'] == team['managerId'] for p in rows), 2)
    # Keep rookie analysis by position; do not average unrelated positional ranks.
    return {
        'activeSeason': latest, 'activeManagerIds': sorted(active_ids),
        'seasons': [s['season'] for s in seasons.values() if s['performanceEligible']],
        'teams': round_aggregates(rows),
        'positions': {pos: aggregate([p for p in rows if p['position'] == pos], 'averageMovement') for pos in POSITIONS},
        'tendencies': tendencies(rows),
        'rookies': {'teams': [{k: v for k, v in r.items() if k not in ('averageMovement', 'totalMovement')} for r in rookie_teams],
                    'positions': {pos: aggregate([p for p in rookies if p['position'] == pos], 'averageMovement') for pos in POSITIONS},
                    'count': len(rookies), 'unknownPicks': sum(p['rookie'] is None and p['position'] != 'D/ST' for p in rows)},
        'trends': {label: round_aggregates([p for p in rows if predicate(p)]) for label, predicate in [
            ('First-round performance', lambda p: p['round'] == 1),
            ('Late-round performance', lambda p: p['round'] >= 10)]},
    }


def build_audit(seasons, root, metadata):
    """Reproducible before/after evidence for every previously excluded selection."""
    rows = []; provisional = []
    for year, season in seasons.items():
        scoring = json.loads((root/f'{year}/player-scoring.json').read_text())
        games = json.loads((root/f'{year}/player-games.json').read_text())
        source = {p['playerId']: p for p in scoring.get('players', [])}
        for pick in season['picks']:
            pid = pick['playerId']; old = previous_coverage_points(source.get(pid, {}), season['weeks'], games)
            if not season['complete']:
                provisional.append({'season': int(year), 'overallPick': pick['overallPick'], 'reason': 'incomplete_season'})
            elif old is None:
                rows.append({'season': int(year), 'overallPick': pick['overallPick'], 'playerId': pid,
                             'playerName': pick['playerName'], 'position': pick['position'],
                             'scoringIdMatched': pid in source, 'metadataIdMatched': pid in metadata,
                             'fixed': pick['overallRank'] is not None, 'points': pick['points'],
                             'recoveredWeeks': pick['scoreEvidence'], 'unresolvedWeeks': pick['missingWeeks'],
                             'status': pick['evaluationStatus']})
    return {'previouslyUnevaluable': len(rows), 'fixed': sum(p['fixed'] for p in rows),
            'remaining': sum(not p['fixed'] for p in rows), 'picks': rows,
            'provisionalPicks': len(provisional),
            'scope': 'Previous coverage exclusions in completed seasons; incomplete seasons are separately provisional.'}


def build_draft_analysis(output='frontend/public/data', slug='pocky-football', years=None):
    root = Path(output) / slug
    read = lambda path: json.loads(path.read_text()) if path.exists() else {}
    identities = identity_lookup(read(ROOT / 'draft-manager-identities.json'))
    metadata = {p['espnId']: p for p in read(root/'players.json').get('players', [])}
    years = sorted(years or [int(p.name) for p in root.iterdir() if p.name.isdigit()])
    seasons = {str(y): analyze_season(y, read(root/f'{y}/league.json'), read(root/f'{y}/teams.json'), read(root/f'{y}/draft.json'),
                                    read(root/f'{y}/player-scoring.json'), read(root/f'{y}/player-games.json'), metadata, identities) for y in years}
    latest = max(years)
    active_ids = {identify(latest, team, identities)[0] for team in read(root/f'{latest}/league.json')['standings']}
    summary = build_summary(seasons, active_ids, latest)
    audit = build_audit(seasons, root, metadata)
    data = {'schemaVersion': 1, 'years': list(reversed(years)), 'seasons': seasons, 'summary': summary, 'audit': audit}
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
    write_json(root/'draft-scoring-audit.json', audit)
    return data


if __name__ == '__main__':
    build_draft_analysis()
