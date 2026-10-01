import unittest
from types import SimpleNamespace as NS

from football_history import lineup_entry, former_players, owner_name, playoff_labels, roster_history, schedule_presentation


class HistoryTests(unittest.TestCase):
    def test_historical_lineup_actual_week_and_slots(self):
        entry = {'playerId': 17, 'lineupSlotId': 23, 'playerPoolEntry': {'player': {
            'fullName': 'Sample', 'proTeamId': 2, 'defaultPositionId': 2,
            'stats': [{'scoringPeriodId': 4, 'statSourceId': 1, 'statSplitTypeId': 1, 'appliedTotal': 20},
                      {'scoringPeriodId': 3, 'statSourceId': 0, 'statSplitTypeId': 1, 'appliedTotal': 30},
                      {'scoringPeriodId': 4, 'statSourceId': 0, 'statSplitTypeId': 1, 'appliedTotal': 12.125}]}}}
        result = lineup_entry(entry, 4)
        self.assertEqual(result['slot'], 'FLEX')
        self.assertEqual(result['points'], 12.12)
        self.assertEqual(result['name'], 'Sample')
        self.assertEqual(result['position'], 'RB')
        entry['playerPoolEntry']['player']['defaultPositionId'] = 3
        self.assertEqual(lineup_entry(entry, 4)['position'], 'WR')
        self.assertIsNone(lineup_entry(entry, 5)['points'])
        entry['lineupSlotId'] = 20
        self.assertEqual(lineup_entry(entry, 4)['slot'], 'BE')
        entry['lineupSlotId'] = 21
        self.assertEqual(lineup_entry(entry, 4)['slot'], 'IR')

    def test_owner_override_real_name_and_display_fallback(self):
        owner = {"firstName": "Ada", "lastName": "Lovelace", "displayName": "username"}
        self.assertEqual(owner_name(owner, {}, 2025, 3), "Ada Lovelace")
        self.assertEqual(owner_name(owner, {"2025": {"3": "Chosen Name"}}, 2025, 3), "Chosen Name")
        self.assertEqual(owner_name({"displayName": "Visible"}, {}, 2025, 3), "Visible")

    def test_rounds_byes_and_consolation_with_different_season_structure(self):
        def match(week, home, away, bracket, winner=None, bye=False):
            return {"week": week, "homeTeamId": home, "awayTeamId": away, "bracket": bracket,
                    "winnerTeamId": winner, "status": "bye" if bye else "final"}
        games = [match(12, 1, None, "championship", bye=True),
                 match(12, 3, 6, "championship", 3), match(12, 4, 5, "championship", 5),
                 match(13, 1, 3, "championship", 1), match(13, 2, 5, "championship", 2),
                 match(13, 4, 6, "placement", 4),
                 match(14, 1, 2, "championship", 1),
                 match(14, 3, 5, "placement", 3), match(14, 4, 6, "placement", 4),
                 match(14, 7, 8, "consolation", 7)]
        playoff_labels(games, 11, 6)
        self.assertEqual([games[i]["roundLabel"] for i in (0, 1, 3, 6, 7, 8, 9)],
                         ["Playoff Bye — First Round", "Playoffs — First Round", "Playoffs — Semifinal",
                          "Championship", "Third Place", "Winners Consolation", "Losers Consolation"])
        self.assertTrue(games[0]["isBye"])

    def test_elimination_presentation_preserves_path_and_third_place(self):
        weeks = [
            {"week": 15, "bracket": "championship", "isPlayoff": True, "result": "L", "roundLabel": "Playoffs — First Round"},
            {"week": 16, "bracket": "placement", "isPlayoff": True, "result": "W", "roundLabel": "Winners Consolation"},
            {"week": 17, "bracket": "placement", "isPlayoff": True, "result": "W", "roundLabel": "Third Place"},
        ]
        schedule_presentation(weeks)
        self.assertEqual([w["displayRoundLabel"] for w in weeks], ["Playoffs — First Round", "Eliminated", "Third Place"])
        self.assertEqual(weeks[1]["roundLabel"], "Winners Consolation")

    def test_weekly_rosters_dedupe_and_player_moving_teams(self):
        def side(team_id, player_ids):
            return {"teamId": team_id, "rosterForCurrentScoringPeriod": {"entries": [
                {"playerId": player_id, "playerPoolEntry": {"player": {"fullName": f"Player {player_id}"}}}
                for player_id in player_ids]}}
        def get(params, headers):
            week = params["scoringPeriodId"]
            home = side(1, [10, 20] if week == 1 else [20])
            away = side(2, [30] if week == 1 else [10, 30])
            return {"schedule": [{"home": home, "away": away}]}
        league = NS(settings=NS(matchup_periods={1: [1], 2: [2]}), espn_request=NS(league_get=get))
        history = roster_history(league, 2)
        self.assertEqual(former_players(history, 1, [{"playerId": 20}]),
                         [{"playerId": 10, "name": "Player 10", "weeks": [1]}])
        self.assertEqual(former_players(history, 2, [{"playerId": 30}]),
                         [{"playerId": 10, "name": "Player 10", "weeks": [2]}])
        self.assertEqual(history[1][20]["weeks"], {1, 2})


if __name__ == "__main__":
    unittest.main()
