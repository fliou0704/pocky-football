import unittest
import json
from pathlib import Path
from types import SimpleNamespace as NS

from football_seasons import build_season, validate_season


def team(team_id, rank, name=None):
    player = NS(playerId=100 + team_id, name="Player", proTeam="MIN", position="WR",
                lineupSlot="WR", injuryStatus="ACTIVE", total_points=42.5)
    bench = NS(playerId=200 + team_id, name="Bench", proTeam="DET", position="RB",
               lineupSlot="BE", injuryStatus="QUESTIONABLE", total_points=12.0)
    return NS(team_id=team_id, team_name=name or f"Team {team_id}", team_abbrev="TST",
              logo_url=None, owners=[{"displayName": "Owner"}], standing=rank,
              final_standing=2 if rank == 1 else 1, division_name="East" if rank == 1 else "West",
              wins=1, losses=0, ties=0, points_for=120.5, points_against=100.25,
              roster=[player, bench])


def league(complete):
    schedule = [
        {"matchupPeriodId": 1, "home": {"teamId": 1, "totalPoints": 120.5},
         "away": {"teamId": 9, "totalPoints": 100.25}, "winner": "HOME", "playoffTierType": "NONE"},
        {"matchupPeriodId": 2, "home": {"teamId": 1, "totalPoints": 0, "totalPointsLive": 25},
         "away": {"teamId": 9, "totalPoints": 0, "totalPointsLive": 12},
         "winner": "UNDECIDED", "playoffTierType": "NONE"},
        {"matchupPeriodId": 3, "home": {"teamId": 1, "totalPoints": 125},
         "winner": "UNDECIDED", "playoffTierType": "WINNERS_BRACKET"},
    ]
    if complete:
        schedule[1]["home"]["totalPoints"] = 90
        schedule[1]["away"]["totalPoints"] = 90
        schedule[1]["winner"] = "TIE"
    request = NS(league_get=lambda params, headers=None: {"schedule": schedule if headers is None else []})
    return NS(league_id=123, year=2025 if complete else 2026,
              scoringPeriodId=5 if complete else 2, finalScoringPeriod=3,
              currentMatchupPeriod=3 if complete else 2,
              settings=NS(reg_season_count=2, name="League", playoff_team_count=2, matchup_periods={1:[1],2:[2],3:[3]}),
              teams=[team(1, 1), team(9, 2)], espn_request=request)


class SeasonTests(unittest.TestCase):
    def build(self, complete):
        return build_season(league(complete), {"season": 2026}, "test", lambda url: None)

    def test_active_standings_live_week_and_current_roster(self):
        standings, teams = self.build(False)
        self.assertFalse(standings["league"]["complete"])
        self.assertIsNone(standings["standings"][0]["finalRank"])
        self.assertEqual(standings["standings"][0]["pointsFor"], 120.5)
        self.assertEqual(standings["standings"][0]["pointsAgainst"], 100.25)
        self.assertEqual(teams["teams"]["1"]["roster"][0]["group"], "starter")
        self.assertEqual(teams["teams"]["1"]["roster"][1]["group"], "bench")
        self.assertEqual(teams["teams"]["1"]["weeks"][0]["scoreRank"], 1)
        self.assertEqual(teams["teams"]["1"]["weeks"][1]["status"], "live")

    def test_completed_regular_rank_final_finish_tie_and_playoff_bye(self):
        standings, teams = self.build(True)
        self.assertEqual(standings["standings"][0]["rank"], 1)
        self.assertEqual(standings["standings"][0]["finalRank"], 2)
        self.assertEqual(teams["teams"]["1"]["weeks"][1]["result"], "T")
        bye = teams["teams"]["1"]["weeks"][2]
        self.assertEqual((bye["result"], bye["opponentTeamId"], bye["phase"]), ("BYE", None, "playoffs"))
        self.assertEqual(teams["teams"]["1"]["rosterLabel"], "Final Roster")
        validate_season(standings, teams)

    def test_current_logo_override_does_not_replace_historical_team(self):
        config = {"season": 2026, "teamLogoOverrides": {"1": "team-logos/team-1.png"}}
        current, _ = build_season(league(False), config, "test", lambda url: None)
        historical, _ = build_season(league(True), config, "test", lambda url: None)
        self.assertEqual(current["standings"][0]["logo"], "team-logos/team-1.png")
        self.assertIsNone(historical["standings"][0]["logo"])

    def test_generated_current_and_historical_contracts(self):
        root = Path(__file__).resolve().parents[1] / "frontend/public/data/pocky-football"
        seasons = {}
        for year in (2021, 2022, 2025, 2026):
            folder = root / str(year)
            standings = json.loads((folder / "league.json").read_text())
            teams = json.loads((folder / "teams.json").read_text())
            validate_season(standings, teams)
            self.assertEqual(standings["league"]["season"], year)
            seasons[year] = {row["teamId"] for row in standings["standings"]}
            if year < 2026:
                self.assertTrue(standings["league"]["complete"])
                self.assertTrue(all(row["finalRank"] is not None for row in standings["standings"]))
                self.assertTrue(any(match["status"] == "bye" for match in teams["matchups"]))
                self.assertTrue(all(data["rosterLabel"] == "Final Roster" and data["roster"] for data in teams["teams"].values()))
                self.assertTrue(any(data["formerPlayers"] for data in teams["teams"].values()))
                self.assertIn("Championship", {match["roundLabel"] for match in teams["matchups"]})
            else:
                self.assertFalse(standings["league"]["complete"])
                self.assertTrue(all(row["finalRank"] is None for row in standings["standings"]))
                self.assertTrue(any(data["roster"] for data in teams["teams"].values()))
        self.assertNotEqual(seasons[2021], seasons[2026])
        self.assertEqual(len(seasons[2022]), 14)


if __name__ == "__main__":
    unittest.main()
