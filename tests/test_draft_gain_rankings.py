"""Offline contracts for gain rankings and NFL-based provisional qualification."""
import copy
import json
import unittest
from pathlib import Path
from football_draft_analysis import analyze_season, competition_ranks, positional_benchmark, completed_nfl_weeks, build_summary, build_draft_analysis

ROOT = Path(__file__).resolve().parents[1]


def fixture(weeks=8):
    league = {'league': {'complete': False}, 'standings': [{'teamId': 1, 'name': 'A', 'owner': 'A'}]}
    draft = {'coverage': {'complete': True}, 'picks': [
        {'playerId': pid, 'position': 'RB', 'overallPick': pick, 'teamId': 1, 'round': 1, 'pickInRound': pick}
        for pid, pick in [(1, 1), (2, 2), (3, 3)]]}
    schedule = [{'id': f'{w}-{i}', 'week': w, 'home': f'T{i*2}', 'away': f'T{i*2+1}',
                 'kickoff': 1, 'complete': w <= weeks, 'completionUnknown': False} for w in range(1, 18) for i in range(16)]
    # 1 is normal; 2 is a high-impact 3-game exception; 3 fails both paths.
    productions = {1:[10]*weeks, 2:[30]*3, 3:[1], 4:[20]*weeks, 5:[15]*weeks}
    scoring = {'weeks': list(range(1,weeks+1)), 'players': []}
    games = {'weeks': list(range(1,weeks+1)), 'games': schedule,
             'coverage': {'playersWithActualSeasonRecords': list(map(str,productions))}, 'players': {}}
    for pid, points in productions.items():
        scoring['players'].append({'playerId': pid, 'position': 'RB', 'pointsByWeek': {str(w):p for w,p in enumerate(points,1)}})
        games['players'][str(pid)] = {str(w):{'played': True, 'stats': {}, 'points':p, 'nflTeam':'T0', 'eventId':f'{w}-0'} for w,p in enumerate(points,1)}
    return [2030, league, {'matchups':[{'week':w,'status':'final'} for w in range(1,weeks+1)]}, draft, scoring, games, {}, {}]


