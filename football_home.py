"""Football weekly Home data, separate from the stable standings contract."""

import math


BRACKET = {
    "NONE": "regular",
    "WINNERS_BRACKET": "championship",
    "WINNERS_CONSOLATION_LADDER": "placement",
    "LOSERS_CONSOLATION_LADDER": "consolation",
}


def phase_for(week, regular_weeks, complete):
    if complete:
        return "offseason"
    return "playoffs" if week > regular_weeks else "regular"


def matchup(match, week, completed, live_scores=None, winner_state=None):
    home = getattr(getattr(match, "home_team", None), "team_id", None)
    away = getattr(getattr(match, "away_team", None), "team_id", None)
    scores = live_scores if live_scores is not None else (match.home_score, match.away_score)
    home_score = round(float(scores[0]), 2) if home is not None else None
    away_score = round(float(scores[1]), 2) if away is not None else None
    if home is None and away is None:
        raise ValueError("ESPN matchup has no teams")
    if away is None or home is None:
        status = "bye"
    elif completed or winner_state in ("HOME", "AWAY", "TIE"):
        status = "final"
    elif home_score or away_score:
        status = "live"
    else:
        status = "upcoming"
    winner = None
    if status == "final":
        if winner_state in ("HOME", "AWAY"):
            winner = home if winner_state == "HOME" else away
        elif winner_state != "TIE" and home_score != away_score:
            winner = home if home_score > away_score else away
    return {
        "week": week,
        "homeTeamId": home,
        "awayTeamId": away,
        "homeScore": home_score,
        "awayScore": away_score,
        "status": status,
        "bracket": BRACKET.get(match.matchup_type, "other"),
        "winnerTeamId": winner,
    }


def current_matchups(league, week):
    """ESPN's basic scoreboard omits live totals; use mMatchupScore's live fields."""
    raw = league.espn_request.league_get(params={"view": "mMatchupScore"})
    records = {}
    for item in raw["schedule"]:
        if item.get("matchupPeriodId") != week:
            continue
        key = (item.get("home", {}).get("teamId"), item.get("away", {}).get("teamId"))
        if key in records:
            raise ValueError("Duplicate current matchup from ESPN")
        records[key] = item
    result = []
    for match in league.scoreboard(week):
        key = (getattr(getattr(match, "home_team", None), "team_id", None),
               getattr(getattr(match, "away_team", None), "team_id", None))
        item = records.get(key)
        if item is None:
            raise ValueError("Current matchup missing from ESPN score response")
        home = item.get("home", {})
        away = item.get("away", {})
        scores = (home.get("totalPointsLive", home.get("totalPoints", match.home_score)),
                  away.get("totalPointsLive", away.get("totalPoints", match.away_score)))
        result.append(matchup(match, week, False, scores, item.get("winner")))
    return result


def top_players(boxes):
    players = []
    for box in boxes:
        for team, lineup in ((box.home_team, box.home_lineup), (box.away_team, box.away_lineup)):
            team_id = getattr(team, "team_id", None)
            if team_id is None:
                continue
            for player in lineup:
                if player.points is None or not math.isfinite(float(player.points)):
                    continue
                players.append({
                    "playerId": player.playerId,
                    "name": player.name,
                    "teamId": team_id,
                    "points": round(float(player.points), 2),
                    "slot": player.slot_position,
                    "bench": player.slot_position in ("BE", "IR"),
                })
    players.sort(key=lambda player: (-player["points"], player["playerId"]))
    seen = set()
    result = []
    for player in players:
        if player["playerId"] in seen:
            continue
        seen.add(player["playerId"])
        result.append(player)
        if len(result) == 5:
            break
    return result


def build_home(league, standings):
    current_week = int(league.currentMatchupPeriod)
    regular_weeks = int(league.settings.reg_season_count)
    final_week = len(league.settings.matchup_periods)
    complete = int(league.scoringPeriodId) > int(league.finalScoringPeriod)
    last_completed = min(current_week, final_week) if complete else max(0, current_week - 1)
    phase = phase_for(current_week, regular_weeks, complete)
    current_matches = [] if complete else current_matchups(league, current_week)
    recap = None
    if last_completed:
        matches = [matchup(m, last_completed, True) for m in league.scoreboard(last_completed)]
        competitive = [m for m in matches if m["status"] == "final" and (last_completed <= regular_weeks or m["bracket"] == "championship")]
        top = None
        if competitive:
            sides = [(m[side + "TeamId"], m[side + "Score"]) for m in competitive for side in ("home", "away")]
            top = {"teamId": max(sides, key=lambda side: (side[1], -side[0]))[0], "points": max(score for _, score in sides)}
        closest = min(competitive, key=lambda m: abs(m["homeScore"] - m["awayScore"])) if competitive else None
        boxes = league.box_scores(last_completed)
        recap = {
            "week": last_completed,
            "phase": "playoffs" if last_completed > regular_weeks else "regular",
            "topTeam": top,
            "closestMatchup": closest,
            "topPlayers": top_players(boxes),
            "matches": matches if last_completed > regular_weeks else [],
        }
    return {
        "schemaVersion": 1,
        "season": league.year,
        "state": {
            "phase": phase,
            "currentWeek": None if complete else current_week,
            "lastCompletedWeek": last_completed or None,
            "regularSeasonWeeks": regular_weeks,
        },
        "currentMatchups": current_matches,
        "recap": recap,
    }


def validate_home(home, standings):
    if home["season"] != standings["league"]["season"]:
        raise ValueError("Home season differs from standings season")
    ids = {team["teamId"] for team in standings["standings"]}
    state = home["state"]
    if state["phase"] not in ("regular", "playoffs", "offseason"):
        raise ValueError("Invalid Home phase")
    if state["regularSeasonWeeks"] < 1:
        raise ValueError("Invalid regular season length")
    for match in home["currentMatchups"] + (home["recap"]["matches"] if home["recap"] else []) + ([home["recap"]["closestMatchup"]] if home["recap"] and home["recap"]["closestMatchup"] else []):
        for side in ("home", "away"):
            team_id = match[side + "TeamId"]
            score = match[side + "Score"]
            if team_id is not None and team_id not in ids:
                raise ValueError("Matchup contains unknown team ID")
            if score is not None and not math.isfinite(score):
                raise ValueError("Matchup contains invalid score")
        if match["status"] not in ("upcoming", "live", "final", "bye"):
            raise ValueError("Matchup has invalid status")
    if home["recap"]:
        top = home["recap"]["topTeam"]
        if top and top["teamId"] not in ids:
            raise ValueError("Recap top team is unknown")
        for player in home["recap"]["topPlayers"]:
            if player["teamId"] not in ids or not math.isfinite(player["points"]):
                raise ValueError("Recap player is invalid")
