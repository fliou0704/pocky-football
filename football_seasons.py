"""Small, season-scoped football contracts for Standings, Teams, and future history views."""

from collections import defaultdict
import math

from football_home import BRACKET


def _number(value):
    result = round(float(value or 0), 2)
    if not math.isfinite(result):
        raise ValueError("Non-finite football score")
    return result


def _roster(team):
    rows = []
    for player in team.roster:
        slot = player.lineupSlot
        rows.append({
            "playerId": player.playerId,
            "name": player.name,
            "nflTeam": player.proTeam,
            "position": player.position,
            "slot": slot,
            "group": "ir" if slot == "IR" else "bench" if slot in ("BE", "BN") else "starter",
            "injuryStatus": player.injuryStatus,
            "seasonPoints": _number(player.total_points),
        })
    return rows


def build_season(league, config, slug, logo_resolver):
    complete = int(league.scoringPeriodId) > int(league.finalScoringPeriod)
    regular_weeks = int(league.settings.reg_season_count)
    teams = sorted(league.teams, key=lambda team: team.standing)
    ids = {team.team_id for team in teams}
    if len(ids) != len(teams) or sorted(team.standing for team in teams) != list(range(1, len(teams) + 1)):
        raise ValueError("Invalid season team identity or standings")
    # Team IDs can be reassigned across years. Current-season manual overrides must
    # not silently replace a different historical team's mark.
    overrides = config.get("teamLogoOverrides", {}) if league.year == config["season"] else {}
    team_rows = []
    for team in teams:
        owner = team.owners[0] if team.owners else None
        if not isinstance(owner, dict):
            owner = None
        team_rows.append({
            "teamId": team.team_id, "name": team.team_name,
            "abbreviation": team.team_abbrev,
            "logo": overrides.get(str(team.team_id)) or logo_resolver(team.logo_url),
            "owner": owner.get("displayName") if owner else None,
            "rank": team.standing, "finalRank": team.final_standing if complete and team.final_standing else None,
            "division": team.division_name or None,
            "wins": team.wins, "losses": team.losses, "ties": team.ties,
            "pointsFor": _number(team.points_for), "pointsAgainst": _number(team.points_against),
        })
    league_data = {
        "schemaVersion": 1,
        "league": {"id": league.league_id, "slug": slug, "sport": "football", "season": league.year,
                   "name": league.settings.name, "complete": complete,
                   "regularSeasonWeeks": regular_weeks, "playoffTeams": league.settings.playoff_team_count},
        "standings": team_rows,
    }

    raw = league.espn_request.league_get(params={"view": "mMatchupScore"})
    matchups = []
    seen = set()
    for item in raw["schedule"]:
        week = int(item["matchupPeriodId"])
        home = item.get("home", {})
        away = item.get("away", {})
        home_id, away_id = home.get("teamId"), away.get("teamId")
        if home_id not in ids or (away_id is not None and away_id not in ids):
            raise ValueError("Matchup refers to an unknown season team")
        if away_id == home_id:
            away_id = None
        key = (week, home_id, away_id)
        if key in seen:
            raise ValueError("Duplicate season matchup")
        seen.add(key)
        winner = item.get("winner")
        status = ("bye" if away_id is None else "final" if complete or winner in ("HOME", "AWAY", "TIE")
                  else "live" if week == int(league.currentMatchupPeriod) and
                  (_number(home.get("totalPointsLive")) or _number(away.get("totalPointsLive"))) else "upcoming")
        score_key = "totalPointsLive" if status == "live" else "totalPoints"
        home_score = _number(home.get(score_key)) if status in ("live", "final") else None
        away_score = _number(away.get(score_key)) if away_id is not None and status in ("live", "final") else None
        winner_id = (home_id if winner == "HOME" else away_id if winner == "AWAY" else None)
        if status == "final" and winner_id is None and winner != "TIE" and home_score != away_score:
            winner_id = home_id if home_score > away_score else away_id
        matchups.append({"week": week, "homeTeamId": home_id, "awayTeamId": away_id,
                         "homeScore": home_score, "awayScore": away_score, "status": status,
                         "winnerTeamId": winner_id, "bracket": BRACKET.get(item.get("playoffTierType"), "other"),
                         "phase": "regular" if week <= regular_weeks else "playoffs"})
    matchups.sort(key=lambda match: (match["week"], match["homeTeamId"]))
    weekly_scores = defaultdict(list)
    for match in matchups:
        if match["status"] == "bye":
            continue
        for side in ("home", "away"):
            weekly_scores[match["week"]].append((match[f"{side}TeamId"], match[f"{side}Score"]))
    rankings = {week: {team_id: 1 + sum(other_score > score for _, other_score in scores)
                       for team_id, score in scores} for week, scores in weekly_scores.items()
                if all(score is not None for _, score in scores)}
    team_data = {}
    for source, row in zip(teams, team_rows):
        team_id = row["teamId"]
        weeks = []
        wins = losses = ties = 0
        for match in matchups:
            if team_id not in (match["homeTeamId"], match["awayTeamId"]):
                continue
            home = team_id == match["homeTeamId"]
            opponent_id = match["awayTeamId"] if home else match["homeTeamId"]
            score = match["homeScore"] if home else match["awayScore"]
            opponent_score = match["awayScore"] if home else match["homeScore"]
            result = ("BYE" if match["status"] == "bye" else "—" if match["status"] != "final"
                      else "T" if match["winnerTeamId"] is None else "W" if match["winnerTeamId"] == team_id else "L")
            if match["phase"] == "regular" and result in ("W", "L", "T"):
                wins += result == "W"
                losses += result == "L"
                ties += result == "T"
            weeks.append({"week": match["week"], "opponentTeamId": opponent_id,
                          "score": score, "opponentScore": opponent_score, "result": result,
                          "status": match["status"], "phase": match["phase"], "bracket": match["bracket"],
                          "cumulativeRecord": {"wins": wins, "losses": losses, "ties": ties} if match["phase"] == "regular" and result in ("W", "L", "T") else None,
                          "scoreRank": rankings.get(match["week"], {}).get(team_id) if match["status"] == "final" else None})
        scored = [week["score"] for week in weeks if week["phase"] == "regular" and week["status"] == "final"]
        team_data[str(team_id)] = {"teamId": team_id, "weeks": weeks,
                                   "averageScore": round(sum(scored) / len(scored), 2) if scored else None,
                                   "highScore": max(scored) if scored else None,
                                   "lowScore": min(scored) if scored else None,
                                   "roster": _roster(source) if not complete else None}
    teams_data = {"schemaVersion": 1, "leagueId": league.league_id, "season": league.year,
                  "complete": complete, "teams": team_data, "matchups": matchups}
    validate_season(league_data, teams_data)
    return league_data, teams_data


def validate_season(league_data, teams_data):
    ids = {row["teamId"] for row in league_data["standings"]}
    if teams_data["season"] != league_data["league"]["season"] or set(map(int, teams_data["teams"])) != ids:
        raise ValueError("Season contracts disagree on teams")
    for match in teams_data["matchups"]:
        if match["homeTeamId"] not in ids or match["awayTeamId"] is not None and match["awayTeamId"] not in ids:
            raise ValueError("Invalid matchup team")
        if match["status"] == "bye" and match["awayTeamId"] is not None:
            raise ValueError("Invalid playoff bye")
        if match["homeTeamId"] == match["awayTeamId"]:
            raise ValueError("Self matchup")
