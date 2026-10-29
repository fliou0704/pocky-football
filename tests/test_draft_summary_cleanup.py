import copy
import json
import unittest
from pathlib import Path
from football_draft_analysis import build_summary, positional_benchmark, tendencies


class SummaryCleanup(unittest.TestCase):
    def pick(self, manager='a', season=2025, overall=10, round_=1, rank=2, position='QB', rookie=False):
        return {'managerId': manager, 'manager': manager.upper(), 'team': {'teamId': 1 if manager == 'a' else 2,
                'name': f'Old {manager}', 'logo': 'old.png', 'season': season}, 'season': season,
                'overallPick': overall, 'round': round_, 'roundRank': rank, 'position': position,
                'rookie': rookie, 'draftPositionGain': 33 if manager == 'a' else -10}

    def test_current_branding_and_historical_identity_aggregation_without_mutation(self):
        picks = [self.pick(season=2024), self.pick(overall=20), self.pick('b', overall=30, rookie=True)]
        seasons = {'2025': {'season': 2025, 'performanceEligible': True, 'picks': picks}}
        original = copy.deepcopy(seasons)
        branding = {'a': {'teamId': 1, 'name': 'Current A', 'logo': 'current.png', 'season': 2026},
                    'b': {'teamId': 2, 'name': 'Current B', 'logo': 'b.png', 'season': 2026}}
        summary = build_summary(seasons, {'a', 'b'}, 2026, branding)
        groups = [summary['teams'], *summary['positions'].values(), *summary['tendencies'].values(),
                  summary['rookies']['teams'], *summary['trends'].values()]
        for group in groups:
            for row in group:
                self.assertEqual(row['team'], branding[row['managerId']])
        self.assertEqual(summary['teams'][0]['picks'], 2)
        self.assertEqual(seasons, original)
        self.assertNotIn('timingComparison', summary)
        self.assertNotIn('rookieComparison', summary)
        self.assertNotIn('positions', summary['rookies'])

    def test_actual_average_round_rank_and_ascending_order(self):
        picks = [self.pick(rank=1), self.pick(overall=20, rank=9), self.pick('b', overall=30, rank=4)]
        result = build_summary({'2025': {'season': 2025, 'performanceEligible': True, 'picks': picks}}, {'a','b'}, 2026)
        self.assertEqual([r['managerId'] for r in result['teams']], ['b','a'])
        self.assertEqual(result['teams'][1]['averageRoundRank'], 5)
        self.assertEqual([r['averageRoundRank'] for r in result['trends']['Round 1']], [4,5])

    def test_actual_positional_reference_and_no_invented_pick(self):
        self.assertEqual(positional_benchmark(100, 5, [10,20,30,40,67,80,90,95,99,100]), (33,'available'))
        self.assertEqual(positional_benchmark(100, 11, [10,67,100]), (None,'beyond_drafted_position'))
        self.assertEqual(positional_benchmark(100, 2.5, [10,67,100]), (None,'fractional_tie'))

    def test_tendency_sorting_uses_requested_raw_metrics(self):
        picks = []
        for pos in ('QB','TE','RB','WR','K','D/ST'):
            picks.extend([self.pick(overall=40, round_=3, position=pos), self.pick('b',overall=50,round_=2,position=pos)])
        result = tendencies(picks)
        for pos in ('QB','TE'):
            self.assertEqual([r['managerId'] for r in result[pos]], ['a','b'])
        for pos in ('RB','WR','K','D/ST'):
            self.assertEqual([r['managerId'] for r in result[pos]], ['b','a'])
        self.assertEqual(result['QB'][0]['averageFirstPick'], 40)

    def test_rookie_count_sorting(self):
        picks = [self.pick('b',overall=10,rookie=True), self.pick(overall=20,rookie=True), self.pick(overall=30,rookie=True)]
        result = build_summary({'2025': {'season': 2025, 'performanceEligible': True, 'picks': picks}}, {'a','b'}, 2026)
        self.assertEqual([r['picks'] for r in result['rookies']['teams']], [2,1])

    def test_committed_contract_has_current_names_and_ascending_round_tables(self):
        root = Path(__file__).resolve().parents[1] / 'frontend/public/data/pocky-football'
        data = json.loads((root/'draft-analysis.json').read_text())
        latest = json.loads((root/'2026/league.json').read_text())
        teams = {t['teamId']: t for t in latest['standings']}
        summary = data['summary']
        groups = [summary['teams'], *summary['positions'].values(), *summary['tendencies'].values(),
                  summary['rookies']['teams'], *summary['trends'].values()]
        for group in groups:
            for row in group:
                self.assertEqual(row['team']['season'], 2026)
                self.assertEqual(row['team']['name'], teams[row['team']['teamId']]['name'])
                self.assertEqual(row['team']['logo'], teams[row['team']['teamId']]['logo'])
        for group in [summary['teams'], *summary['trends'].values()]:
            self.assertEqual([r['averageRoundRank'] for r in group], sorted(r['averageRoundRank'] for r in group))
