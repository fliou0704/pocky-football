"""Reproducible weekly stories from normalized snapshots; never requests ESPN."""
import json
from collections import defaultdict
from pathlib import Path
from football_team_of_week import numeric
from football_draft_analysis import identity_lookup


def match_id(year, match):
    return f"{year}-{match['week']}-" + '-'.join(map(str, sorted((match['homeTeamId'], match['awayTeamId']))))


def valid(match):
    return (match['status'] == 'final' and match.get('homeTeamId') is not None
            and match.get('awayTeamId') is not None and match['homeTeamId'] != match['awayTeamId']
            and all(numeric(match.get(s+'Score')) for s in ('home', 'away')))


def derive(seasons, identities, details=None):
    """One chronological pass. History is keyed by verified manager, never team ID."""
    history = defaultdict(lambda: [0, 0, 0])
    results = {}
    for year, (league, data) in sorted(seasons.items()):
        teams = {t['teamId']: t for t in league['standings']}
        ids = set(teams)
        managers = {tid: identities[(year, tid)][0] for tid, t in teams.items()
                    if (year, tid) in identities and identities[(year, tid)][2] == t.get('owner')}
        allplay = {str(tid): dict(wins=0, losses=0, ties=0) for tid in ids}
        streak = dict.fromkeys(ids, 0)
        wins = dict.fromkeys(ids, 0)
        known_start = dict.fromkeys(ids, True)
        weeks, previews, excluded = {}, {}, []
        regular = league['league']['regularSeasonWeeks']
        previous_week = 0
        for week in sorted({m['week'] for m in data['matchups']}):
            if week <= regular and week != previous_week + 1:
                streak = dict.fromkeys(ids, 0)
                known_start = dict.fromkeys(ids, False)
            previous_week = week
            matches = [m for m in data['matchups'] if m['week'] == week]
            # Reject duplicate games and partial league coverage rather than fabricate ranks.
            participants = [m[s+'TeamId'] for m in matches for s in ('home', 'away') if m.get(s+'TeamId') is not None]
            unique = len(participants) == len(set(participants))
            finals = [m for m in matches if valid(m)] if unique else []
            complete = unique and bool(finals) and all(valid(m) or m['status'] == 'bye' for m in matches) and set(participants) == ids
            scores = {m[s+'TeamId']: m[s+'Score'] for m in finals for s in ('home', 'away')}
            indicators = {}
            for m in matches:
                a, b = m['homeTeamId'], m['awayTeamId']
                if a not in ids or b not in ids or a == b:
                    continue
                labels = []
                if week <= regular and streak[a] >= 3 and streak[b] >= 3:
                    labels.append('Hot Streak Showdown')
                # Only use explicitly archived entering-week official rankings.
                ranks = data.get('enteringWeekRanks', {}).get(str(week), {})
                if week > 1 and {ranks.get(str(a)), ranks.get(str(b))} == {1, 2}:
                    labels.append('Top Two Showdown')
                ma, mb = managers.get(a), managers.get(b)
                if ma and mb and ma != mb:
                    w, l, t = history[(ma, mb)]
                    if w == l and w+l+t > 0:
                        labels.append(f'Rivalry Tied {w}–{l}' + (f'–{t}' if t else ''))
                if m['status'] in ('upcoming', 'live') and labels:
                    indicators[match_id(year, m)] = labels
            previews[str(week)] = indicators
            stories = []
            for tid in sorted(ids):
                games = [m for m in matches if tid in (m['homeTeamId'], m['awayTeamId'])]
                if not unique or len(games) != 1 or not valid(games[0]):
                    streak[tid] = 0
                    if not (len(games) == 1 and games[0]['status'] == 'bye'):
                        known_start[tid] = False
                    continue
                m = games[0]
                won = m.get('winnerTeamId') == tid
                if won:
                    if wins[tid] == 0 and known_start[tid]:
                        stories.append({'teamId': tid, 'kind': 'firstWin'})
                    wins[tid] += 1
                if week <= regular:
                    streak[tid] = streak[tid]+1 if won else 0
                    if streak[tid] >= 3:
                        stories.append({'teamId': tid, 'kind': 'streak', 'count': streak[tid]})
            if week <= regular:
                if complete and set(scores) == ids:
                    for tid, score in scores.items():
                        for other, other_score in scores.items():
                            if tid != other:
                                key = 'wins' if score > other_score else 'losses' if score < other_score else 'ties'
                                allplay[str(tid)][key] += 1
                else:
                    excluded.append(week)
            if complete:
                leaderboard = sorted(({'teamId': t, 'points': s} for t, s in scores.items()), key=lambda r: (-r['points'], r['teamId']))
                for row in leaderboard:
                    row['rank'] = 1 + sum(r['points'] > row['points'] for r in leaderboard)
                awards = {}
                competitive = [m for m in finals if week <= regular or m.get('bracket') == 'championship']
                closest = min(competitive, key=lambda m: (abs(m['homeScore']-m['awayScore']), match_id(year, m))) if competitive else None
                def award(m, label):
                    key = match_id(year, m)
                    awards.setdefault(key, {'id': key, 'match': m, 'labels': []})['labels'].append(label)
                if closest:
                    award(closest, 'Closest Matchup')
                # Ambiguous ties at either of the top two places are deliberately omitted.
                if set(scores) == ids and len(leaderboard) >= 2 and leaderboard[0]['points'] > leaderboard[1]['points'] and (len(leaderboard) == 2 or leaderboard[1]['points'] > leaderboard[2]['points']):
                    top = {r['teamId'] for r in leaderboard[:2]}
                    for m in finals:
                        if {m['homeTeamId'], m['awayTeamId']} == top:
                            award(m, 'Top Two Scorers')
                roster = (details or {}).get((year, week), {}).get('teams', {})
                players = [dict(p, teamId=int(t)) for t, rows in roster.items() for p in rows if numeric(p.get('points'))]
                players.sort(key=lambda p: (-p['points'], p['playerId']))
                seen, top_players = set(), []
                for p in players:
                    if p['playerId'] not in seen:
                        seen.add(p['playerId'])
                        top_players.append(dict(p, bench=p.get('slot') in ('BE', 'BN', 'IR')))
                weeks[str(week)] = {'week': week, 'phase': 'regular' if week <= regular else 'playoffs', 'topTeam': leaderboard[0], 'leaderboard': leaderboard,
                                   'topPlayers': top_players[:5], 'awards': list(awards.values()), 'stories': stories}
            # Add actual final meetings only after calculating the pregame indicators.
            seen = set()
            for m in finals:
                key = match_id(year, m)
                if key in seen:
                    continue
                seen.add(key)
                ma, mb = managers.get(m['homeTeamId']), managers.get(m['awayTeamId'])
                if not ma or not mb or ma == mb:
                    continue
                winner = m.get('winnerTeamId')
                result = 2 if winner is None else 0 if winner == m['homeTeamId'] else 1
                history[(ma, mb)][result] += 1
                history[(mb, ma)][2 if result == 2 else 1-result] += 1
        results[year] = {'schemaVersion': 1, 'season': year, 'allPlay': allplay, 'excludedAllPlayWeeks': excluded,
                         'weeks': weeks, 'previews': previews,
                         'rules': {'topTwo': 'Requires unique first and second scores; ambiguous ties omitted.',
                                   'rivalry': 'Verified managers; actual prior regular and playoff meetings; W–L–T includes ties.',
                                   'rankings': 'Top Two Showdown requires archived official entering-week ranks; omitted when unavailable.'}}
    return results


