"""Precomputed football records from existing normalized seasons and weekly lineups."""
from collections import Counter, defaultdict
from fractions import Fraction
import json
import math
from pathlib import Path

SLOT_ORDER = ('QB', 'RB', 'WR', 'TE', 'FLEX', 'D/ST', 'K', 'OP')
STARTERS = {'QB', 'RB', 'WR', 'TE', 'FLEX', 'RB/WR/TE', 'D/ST', 'K', 'OP'}
POSITIONS = ('QB', 'RB', 'WR', 'TE', 'D/ST', 'K')


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def identity(team):
    return {key: team[key] for key in ('teamId', 'name', 'logo')}


def eligible(match):
    return (match['status'] == 'final' and not match.get('isBye')
            and match.get('awayTeamId') is not None and match['homeTeamId'] != match['awayTeamId']
            and numeric(match['homeScore']) and numeric(match['awayScore']))


def record(key, label, rows, minimum=False, unit='points', rule=None):
    """Preserve every exact tied holder with stable season/week/team/player ordering."""
    value = (min if minimum else max)((row['value'] for row in rows), default=None)
    holders = sorted((r for r in rows if r['value'] == value),
                     key=lambda r: (r['season'], r.get('week', r.get('endWeek', 0)),
                                    r['team']['teamId'], r.get('playerId', 0), r.get('slot', '')))
    return {'id': key, 'label': label, 'value': float(value) if value is not None else None,
            'unit': unit, 'rule': rule, 'holders': [{**h, 'value': float(h['value'])} for h in holders]}


def streak_rows(year, team, weeks):
    rows, run = [], []
    result = None
    def finish():
        if run:
            rows.append({'season': year, 'team': identity(team), 'value': len(run),
                         'startWeek': run[0], 'endWeek': run[-1], 'result': result})
    for week in sorted(weeks, key=lambda w: w['week']):
        if week['phase'] != 'regular':
            continue
        if week.get('isBye') or week['opponentTeamId'] in (None, team['teamId']):
            continue
        current = week['result'] if week['status'] == 'final' else None
        if current not in ('W', 'L') or current != result:
            finish(); run = []; result = current
        if current in ('W', 'L'):
            run.append(week['week'])
    finish()
    return rows


