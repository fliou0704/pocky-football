import copy
import json
from pathlib import Path
import unittest
from football_weekly import derive, match_id, weekly_contracts, capture_entering_ranks


def game(week, a=1, b=2, x=100, y=90, status='final'):
    return dict(week=week, homeTeamId=a, awayTeamId=b, homeScore=x, awayScore=y,
                status=status, phase='regular', winnerTeamId=a if x>y else b if y>x else None)


def season(matches, year=2025, regular=14):
    return {year: ({'league': {'regularSeasonWeeks':regular}, 'standings': [dict(teamId=i, owner=f'Manager {i}') for i in range(1,5)]}, {'matchups':matches})}


def identities(years=(2025,)):
    return {(y,i):(f'manager-{i}', f'Manager {i}', f'Manager {i}') for y in years for i in range(1,5)}


class WeeklyTests(unittest.TestCase):
    def test_allplay_ties_incomplete_playoffs_history(self):
        matches=[game(1,x=100,y=100), game(1,3,4,110,80), game(2), game(2,3,4,status='live'), game(3), game(3,3,4)]
        r=derive(season(matches,regular=2),identities())[2025]
        self.assertEqual(r['allPlay']['1'],dict(wins=1,losses=1,ties=1))
        self.assertEqual(r['excludedAllPlayWeeks'],[2])
        self.assertNotIn('2',r['weeks'])
        self.assertIn('3',r['weeks'])
        broken=copy.deepcopy(matches); broken[1]['homeTeamId']=1
        self.assertNotIn('1',derive(season(broken),identities())[2025]['weeks'])

    def test_streak_first_win_tie_loss_and_bye(self):
        matches=[]
        for w in range(1,7):
            matches += [game(w,x=100,y=100 if w==4 else 110 if w==5 else 90), game(w,3,4)]
        r=derive(season(matches),identities())[2025]['weeks']
        self.assertEqual({s['teamId'] for s in r['1']['stories'] if s['kind']=='firstWin'}, {1,3})
        self.assertIn(dict(teamId=1,kind='streak',count=3), r['3']['stories'])
        self.assertFalse(any(s['kind']=='streak' and s['teamId']==1 for s in r['4']['stories']))
        self.assertIn(dict(teamId=2,kind='firstWin'),r['5']['stories'])
        self.assertFalse(any(s['kind']=='firstWin' and s['teamId']==1 for s in r['6']['stories']))
        self.assertIn(dict(teamId=3,kind='streak',count=6),r['6']['stories'])

    def test_top_two_shared_award_and_ambiguous_ties(self):
        matches=[game(1,x=120,y=119),game(1,3,4,80,60)]
        r=derive(season(matches),identities())[2025]['weeks']['1']
        self.assertEqual(len(r['awards']),1)
        self.assertEqual(r['awards'][0]['labels'],['Closest Matchup','Top Two Scorers'])
        matches[0]['awayScore']=120
        self.assertEqual(derive(season(matches),identities())[2025]['weeks']['1']['awards'][0]['labels'],['Closest Matchup'])
        matches=[game(1,x=120,y=100),game(1,3,4,80,79)]
        self.assertEqual(len(derive(season(matches),identities())[2025]['weeks']['1']['awards']),2)

    def test_previews_prior_history_verified_managers_and_no_lookahead(self):
        old=[game(1),game(1,3,4),game(2,x=90,y=100),game(2,3,4)]
        new=[]
        for w in range(1,4):
            new += [game(w,1,3), game(w,2,4)]
        new += [game(4,status='live'), game(4,3,4,status='upcoming'),game(5,x=120,y=90),game(5,3,4)]
        source={**season(old,2024), **season(new)}
        source[2025][1]['enteringWeekRanks']={'4':{'1':1,'2':2}}
        r=derive(source,identities((2024,2025)))[2025]
        labels=r['previews']['4'][match_id(2025,new[6])]
        self.assertEqual(set(labels),{'Hot Streak Showdown','Rivalry Tied 1–1','Top Two Showdown'})
        self.assertEqual(r['previews']['5'],{})
        self.assertEqual(r['previews']['1'],{})
        source[2024][0]['standings'][0]['owner']='Someone else'
        r=derive(source,identities((2024,2025)))[2025]
        self.assertFalse(any('Rivalry' in label for label in r['previews']['4'][match_id(2025,new[6])]))

    def test_committed_contracts_and_current_rank_capture(self):
        expected=weekly_contracts()
        for year, data in expected.items():
            root=Path(f'frontend/public/data/pocky-football/{year}')
            self.assertEqual(data,json.loads((root/'weekly.json').read_text()))
            for recap in data['weeks'].values():
                self.assertEqual(len({a['id'] for a in recap['awards']}),len(recap['awards']))
            if year==2026:
                league=json.loads((root/'league.json').read_text());teams=json.loads((root/'teams.json').read_text())
                capture_entering_ranks(league,teams)
                self.assertIn('8',teams['enteringWeekRanks'])
                league['standings'][0]['wins']+=1
                teams.pop('enteringWeekRanks')
                capture_entering_ranks(league,teams)
                self.assertNotIn('enteringWeekRanks',teams)

    def test_byes_gaps_unknown_scoring_and_rivalry_ties(self):
        matches=[game(1),game(1,3,4),game(3),game(3,3,4),game(4),game(4,3,4)]
        r=derive(season(matches),identities())[2025]
        self.assertFalse(any(s['kind']=='streak' for s in r['weeks']['4']['stories']))
        matches[0]['homeScore']=None
        r=derive(season(matches),identities())[2025]
        self.assertNotIn('1',r['weeks'])
        self.assertIn(1,r['excludedAllPlayWeeks'])
        old=[game(1,x=100,y=100),game(1,3,4)]
        new=[game(1,status='upcoming'),game(1,3,4,status='upcoming')]
        r=derive({**season(old,2024),**season(new)},identities((2024,2025)))[2025]
        self.assertEqual(r['previews']['1'][match_id(2025,new[0])],['Rivalry Tied 0–0–1'])
        matches=[]
        for w in range(1,5):
            matches += [game(w),game(w,3,4)]
        matches[4]=dict(game(3),awayTeamId=None,awayScore=None,status='bye')
        r=derive(season(matches),identities())[2025]
        self.assertFalse(any(s['kind']=='streak' and s['teamId']==1 for s in r['weeks']['4']['stories']))
