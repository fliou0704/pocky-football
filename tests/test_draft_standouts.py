import copy
import json
import unittest
from pathlib import Path
from football_draft_standouts import round_standouts, compare_methods

ROOT = Path(__file__).resolve().parents[1]


def committed_seasons():
    data = json.loads((ROOT/'frontend/public/data/pocky-football/draft-analysis.json').read_text())
    seasons = data['seasons']
    lookup = {(p['season'], p['overallPick']): p for s in seasons.values() for p in s['picks']}
    for season in seasons.values():
        for round_ in season['rounds']:
            round_['picks'] = [lookup[tuple(p['pickRef'])] for p in round_['picks']]
    return seasons


class DraftStandouts(unittest.TestCase):
    def pick(self, pid, overall, gain, finish, points=100, position='RB'):
        return {'playerId': pid, 'overallPick': overall, 'draftPositionGain': gain,
                'positionalRank': finish, 'points': points, 'position': position}

    def test_elite_first_overall_keeps_excellence_recognition_with_zero_gain(self):
        first = self.pick(1, 1, 0, 1, 500)
        later = self.pick(2, 10, 5, 2, 300, 'WR')
        result = round_standouts([first, later], True)
        self.assertEqual(result['valueLeaders'], [later])
        self.assertEqual(result['finishLeaders'], [first])
        self.assertEqual(result['relativeGainPercent'], 50)

    def test_early_qb_success_is_recognized_without_raw_points_deciding_value(self):
        qb = self.pick(1, 20, 0, 2, 400, 'QB')
        wr = self.pick(2, 28, 10, 3, 280, 'WR')
        result = round_standouts([qb, wr], True)
        self.assertEqual(result['finishLeaders'], [qb])
        self.assertEqual(result['valueLeaders'], [wr])
        result2 = round_standouts([qb, {**wr, 'positionalRank': 1}], True)
        self.assertEqual(result2['finishLeaders'][0]['playerId'], 2)

    def test_actual_2025_round_three_jsn_allen_mcbride(self):
        season = committed_seasons()['2025']
        picks = next(r['picks'] for r in season['rounds'] if r['round'] == 3)
        result = round_standouts(picks, True)
        winner = result['valueLeaders'][0]
        self.assertEqual(winner['playerName'], 'Jaxon Smith-Njigba')
        self.assertEqual((winner['overallPick'], winner['draftPositionGain']), (30, 27))
        self.assertEqual(result['relativeGainPercent'], 90)
        self.assertEqual({p['playerName'] for p in result['finishLeaders']}, {'Josh Allen', 'Trey McBride'})
        allen = next(p for p in picks if p['playerName'] == 'Josh Allen')
        self.assertEqual((allen['overallPick'], allen['draftPositionGain']), (26, 1))

    def test_missing_benchmark_uses_separate_finish_component_without_inventing_value(self):
        missing = self.pick(1, 150, None, 25, 20, 'D/ST')
        result = round_standouts([missing], True)
        self.assertEqual(result['valueLeaders'], [])
        self.assertEqual(result['finishLeaders'], [missing])
        self.assertEqual(result['missingBenchmarks'], 1)
        self.assertIsNone(result['relativeGainPercent'])
        self.assertIsNone(missing['draftPositionGain'])

    def test_ties_are_shared_and_do_not_use_raw_points_as_tiebreaker(self):
        picks = [self.pick(1, 20, 10, 1, 400), self.pick(2, 30, 15, 1, 200, 'TE')]
        result = round_standouts(picks, True)
        self.assertEqual(result['valueLeaders'], picks)
        self.assertEqual(result['finishLeaders'], picks)

    def test_no_mutation_provisional_and_unknown_points(self):
        picks = [self.pick(1, 1, 0, 1)]
        original = copy.deepcopy(picks)
        self.assertEqual(round_standouts(picks, False)['valueLeaders'], [])
        self.assertEqual(round_standouts([{**picks[0], 'points': None}], True)['status'], 'missing_scores')
        round_standouts(picks, True)
        self.assertEqual(picks, original)

    def test_all_completed_rounds_and_actual_early_busts(self):
        seasons = committed_seasons(); rows = compare_methods(seasons)
        self.assertEqual(len(rows), 80)
        changed = sum({p['playerId'] for p in row['rawGainLeaders']} != {p['playerId'] for p in row['valueLeaders']} for row in rows)
        self.assertEqual(changed, 8)
        for season in seasons.values():
            for round_ in season['rounds']:
                picks = round_['picks']; result = round_standouts(picks, season['performanceEligible'])
                self.assertEqual(len({p['playerId'] for p in picks}), len(picks))
                for p in result['valueLeaders'] + result['finishLeaders']:
                    self.assertEqual(p['team']['season'], season['season'])
                    self.assertIn(p, picks)
                self.assertEqual([p['overallPick'] for p in picks], sorted(p['overallPick'] for p in picks))
        # Real zero-gain positional champion is not lost behind the value award.
        round1 = next(r for r in rows if r['season'] == 2023 and r['round'] == 1)
        cmc = next(p for p in round1['finishLeaders'] if p['playerName'] == 'Christian McCaffrey')
        self.assertEqual(cmc['draftPositionGain'], 0)
        # 2024's injured first overall pick has no made-up positional benchmark.
        bust = seasons['2024']['picks'][0]
        self.assertIsNone(bust['draftPositionGain'])
        self.assertNotIn(bust['playerId'], {p['playerId'] for p in next(r for r in rows if r['season']==2024 and r['round']==1)['valueLeaders']})