def season_candidates(year, league, data, lineups):
    teams = {t['teamId']: t for t in league['standings']}
    matches = [m for m in data['matchups'] if eligible(m)]
    regular = [m for m in matches if m['phase'] == 'regular']
    scheduled = [m for m in data['matchups'] if m['phase'] == 'regular' and not m.get('isBye')
                 and m.get('awayTeamId') is not None and m['homeTeamId'] != m['awayTeamId']]
    regular_complete = (bool(scheduled) and all(eligible(m) for m in scheduled)
                        and {m['week'] for m in scheduled} == set(range(1, league['league']['regularSeasonWeeks'] + 1)))
    weekly, margins, season_totals, seasons, streaks, players, starter_totals = [], [], [], [], [], [], defaultdict(list)
    for m in matches:
        for side, other in (('home', 'away'), ('away', 'home')):
            team_id, opponent_id = m[f'{side}TeamId'], m[f'{other}TeamId']
            weekly.append({'season': year, 'week': m['week'], 'team': identity(teams[team_id]),
                           'opponent': identity(teams[opponent_id]), 'value': m[f'{side}Score'],
                           'opponentScore': m[f'{other}Score'], 'isPlayoff': m['phase'] != 'regular',
                           'roundLabel': m.get('roundLabel')})
        winner = m.get('winnerTeamId')
        margin = round(abs(m['homeScore'] - m['awayScore']), 2)
        side = 'away' if winner == m['awayTeamId'] else 'home'
        other = 'home' if side == 'away' else 'away'
        margins.append({'season': year, 'week': m['week'], 'team': identity(teams[m[f'{side}TeamId']]),
                        'opponent': identity(teams[m[f'{other}TeamId']]), 'score': m[f'{side}Score'],
                        'opponentScore': m[f'{other}Score'], 'value': margin,
                        'isTie': winner is None, 'isPlayoff': m['phase'] != 'regular',
                        'roundLabel': m.get('roundLabel')})
    for team in teams.values():
        weeks = data['teams'][str(team['teamId'])]['weeks']
        streaks.extend(streak_rows(year, team, weeks))
        played = [w for w in weeks if w['phase'] == 'regular' and w['status'] == 'final'
                  and not w.get('isBye') and w['opponentTeamId'] not in (None, team['teamId'])
                  and numeric(w['score']) and numeric(w['opponentScore'])]
        if regular_complete and played:
            base = {'season': year, 'team': identity(team), 'games': len(played),
                    'wins': sum(w['result'] == 'W' for w in played),
                    'losses': sum(w['result'] == 'L' for w in played), 'ties': sum(w['result'] == 'T' for w in played)}
            season_totals.append({**base, 'value': round(sum(w['score'] for w in played), 2)})
            seasons.append({**base, 'value': Fraction(2 * base['wins'] + base['ties'], 2 * len(played))})
    seen = set(); missing_weeks = set(); missing_points = 0
    for m in matches:
        detail = lineups.get(m['week'])
        if detail is None:
            missing_weeks.add(m['week']); continue
        for side, other in (('home', 'away'), ('away', 'home')):
            team_id = m[f'{side}TeamId']; rows = detail.get('teams', {}).get(str(team_id))
            if not rows:
                missing_weeks.add(m['week']); continue
            for p in rows:
                key = (m['week'], team_id, p['playerId'])
                if key in seen:
                    continue
                seen.add(key)
                if not numeric(p['points']):
                    missing_points += 1; continue
                holder = {'season': year, 'week': m['week'], 'team': identity(teams[team_id]),
                          'opponent': identity(teams[m[f'{other}TeamId']]),
                          **{k: p[k] for k in ('playerId', 'name', 'nflTeam', 'position', 'slot')},
                          'value': p['points'], 'isPlayoff': m['phase'] != 'regular'}
                players.append(holder)
                if m['phase'] == 'regular' and p['slot'] in STARTERS:
                    starter_totals[p['playerId']].append(holder)
    mvps = []
    for contributions in starter_totals.values():
        latest = max(contributions, key=lambda p: p['week'])
        mvps.append({**latest, 'value': round(sum(p['value'] for p in contributions), 2),
                     'teams': [identity(teams[i]) for i in sorted({p['team']['teamId'] for p in contributions})]})
    championship = [m for m in matches if m['bracket'] == 'championship']
    final = max(championship, key=lambda m: m['week'], default=None)
    champion = (identity(teams[final['winnerTeamId']]) if league['league']['complete'] and final
                and final.get('winnerTeamId') in teams else None)
    # Use this season's observed lineup shape, rather than a fixed league size/roster.
    patterns = Counter(tuple(sorted((p['slot'] for p in rows if p['slot'] in STARTERS),
                                     key=lambda slot: SLOT_ORDER.index(slot) if slot in SLOT_ORDER else 99))
                       for detail in lineups.values() for rows in detail.get('teams', {}).values() if rows)
    slots = sorted(patterns, key=lambda slots:(-patterns[slots], slots))[0] if patterns else ()
    selected = set(); fantasy_team = []
    for slot in slots:
        positions = {'RB', 'WR', 'TE'} if slot in ('FLEX', 'RB/WR/TE') else set(POSITIONS) - {'D/ST', 'K'} if slot == 'OP' else {slot}
        available = [p for p in mvps if p['position'] in positions and p['playerId'] not in selected]
        if available:
            top = max(p['value'] for p in available)
            leaders = sorted((p for p in available if p['value'] == top), key=lambda p:p['playerId'])
            choice = leaders[0]; selected.add(choice['playerId'])
            fantasy_team.append({**choice, 'awardSlot': 'FLEX' if slot == 'RB/WR/TE' else slot,
                                 'tiedAlternates': [p for p in leaders[1:]]})
    return {'allFantasyTeam': fantasy_team, 'weekly': weekly, 'margins': margins, 'totals': season_totals, 'records': seasons,
            'streaks': streaks, 'players': players, 'mvps': mvps, 'champion': champion,
            'regularSeasonComplete': regular_complete, 'complete': league['league']['complete'],
            'missingLineupWeeks': sorted(missing_weeks), 'missingPlayerPoints': missing_points}