class GainRankings(unittest.TestCase):
    def test_competition_ties_are_order_independent_and_skip(self):
        for values, expected in [([100,90,90,70],[1,2,2,4]), ([100,90,90,90,70],[1,2,2,2,5])]:
            rows=[{'playerId':i,'score':v} for i,v in enumerate(values)]
            self.assertEqual(list(competition_ranks(rows,'score').values()), expected)
            self.assertEqual(competition_ranks(rows,'score'),competition_ranks(rows[::-1],'score'))

    def test_outside_rank_uses_entire_draft_end_not_position_end(self):
        self.assertEqual(positional_benchmark(10,3,[10,20],150),(-141,'below_drafted_range'))
        for actual, rank, expected in [(10,2,-10),(20,2,0),(30,1,20)]:
            self.assertEqual(positional_benchmark(actual,rank,[10,20],150),(expected,'available'))
        for rank in (None,0,float('nan')):
            self.assertIsNone(positional_benchmark(10,rank,[10],150)[0])

    def test_ongoing_fppg_normal_exception_and_failure_include_undrafted(self):
        s=analyze_season(*fixture()); p={p['playerId']:p for p in s['picks']}
        self.assertEqual(s['minimumGames'],4)
        self.assertEqual((p[1]['qualification'],p[1]['fppg'],p[1]['positionalRank']),('normal',10,4))
        # Cumulative RB3 (90 points) is within the 3 drafted RBs, then FPPG ranks RB1.
        self.assertEqual((p[2]['qualification'],p[2]['gamesPlayed'],p[2]['positionalRank']),('total_points',3,1))
        self.assertEqual(p[3]['qualification'],'insufficient_games')
        self.assertIsNone(p[3]['positionalRank'])
        self.assertEqual(p[1]['benchmarkPick'],4)
        self.assertEqual(p[1]['benchmarkStatus'],'below_drafted_range')
        self.assertEqual([p[i]['roundRank'] for i in (1,2,3)],[2,1,None])
        self.assertFalse(s['performanceEligible'])
        self.assertEqual(build_summary({'2030':s},{p[1]['managerId']},2030)['teams'],[])

    def test_partial_week_rescheduled_unknown_and_partial_schedule_do_not_count(self):
        args=fixture(); games=args[5]
        games['games'][8*16-1]['complete']=False
        self.assertEqual(completed_nfl_weeks(games),list(range(1,8)))
        games['games'][8*16-1].update(complete=True,completionUnknown=True)
        self.assertEqual(completed_nfl_weeks(games),list(range(1,8)))
        games['games'][8*16-1].update(complete=False,completionUnknown=False,canceled=True)
        self.assertEqual(len(completed_nfl_weeks(games)),8)
        games['games']=games['games'][:1]
        self.assertEqual(completed_nfl_weeks(games),[])

    def test_threshold_examples_and_zero_game_participation(self):
        for weeks, threshold in [(1,1),(5,3),(7,4),(8,4),(9,5)]:
            args=fixture(weeks); s=analyze_season(*args)
            self.assertEqual(s['minimumGames'],threshold)
        args=fixture(1); args[4]['players'][0]['pointsByWeek']['1']=0
        args[5]['players']['1']['1']['points']=0
        pick=analyze_season(*args)['picks'][0]
        self.assertEqual((pick['gamesPlayed'],pick['fppg'],pick['qualification']),(1,0,'normal'))

    def test_bye_and_dnp_do_not_count_and_missing_participation_is_not_invented(self):
        args=fixture(); next(g for g in args[5]['games'] if g['week']==8 and g['home']=='T0').update(week=18,complete=False)
        args[5]['players']['1'].pop('8');args[4]['players'][0]['pointsByWeek'].pop('8')
        s=analyze_season(*args)
        self.assertEqual(s['picks'][0]['gamesPlayed'],7)
        args=fixture(); args[5]['players']['2']['1']['played']=None
        pick=analyze_season(*args)['picks'][1]
        self.assertIsNone(pick['fppg']);self.assertIsNone(pick['positionalRank'])
        self.assertEqual(pick['qualification'],'missing_participation')

    def test_missing_or_conflicting_scores_do_not_earn_exception(self):
        for conflict in (False,True):
            args=fixture();args[4]['players'][1]['pointsByWeek']['1']=None if not conflict else 999
            if not conflict: args[5]['players']['2']['1'].pop('points')
            pick=analyze_season(*args)['picks'][1]
            self.assertIsNone(pick['points']);self.assertIsNone(pick['positionalRank'])
        args=fixture();args[5]['coverage']={};args[5]['players'].pop('2')
        self.assertIsNone(analyze_season(*args)['picks'][1]['positionalRank'])

    def test_total_points_tie_at_cutoff_qualifies_and_uncovered_week_is_unknown(self):
        args=fixture(); args[4]['players'][0]['pointsByWeek']['1']=20
        args[5]['players']['1']['1']['points']=20
        pick=analyze_season(*args)['picks'][1]
        self.assertEqual((pick['cumulativePositionalRank'],pick['qualification']),(3,'total_points'))
        args=fixture();args[5]['weeks']=list(range(1,7))
        self.assertIsNone(analyze_season(*args)['picks'][1]['gamesPlayed'])

    def test_transition_to_final_uses_total_points_and_includes_short_availability(self):
        args=fixture(); provisional=analyze_season(*args)
        args[1]['league']['complete']=True;final=analyze_season(*args)
        self.assertTrue(final['performanceEligible'])
        self.assertEqual(final['rankingBasis'],'points')
        self.assertEqual(final['picks'][1]['positionalRank'],3)
        self.assertEqual(provisional['picks'][1]['positionalRank'],1)
        self.assertIsNotNone(final['picks'][2]['positionalRank'])

    def test_round_winners_gain_not_points_and_ties(self):
        args=fixture();s=analyze_season(*args)
        self.assertEqual(s['rounds'][0]['leaders'][0]['playerId'],2)
        # Different positions at their exact benchmarks each earn zero: tie despite points.
        args[1]['league']['complete']=True
        args[3]['picks']=args[3]['picks'][:2]
        args[3]['picks'][1]['position']='QB';args[4]['players'][1]['position']='QB'
        args[4]['players']=[p for p in args[4]['players'] if p['playerId'] in (1,2)]
        picks=analyze_season(*args)['picks']
        self.assertEqual([p['roundRank'] for p in picks],[1,1])
        self.assertTrue(all(p['roundWinner'] for p in picks))

    def test_actual_committed_all_seasons_integer_ranks_and_benchmark_arithmetic(self):
        data=json.loads((ROOT/'frontend/public/data/pocky-football/draft-analysis.json').read_text())
        self.assertIn(2026,data['years'])
        for year,s in data['seasons'].items():
            evaluated=[p for p in s['picks'] if p['draftPositionGain'] is not None]
            self.assertTrue(evaluated,year)
            last=max(p['overallPick'] for p in s['picks'])
            for p in evaluated:
                self.assertEqual(p['draftPositionGain'],p['overallPick']-p['benchmarkPick'])
                for field in ('positionalRank','roundRank','benchmarkPick'):
                    self.assertIs(type(p[field]),int)
                if p['benchmarkStatus']=='below_drafted_range':self.assertEqual(p['benchmarkPick'],last+1)

    def test_future_season_is_discovered_from_valid_draft_without_year_constant(self):
        # The builder discovers year folders with nonempty drafts; test against a copy
        # without generating or fetching any source data.
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'pocky-football';root.mkdir()
            source=ROOT/'frontend/public/data/pocky-football'
            shutil.copytree(source/'2026',root/'2030')
            shutil.copy(source/'players.json',root/'players.json')
            (root/'2031').mkdir()
            data=build_draft_analysis(folder)
            self.assertEqual(data['years'],[2030])
            self.assertTrue(data['seasons']['2030']['analysisAvailable'])