def capture_entering_ranks(league, data, previous=None):
    """Archive ESPN's official rank only if standings contain exactly prior results.

    This cannot reconstruct official historical tiebreakers. A midweek snapshot is
    eligible only while standings W/L/T and PF still match all prior final games.
    """
    archived = dict((previous or {}).get('enteringWeekRanks', {}))
    if not league['league']['complete']:
        weeks = sorted({m['week'] for m in data['matchups'] if m['status'] in ('live', 'upcoming')})
        if weeks:
            week = weeks[0]
            prior = [m for m in data['matchups'] if m['week'] < week and m['phase'] == 'regular']
            current = [m for m in data['matchups'] if m['week'] == week]
            if week > 1 and week <= league['league']['regularSeasonWeeks'] and prior and all(valid(m) for m in prior) and not any(m['status'] == 'final' for m in current):
                reliable = True
                for t in league['standings']:
                    games = [m for m in prior if t['teamId'] in (m['homeTeamId'], m['awayTeamId'])]
                    w = sum(m['winnerTeamId'] == t['teamId'] for m in games)
                    ties = sum(m['winnerTeamId'] is None for m in games)
                    points = sum(m['homeScore'] if m['homeTeamId'] == t['teamId'] else m['awayScore'] for m in games)
                    reliable &= (t['wins'], t['losses'], t['ties']) == (w, len(games)-w-ties, ties) and abs(t['pointsFor']-points) < .02
                if reliable:
                    archived.setdefault(str(week), {str(t['teamId']): t['rank'] for t in league['standings']})
    if archived:
        data['enteringWeekRanks'] = archived


def weekly_contracts(output='frontend/public/data', slug='pocky-football', years=None):
    from football_exporter import ROOT
    root = Path(output)/slug
    years = years or json.loads((Path(output)/'site.json').read_text())['seasons']
    read = lambda path: json.loads(path.read_text())
    seasons = {y: (read(root/str(y)/'league.json'), read(root/str(y)/'teams.json')) for y in years}
    details = {(y, int(p.stem)): read(p) for y in years for p in (root/str(y)/'lineups').glob('*.json')}
    return derive(seasons, identity_lookup(read(ROOT/'draft-manager-identities.json')), details)


def build_weekly(output='frontend/public/data', slug='pocky-football', years=None):
    from football_exporter import write_json
    root = Path(output)/slug
    results = weekly_contracts(output, slug, years)
    for y, value in results.items():
        write_json(root/str(y)/'weekly.json', value)
    return results


if __name__ == '__main__':
    build_weekly()