def view(candidates):
    collect = lambda key: [row for c in candidates.values() for row in c[key]]
    weekly, margins, totals, records, streaks, players = [collect(k) for k in ('weekly', 'margins', 'totals', 'records', 'streaks', 'players')]
    weekly_rule = 'Completed regular-season and playoff matchups; byes excluded.'
    season_rule = 'Completed regular seasons only; playoff points excluded.'
    team_records = [
        record('team-high', 'Highest Team Score', weekly, rule=weekly_rule),
        record('team-low', 'Lowest Team Score', weekly, minimum=True, rule=weekly_rule),
        record('margin-high', 'Largest Margin of Victory', [r for r in margins if not r['isTie']], rule=weekly_rule),
        record('margin-low', 'Closest Matchup', margins, minimum=True, rule=weekly_rule + ' Ties count as a zero-point margin.'),
        record('season-high', 'Most Points in a Season', totals, rule=season_rule),
        record('season-low', 'Fewest Points in a Season', totals, minimum=True, rule=season_rule),
        record('record-best', 'Best Regular-Season Record', records, unit='record', rule=season_rule + ' Ranked by win percentage; a tie counts as half a win.'),
        record('record-worst', 'Worst Regular-Season Record', records, minimum=True, unit='record', rule=season_rule + ' Ranked by win percentage; a tie counts as half a win.'),
        record('streak-win', 'Longest Winning Streak', [r for r in streaks if r['result'] == 'W'], unit='games', rule='Within one season, regular-season completed games only. Ties interrupt; byes do not count; unfinalized games interrupt.'),
        record('streak-loss', 'Longest Losing Streak', [r for r in streaks if r['result'] == 'L'], unit='games', rule='Within one season, regular-season completed games only. Ties interrupt; byes do not count; unfinalized games interrupt.'),
    ]
    player_records = [
        record('player-high', 'Highest Player Score in One Week', players, rule='All roster slots in completed matchups; missing actual points excluded.'),
        record('starter-high', 'Highest Starter Score in One Week', [p for p in players if p['slot'] in STARTERS], rule='Historical starter slots only; BE and IR excluded.'),
        record('bench-high', 'Highest Bench Score in One Week', [p for p in players if p['slot'] in ('BE', 'BN')], rule='Bench only; IR excluded.'),
    ]
    return {'teamRecords': team_records, 'playerRecords': player_records,
            'negativeStarterWeeks': sorted([p for p in players if p['slot'] in STARTERS and p['value'] < 0], key=lambda p:(-p['season'], -p['week'], p['team']['teamId'], p['playerId'])),
            'positionRecords': [record(f'position-{pos}', pos, [p for p in players if p['position'] == pos], rule='All roster slots in completed matchups.') for pos in POSITIONS],
            'champions': [{'season': y, 'team': c['champion']} for y, c in sorted(candidates.items()) if c['champion']],
            'mvp': record('mvp', 'Most Valuable Player', collect('mvps'), rule='Regular-season starter contributions to fantasy teams; excludes bench, IR and playoffs. Current season is season-to-date.'),
            'allFantasyTeam': next(iter(candidates.values()))['allFantasyTeam'] if len(candidates) == 1 else [],
            'coverage': [{'season': y, **{k:c[k] for k in ('complete', 'regularSeasonComplete', 'missingLineupWeeks', 'missingPlayerPoints')}} for y,c in sorted(candidates.items())]}


def build_record_book(output, slug, years):
    from football_exporter import write_json
    root = Path(output) / slug
    candidates = {}
    for year in years:
        folder = root / str(year)
        read = lambda path: json.loads(path.read_text())
        lineups = {int(p.stem): read(p) for p in (folder / 'lineups').glob('*.json')}
        candidates[year] = season_candidates(year, read(folder / 'league.json'), read(folder / 'teams.json'), lineups)
    payload = {'schemaVersion': 1, 'years': sorted(years, reverse=True), 'defaultYear': 'All-Time',
               'allTime': view(candidates), 'seasons': {str(y): view({y:candidates[y]}) for y in years}}
    write_json(root / 'record-book.json', payload)
    return payload
