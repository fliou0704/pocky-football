import unittest
from types import SimpleNamespace as NS

from football_home import build_home, current_matchups, matchup, phase_for, validate_home


def team(team_id):
    return NS(team_id=team_id)


def match(home=1, away=2, scores=(100, 95), kind="NONE"):
    value = NS(home_team=team(home), home_score=scores[0], away_score=scores[1], matchup_type=kind)
    if away is not None:
        value.away_team = team(away)
    return value


class HomeTests(unittest.TestCase):
    def setUp(self):
        self.standings = {"league": {"season": 2026}, "standings": [{"teamId": 1}, {"teamId": 2}]}

    def test_current_regular_week_and_completed_recap(self):
        player = NS(playerId=20, name="Player", points=21.5, slot_position="WR")
        box = NS(home_team=team(1), away_team=team(2), home_lineup=[player], away_lineup=[])
        league = NS(year=2026, currentMatchupPeriod=3, scoringPeriodId=3, finalScoringPeriod=17,
                    settings=NS(reg_season_count=14, matchup_periods={str(i): [i] for i in range(1, 18)}),
                    scoreboard=lambda week: [match(scores=(0, 0))] if week == 3 else [match()],
                    box_scores=lambda week: [box],
                    espn_request=NS(league_get=lambda params: {"schedule": [{"matchupPeriodId": 3,
                        "home": {"teamId": 1, "totalPointsLive": 0},
                        "away": {"teamId": 2, "totalPointsLive": 0}, "winner": "UNDECIDED"}]}))
        home = build_home(league, self.standings)
        validate_home(home, self.standings)
        self.assertEqual(home["state"]["phase"], "regular")
        self.assertEqual(home["state"]["lastCompletedWeek"], 2)
        self.assertEqual(home["currentMatchups"][0]["status"], "upcoming")
        self.assertEqual(home["recap"]["topPlayers"][0]["points"], 21.5)

    def test_in_progress_uses_live_scores_not_basic_scoreboard_zeroes(self):
        league = NS(scoreboard=lambda week: [match(scores=(0, 0))],
                    espn_request=NS(league_get=lambda params: {"schedule": [{"matchupPeriodId": 3,
                        "home": {"teamId": 1, "totalPoints": 0, "totalPointsLive": 75.64},
                        "away": {"teamId": 2, "totalPoints": 0, "totalPointsLive": 155.34},
                        "winner": "UNDECIDED"}]}))
        result = current_matchups(league, 3)[0]
        self.assertEqual(result["status"], "live")
        self.assertEqual((result["homeScore"], result["awayScore"]), (75.64, 155.34))
        self.assertIsNone(result["winnerTeamId"])

    def test_espn_winner_marks_current_matchup_final(self):
        result = matchup(match(scores=(0, 0)), 3, False, (100.5, 90.25), "HOME")
        self.assertEqual(result["status"], "final")
        self.assertEqual(result["winnerTeamId"], 1)

    def test_completed_playoff_bye_and_offseason(self):
        bye = matchup(match(1, None, (120, 0), "WINNERS_BRACKET"), 15, True)
        self.assertEqual(bye["status"], "bye")
        self.assertIsNone(bye["awayTeamId"])
        self.assertEqual(bye["bracket"], "championship")
        self.assertEqual(phase_for(15, 14, False), "playoffs")
        self.assertEqual(phase_for(17, 14, True), "offseason")

    def test_completed_tie_has_no_winner(self):
        result = matchup(match(scores=(100, 100)), 2, True)
        self.assertEqual(result["status"], "final")
        self.assertIsNone(result["winnerTeamId"])

    def test_unknown_team_is_rejected(self):
        home = {"season": 2026, "state": {"phase": "regular", "regularSeasonWeeks": 14},
                "currentMatchups": [matchup(match(1, 99), 3, False)], "recap": None}
        with self.assertRaisesRegex(ValueError, "unknown team"):
            validate_home(home, self.standings)


if __name__ == "__main__":
    unittest.main()
