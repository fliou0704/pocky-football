import unittest
from football_draft_analysis import (
    midranks, rookie_status, identity_lookup, identify, season_points,
    analyze_season, aggregate, tendencies, build_summary, scoring_details,
)


class DraftAnalysisTests(unittest.TestCase):
    def fixture(self, complete=True):
        league = {'league': {'complete': complete}, 'standings': [
            {'teamId': 1, 'name': 'A', 'owner': 'Alice'},
            {'teamId': 2, 'name': 'B', 'owner': 'Bob'}]}
        teams = {'matchups': [{'week': 1, 'status': 'final'}]}
        draft = {'coverage': {'complete': True}, 'picks': [
            {'playerId': i, 'playerName': str(i), 'overallPick': i,
             'teamId': 1 if i % 2 else 2, 'round': (i-1)//2+1,
             'pickInRound': (i-1) % 2+1, 'position': 'QB' if i <= 2 else 'RB'}
            for i in range(1, 5)]}
        scoring = {'weeks': [1], 'players': [
            {'playerId': i, 'position': 'QB' if i <= 2 else 'RB', 'pointsByWeek': {'1': value}}
            for i, value in [(1, 200), (2, 300), (3, 10), (4, 20), (5, 400)]]}
        return [2025, league, teams, draft, scoring, {}, {}, {}]

    def test_ties_use_average_ranks_and_keep_zero(self):
        self.assertEqual(midranks([{'playerId': 1, 'points': 0}, {'playerId': 2, 'points': 10},
                                   {'playerId': 3, 'points': 10}], 'points'), {2: 1.5, 3: 1.5, 1: 3})

    def test_missing_is_not_zero(self):
        player = {'playerId': 1, 'pointsByWeek': {'1': 0}, 'nflTeamsByWeek': {'1': 'BUF'}}
        self.assertIsNone(season_points(player, [1, 2], {}))
        self.assertEqual(season_points(player, [1], {}), 0)
        self.assertEqual(season_points(player, [1, 2], {'players': {'1': {'2': {'played': False}}}}), 0)
        self.assertIsNone(season_points(player, [1, 2], {'players': {'1': {'2': {'played': True}}}}))
        self.assertIsNone(season_points({'playerId': 99}, [1], {}))

    def test_game_record_recovers_positive_and_zero_scores(self):
        for points in (11.4, 0):
            games = {'players': {'1': {'1': {'played': True, 'points': points}}}}
            detail = scoring_details({'playerId': 1}, [1], games)
            self.assertEqual(detail['points'], points)
            self.assertEqual(detail['evidence'][0]['reason'], 'actual_game_score')

    def test_source_coverage_required_before_treating_absent_actual_as_no_production(self):
        player = {'playerId': 1, 'pointsByWeek': {'1': 10}}
        self.assertIsNone(season_points(player, [1, 2], {}))
        games = {'weeks': [1, 2], 'coverage': {'playersWithActualSeasonRecords': ['1']},
                 'players': {'1': {'1': {'points': 10}}}}
        detail = scoring_details(player, [1, 2], games)
        self.assertEqual(detail['points'], 10)
        self.assertEqual(detail['evidence'][0]['reason'], 'covered_no_actual_record')
        games['weeks'] = [1]
        self.assertIsNone(season_points(player, [1, 2], games))

    def test_conflicting_fallback_is_not_silently_accepted(self):
        player = {'playerId': 1, 'pointsByWeek': {'1': 10}}
        self.assertIsNone(season_points(player, [1], {'players': {'1': {'1': {'points': 20}}}}))

    def test_canceled_game_and_bye_are_recovered_from_historical_schedule(self):
        schedule = [{'week': w, 'home': 'BUF', 'away': 'CIN', 'kickoff': 1,
                     'canceled': w == 17} for w in range(1, 19) if w != 7]
        games = {'weeks': list(range(1, 19)), 'games': schedule,
                 'coverage': {'playersWithActualSeasonRecords': ['1']}}
        player = {'playerId': 1, 'pointsByWeek': {'1': 10}, 'nflTeamsByWeek': {'1': 'BUF'}}
        detail = scoring_details(player, [1, 7, 17], games)
        self.assertEqual(detail['points'], 10)
        self.assertEqual([e['reason'] for e in detail['evidence']], ['schedule_bye', 'canceled_game'])

    def test_explicit_invalid_weekly_value_is_not_a_zero(self):
        games = {'weeks': [1], 'coverage': {'playersWithActualSeasonRecords': ['1']}}
        self.assertIsNone(season_points({'playerId': 1, 'pointsByWeek': {'1': None}}, [1], games))

    def test_rookies_require_rookie_metadata(self):
        self.assertTrue(rookie_status({'rookieSeason': 2025}, 2025))
        self.assertFalse(rookie_status({'rookieSeason': 2021}, 2025))
        for metadata in ({'nflDraft': None}, {'rookieSeason': 2026}, {'entityType': 'team_defense'}):
            self.assertIsNone(rookie_status(metadata, 2025))

    def test_identity_does_not_follow_reused_team_id(self):
        config = {'managers': {'alice': {'name': 'Alice', 'memberships': [
            {'season': 2025, 'teamId': 1, 'expectedOwner': 'Alice'}]}}}
        identities = identity_lookup(config)
        self.assertEqual(identify(2025, {'teamId': 1, 'name': 'A', 'owner': 'Alice'}, identities)[0], 'alice')
        self.assertNotEqual(identify(2026, {'teamId': 1, 'name': 'B', 'owner': 'Bob'}, identities)[0], 'alice')
        self.assertNotEqual(identify(2025, {'teamId': 1, 'name': 'B', 'owner': 'Bob'}, identities)[0], 'alice')
        config['managers']['alice']['memberships'] *= 2
        with self.assertRaises(ValueError):
            identity_lookup(config)

    def test_positional_and_overall_movement_include_undrafted_players(self):
        picks = analyze_season(*self.fixture())['picks']
        self.assertEqual([p['draftPositionRank'] for p in picks], [1, 2, 1, 2])
        self.assertEqual([p['positionalRank'] for p in picks], [2, 1, 3, 2])
        self.assertEqual([p['positionalMovement'] for p in picks], [-1, 1, -2, 0])
        self.assertEqual([p['overallMovement'] for p in picks], [-2, 0, -2, 0])
        self.assertTrue(all('value' not in p and 'draftedFinishRank' not in p for p in picks))
        rb = aggregate([p for p in picks if p['position'] == 'RB'], 'averageMovement')
        self.assertEqual(rb[0]['averageMovement'], 0)
        self.assertEqual(rb[1]['totalMovement'], -2)

    def test_original_order_is_preserved_independent_of_round_ranking(self):
        args = self.fixture(); args[3]['picks'].reverse()
        data = analyze_season(*args)
        self.assertEqual([p['overallPick'] for p in data['picks']], [1, 2, 3, 4])
        self.assertEqual([p['overallPick'] for p in data['rounds'][0]['picks']], [1, 2])
        self.assertEqual([p['roundRank'] for p in data['rounds'][0]['picks']], [2, 1])
        self.assertEqual(data['rounds'][0]['leaders'][0]['overallPick'], 2)

    def test_incomplete_season_withholds_final_ranks_and_movement(self):
        data = analyze_season(*self.fixture(False))
        self.assertFalse(data['performanceEligible'])
        self.assertEqual(data['picks'][0]['points'], 200)
        self.assertEqual(data['picks'][0]['draftPositionRank'], 1)
        for pick in data['picks']:
            for key in ('positionalMovement', 'overallMovement', 'positionalRank', 'roundRank'):
                self.assertIsNone(pick[key])
            self.assertEqual(pick['evaluationStatus'], 'provisional')

    def test_missing_pick_does_not_shift_other_positional_draft_orders(self):
        args = self.fixture(); args[4]['players'] = args[4]['players'][1:]
        data = analyze_season(*args)
        self.assertIsNone(data['picks'][0]['points'])
        self.assertEqual(data['picks'][0]['scoringStatus'], 'missing_player_scoring_source')
        self.assertIsNone(data['picks'][1]['roundRank'])
        self.assertEqual(data['picks'][1]['draftPositionRank'], 2)
        self.assertEqual(data['picks'][1]['positionalMovement'], 1)
        self.assertEqual(data['picks'][2]['roundRank'], 2)

    def test_tied_round_winners_and_volume_independent_averages(self):
        args = self.fixture(); args[4]['players'][0]['pointsByWeek']['1'] = 300
        picks = analyze_season(*args)['picks']
        self.assertTrue(all(p['roundWinner'] for p in picks[:2]))
        self.assertEqual(picks[0]['roundRank'], 1.5)
        self.assertEqual([r['averageMovement'] for r in aggregate(picks)],
                         [r['averageMovement'] for r in aggregate(picks+picks)])

    def test_unused_nfl_week_is_excluded(self):
        args = self.fixture(); args[4]['players'][0]['pointsByWeek']['18'] = 999
        self.assertEqual(analyze_season(*args)['picks'][0]['points'], 200)

    def test_conflicts_withhold_performance(self):
        args = self.fixture(); args[4]['coverage'] = {'conflicts': [{'playerId': 1}]}
        self.assertFalse(analyze_season(*args)['performanceEligible'])

    def test_first_position_selection_gets_one_vote_per_season(self):
        picks = analyze_season(*self.fixture())['picks']
        picks[1]['managerId'] = picks[0]['managerId']
        rows = tendencies(picks)['QB']
        self.assertEqual(rows[0]['picks'], 2)
        self.assertEqual(len(rows[0]['evidence']), 1)

    def test_active_manager_filter_is_applied_to_every_summary_but_not_seasons(self):
        data = analyze_season(*self.fixture())
        active_id = data['picks'][0]['managerId']
        summary = build_summary({'2025': data}, {active_id}, 2026)
        self.assertEqual(len(data['teams']), 2)  # inactive manager remains in the year
        self.assertEqual({r['managerId'] for r in summary['teams']}, {active_id})
        groups = [*summary['positions'].values(), *summary['tendencies'].values(),
                  *summary['trends'].values(), summary['rookies']['teams'], *summary['rookies']['positions'].values()]
        self.assertTrue(all(r['managerId'] == active_id for rows in groups for r in rows))
        self.assertTrue(all('averageMovement' not in row for row in summary['teams']))

    def test_negative_defense_ids_and_zero_scores_are_eligible(self):
        args = self.fixture(); args[3]['picks'][0].update(playerId=-16001, position='D/ST')
        args[4]['players'][0].update(playerId=-16001, position='D/ST', pointsByWeek={'1': 0})
        pick = analyze_season(*args)['picks'][0]
        self.assertEqual(pick['points'], 0)
        self.assertEqual(pick['positionalRank'], 1)
        self.assertEqual(pick['positionalMovement'], 0)


if __name__ == '__main__':
    unittest.main()
