"""Offline H2H calculations from the existing normalized season snapshots."""
from itertools import combinations
import json
import math
from pathlib import Path


def summary(rows):
    return {'wins': sum(r['result'] == 'W' for r in rows),
            'losses': sum(r['result'] == 'L' for r in rows),
            'ties': sum(r['result'] == 'T' for r in rows), 'total': len(rows)}


def valid_score(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def pair_view(seasons, first, second):
    historical, theoretical = [], []
    for year, (league, data) in seasons.items():
        teams = {t['teamId']: t for t in league['standings']}
        if first not in teams or second not in teams:
            continue
        def row(week, a_score, b_score, winner, playoff=False, label=None, actual=False):
            return {'season': year, 'week': week, 'teamAId': first, 'teamBId': second,
                    'teamA': {k: teams[first][k] for k in ('teamId', 'name', 'logo')},
                    'teamB': {k: teams[second][k] for k in ('teamId', 'name', 'logo')},
                    'teamAScore': a_score, 'teamBScore': b_score,
                    'result': 'T' if winner is None else 'W' if winner == first else 'L',
                    'isPlayoff': playoff, 'roundLabel': label, 'actualMeeting': actual}
        actual_weeks = set()
        for match in data['matchups']:
            if match['status'] != 'final' or match.get('isBye') or match['homeTeamId'] == match['awayTeamId']:
                continue
            if {match['homeTeamId'], match['awayTeamId']} != {first, second}:
                continue
            home = match['homeTeamId'] == first
            a, b = (match['homeScore'], match['awayScore']) if home else (match['awayScore'], match['homeScore'])
            if not valid_score(a) or not valid_score(b):
                continue
            historical.append(row(match['week'], a, b, match['winnerTeamId'],
                                  match['isPlayoff'], match['roundLabel'], True))
            actual_weeks.add(match['week'])
        def scores(team_id):
            return {w['week']: w['score'] for w in data['teams'][str(team_id)]['weeks']
                    if w['phase'] == 'regular' and w['status'] == 'final' and not w.get('isBye') and valid_score(w['score'])}
        left, right = scores(first), scores(second)
        for week in left.keys() & right.keys():
            a, b = left[week], right[week]
            theoretical.append(row(week, a, b, first if a > b else second if b > a else None,
                                   actual=week in actual_weeks))
    for rows in (historical, theoretical):
        rows.sort(key=lambda r: (r['season'], r['week']), reverse=True)
    def view(rows):
        years = sorted({r['season'] for r in rows}, reverse=True)
        return {'teamAId': first, 'teamBId': second, 'summary': summary(rows), 'rows': rows,
                'seasons': years, 'seasonSummaries': {str(y): summary([r for r in rows if r['season'] == y]) for y in years}}
    history = view(historical)
    history['regularSummary'] = summary([r for r in historical if not r['isPlayoff']])
    history['playoffSummary'] = summary([r for r in historical if r['isPlayoff']])
    return {'historical': history, 'theoretical': view(theoretical)}


def build_h2h(output, slug, years, current_year):
    from football_exporter import write_json
    root = Path(output) / slug
    seasons = {year: (json.loads((root / str(year) / 'league.json').read_text()),
                      json.loads((root / str(year) / 'teams.json').read_text())) for year in years}
    teams = [{k: t[k] for k in ('teamId', 'name', 'logo')} for t in seasons[current_year][0]['standings']]
    for first, second in combinations(sorted(t['teamId'] for t in teams), 2):
        forward, reverse = pair_view(seasons, first, second), pair_view(seasons, second, first)
        write_json(root / 'h2h' / f'{first}-{second}.json', {'schemaVersion': 1,
                   **{mode: {str(first): forward[mode], str(second): reverse[mode]} for mode in ('historical', 'theoretical')}})
    write_json(root / 'h2h.json', {'schemaVersion': 1, 'teams': teams, 'supportedSeasons': sorted(years, reverse=True),
               'pairPath': f'{slug}/h2h/', 'theoreticalRule': 'Final regular-season scores from the same season and week only.'})
