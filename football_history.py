"""Small football-only interpretations of ESPN playoff and roster history data."""

import json
from collections import defaultdict


def owner_name(owner, overrides, year, team_id):
    configured = overrides.get(str(year), {}).get(str(team_id))
    if configured:
        return configured.strip()
    if not isinstance(owner, dict):
        return None
    full = " ".join(str(owner.get(key) or "").strip() for key in ("firstName", "lastName")).strip()
    return full or owner.get("displayName") or None


def playoff_labels(matchups, regular_weeks, playoff_teams):
    """Label by season round and prior winners-bracket progression."""
    winners = defaultdict(list)
    for match in matchups:
        if match["week"] > regular_weeks and match["bracket"] == "championship":
            winners[match["week"]].append(match)
    rounds = sorted(winners)
    semifinal_losers = set()
    if len(rounds) >= 2:
        for match in winners[rounds[-2]]:
            if match["awayTeamId"] is not None and match["winnerTeamId"] is not None:
                semifinal_losers.update({match["homeTeamId"], match["awayTeamId"]} - {match["winnerTeamId"]})
    for match in matchups:
        week = match["week"]
        if week <= regular_weeks:
            label = None
        elif match["status"] == "bye":
            label = "Playoff Bye — First Round" if rounds and week == rounds[0] else "Playoff Bye"
        elif match["bracket"] == "championship":
            if rounds and week == rounds[-1]:
                label = "Championship"
            elif len(rounds) >= 2 and week == rounds[-2]:
                label = "Playoffs — Semifinal"
            else:
                label = "Playoffs — First Round" if playoff_teams > 2 else "Playoffs"
        elif match["bracket"] == "placement":
            participants = {match["homeTeamId"], match["awayTeamId"]}
            label = "Third Place" if rounds and week == rounds[-1] and participants <= semifinal_losers else "Winners Consolation"
        elif match["bracket"] == "consolation":
            label = "Losers Consolation"
        else:
            label = "Playoffs"
        match["roundLabel"] = label
        match["isPlayoff"] = week > regular_weeks
        match["isBye"] = match["status"] == "bye"


def schedule_presentation(weeks):
    """Keep bracket labels intact; simplify games after loss/nonqualification."""
    eliminated = False
    for week in sorted(weeks, key=lambda row: row['week']):
        consolation = week['bracket'] in ('placement', 'consolation')
        # ESPN's losers ladder explicitly identifies teams outside the title bracket.
        if week['isPlayoff'] and week['bracket'] == 'consolation':
            eliminated = True
        week['displayRoundLabel'] = ('Eliminated' if eliminated and consolation
                                     and week['roundLabel'] != 'Third Place' else week['roundLabel'])
        if week['isPlayoff'] and week['bracket'] == 'championship' and week['result'] == 'L':
            eliminated = True


def lineup_entry(entry, week):
    from espn_api.football.constant import POSITION_MAP, PRO_TEAM_MAP
    player = (entry.get('playerPoolEntry') or {}).get('player') or {}
    actual = next((stat for stat in player.get('stats', []) if stat.get('scoringPeriodId') == week
                   and stat.get('statSourceId') == 0 and stat.get('statSplitTypeId') == 1), None)
    slot = POSITION_MAP.get(entry.get('lineupSlotId'), 'Unknown')
    return {'playerId': entry.get('playerId'), 'name': player.get('fullName', 'Unknown player'),
            'slot': {'RB/WR/TE': 'FLEX', 'BN': 'BE'}.get(slot, slot),
            'nflTeam': PRO_TEAM_MAP.get(player.get('proTeamId'), '—'),
            'position': {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 16: 'D/ST'}.get(player.get('defaultPositionId'), '—'),
            'points': round(float(actual['appliedTotal']), 2) if actual and actual.get('appliedTotal') is not None else None}


def roster_history(league, last_week, detail_writer=None):
    """Full weekly roster snapshots, including bench and IR, from ESPN scoreboard."""
    seen = defaultdict(lambda: defaultdict(lambda: {"weeks": set(), "name": None}))
    for week in range(1, last_week + 1):
        lineups = {}
        period = next((int(period) for period, weeks in league.settings.matchup_periods.items() if week in weeks), week)
        filters = {"schedule": {"filterMatchupPeriodIds": {"value": [period]}}}
        raw = league.espn_request.league_get(
            params={"view": ["mMatchupScore", "mScoreboard"], "scoringPeriodId": week},
            headers={"x-fantasy-filter": json.dumps(filters)},
        )
        for match in raw.get("schedule", []):
            for side in ("home", "away"):
                team = match.get(side) or {}
                team_id = team.get("teamId")
                if team_id is None:
                    continue
                roster = team.get("rosterForCurrentScoringPeriod") or {}
                if detail_writer is not None:
                    lineups[str(team_id)] = [lineup_entry(entry, week) for entry in roster.get('entries', [])]
                for entry in roster.get("entries", []):
                    player_id = entry.get("playerId")
                    player = (entry.get("playerPoolEntry") or {}).get("player") or {}
                    if player_id is None or not player.get("fullName"):
                        continue
                    record = seen[team_id][player_id]
                    record["weeks"].add(week)
                    record["name"] = player["fullName"]
        if detail_writer is not None:
            detail_writer(week, {'schemaVersion': 1, 'season': league.year, 'week': week, 'teams': lineups})
    return seen


def former_players(history, team_id, current_roster):
    current = {player["playerId"] for player in current_roster}
    return [{"playerId": player_id, "name": record["name"], "weeks": sorted(record["weeks"])}
            for player_id, record in sorted(history.get(team_id, {}).items(), key=lambda item: item[1]["name"])
            if player_id not in current]
