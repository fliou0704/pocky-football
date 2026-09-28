"""Read-only, bounded ESPN football object inspection. Never emits credentials."""

import json
import os
import hashlib
from pathlib import Path

from dotenv import load_dotenv
from espn_api.football import League


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)
LEAGUE_ID = 668411840
SEASON = int(os.environ.get("FOOTBALL_SEASON", "2025"))


def public_fields(obj):
    return sorted(k for k in vars(obj) if not k.startswith("_") and k not in {"espn_request", "logger"})


def safe_call(label, call):
    try:
        return call()
    except Exception as exc:
        print(json.dumps({"check": label, "errorType": type(exc).__name__}))
        return None


def team_summary(team):
    return {
        "id": team.team_id,
        "name": team.team_name,
        "abbreviation": team.team_abbrev,
        "ownerKeys": [hashlib.sha256(str(owner.get("id")).encode()).hexdigest()[:12] for owner in team.owners],
        "record": [team.wins, team.losses, team.ties],
        "points": [team.points_for, team.points_against],
        "standing": team.standing,
        "finalStanding": team.final_standing,
        "divisionId": team.division_id,
        "scheduleCount": len(team.schedule),
        "scoreCount": len(team.scores),
        "outcomeCounts": {value: team.outcomes.count(value) for value in set(team.outcomes)},
        "rosterCount": len(team.roster),
        "logoPresent": bool(team.logo_url),
    }


def player_summary(player):
    return {
        "fields": public_fields(player),
        "id": player.playerId,
        "name": player.name,
        "nflTeam": player.proTeam,
        "position": getattr(player, "position", None),
        "eligibleSlots": player.eligibleSlots,
        "lineupSlot": player.lineupSlot,
        "boxSlot": getattr(player, "slot_position", None),
        "injuryStatus": player.injuryStatus,
        "seasonPoints": player.total_points,
        "seasonProjected": player.projected_total_points,
        "statPeriods": sorted(str(k) for k in player.stats.keys())[:8],
        "statExampleKeys": sorted(next(iter(player.stats.values())).keys()) if player.stats else [],
        "boxPoints": getattr(player, "points", None),
        "boxProjected": getattr(player, "projected_points", None),
    }


def inspect_season(year):
    league = safe_call(f"connect-{year}", lambda: League(LEAGUE_ID, year, espn_s2=os.environ["ESPN_S2"], swid=os.environ["SWID"]))
    if league is None:
        return
    settings = league.settings
    print(json.dumps({
        "season": year,
        "leagueFields": public_fields(league),
        "leagueId": league.league_id,
        "leagueName": settings.name,
        "currentMatchupPeriod": league.currentMatchupPeriod,
        "currentWeek": league.current_week,
        "nflWeek": league.nfl_week,
        "previousSeasons": league.previousSeasons,
        "settingsFields": public_fields(settings),
        "regularWeeks": settings.reg_season_count,
        "matchupPeriodCount": len(settings.matchup_periods),
        "playoffTeamCount": settings.playoff_team_count,
        "divisions": settings.division_map,
        "scoringType": settings.scoring_type,
        "scoringFormatCount": len(settings.scoring_format),
        "scoringFormatExample": settings.scoring_format[:3],
        "positionSlotCounts": settings.position_slot_counts,
        "tieRule": settings.tie_rule,
        "playoffTieRule": settings.playoff_tie_rule,
        "playoffSeedTieRule": settings.playoff_seed_tie_rule,
        "playoffMatchupPeriodLength": settings.playoff_matchup_period_length,
        "teamFields": public_fields(league.teams[0]) if league.teams else [],
        "teams": [team_summary(t) for t in league.teams],
        "memberCount": len(league.members),
        "memberFields": sorted(league.members[0]) if league.members else [],
    }, default=str))
    if not league.teams:
        return
    roster = league.teams[0].roster
    if roster:
        print(json.dumps({"season": year, "rosterPlayer": player_summary(roster[0])}, default=str))
    for week in sorted({1, settings.reg_season_count, settings.reg_season_count + 1}):
        if week < 1 or week > len(settings.matchup_periods):
            continue
        matches = safe_call(f"scoreboard-{year}-{week}", lambda w=week: league.scoreboard(w))
        if matches is not None:
            print(json.dumps({"season": year, "week": week, "matchupCount": len(matches),
                "matchupFields": public_fields(matches[0]) if matches else [],
                "matchups": [{"homeId": getattr(getattr(m, "home_team", None), "team_id", None),
                    "awayId": getattr(getattr(m, "away_team", None), "team_id", None),
                    "homeScore": m.home_score, "awayScore": m.away_score,
                    "type": m.matchup_type, "isPlayoff": m.is_playoff} for m in matches[:4]]}, default=str))
        if week == 1:
            boxes = safe_call(f"box-{year}-{week}", lambda w=week: league.box_scores(w))
            if boxes:
                box = boxes[0]
                print(json.dumps({"season": year, "week": week, "boxFields": public_fields(box),
                    "homeId": getattr(getattr(box, "home_team", None), "team_id", None),
                    "awayId": getattr(getattr(box, "away_team", None), "team_id", None),
                    "scores": [box.home_score, box.away_score],
                    "projections": [box.home_projected, box.away_projected],
                    "lineupCounts": [len(box.home_lineup), len(box.away_lineup)],
                    "boxPlayer": player_summary(box.home_lineup[0]) if box.home_lineup else None}, default=str))
    activity = safe_call(f"activity-{year}", lambda: league.recent_activity(size=3))
    if activity is not None:
        print(json.dumps({"season": year, "activityCount": len(activity),
            "activityFields": public_fields(activity[0]) if activity else [],
            "activityActionTypes": [type(a.actions).__name__ for a in activity]}))


if __name__ == "__main__":
    missing = [key for key in ("ESPN_S2", "SWID") if not os.environ.get(key)]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
    else:
        inspect_season(SEASON)
        prior = int(os.environ.get("FOOTBALL_PRIOR_SEASON", str(SEASON - 1)))
        if prior != SEASON:
            inspect_season(prior)
