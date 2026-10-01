import unittest
import json
from pathlib import Path
from football_h2h import pair_view


def season(year, ids=(1,2), tie=False):
    teams=[{'teamId':i,'name':f'{year} Team {i}','logo':None} for i in ids]
    matches=[{'week':1,'homeTeamId':1,'awayTeamId':2,'homeScore':100,'awayScore':100 if tie else 90,'winnerTeamId':None if tie else 1,'status':'final','isBye':False,'isPlayoff':False,'roundLabel':None},
             {'week':2,'homeTeamId':1,'awayTeamId':2,'homeScore':10,'awayScore':20,'winnerTeamId':None,'status':'live','isBye':False,'isPlayoff':False,'roundLabel':None},
             {'week':3,'homeTeamId':1,'awayTeamId':None,'homeScore':None,'awayScore':None,'winnerTeamId':None,'status':'bye','isBye':True,'isPlayoff':True,'roundLabel':'Bye'},
             {'week':4,'homeTeamId':2,'awayTeamId':1,'homeScore':110,'awayScore':80,'winnerTeamId':2,'status':'final','isBye':False,'isPlayoff':True,'roundLabel':'Championship'}]
    data={'matchups':matches,'teams':{str(i):{'weeks':[{'week':1,'score':100 if i==1 or tie else 90,'phase':'regular','status':'final','isBye':False}, {'week':2,'score':20,'phase':'regular','status':'live','isBye':False}, {'week':4,'score':80 if i==1 else 110,'phase':'playoffs','status':'final','isBye':False}]} for i in ids}}
    return ({'standings':teams},data)


class H2HTests(unittest.TestCase):
    def test_generated_pairs_have_consistent_records_and_unique_weeks(self):
        root = Path(__file__).resolve().parents[1] / 'frontend/public/data/pocky-football/h2h'
        files = list(root.glob('*.json'))
        self.assertEqual(len(files), 45)
        for path in files:
            data = json.loads(path.read_text())
            for mode in ('historical', 'theoretical'):
                for view in data[mode].values():
                    record = view['summary']
                    self.assertEqual(record['total'], record['wins'] + record['losses'] + record['ties'])
                    self.assertEqual(record['total'], len(view['rows']))
                    keys = [(row['season'], row['week']) for row in view['rows']]
                    self.assertEqual(len(keys), len(set(keys)))
                    if mode == 'theoretical':
                        self.assertTrue(all(not row['isPlayoff'] for row in view['rows']))

    def test_actual_ties_playoffs_byes_and_historical_names(self):
        view=pair_view({2025:season(2025,tie=True)},1,2)
        self.assertEqual(view['historical']['summary'],{'wins':0,'losses':1,'ties':1,'total':2})
        self.assertEqual(view['historical']['rows'][0]['roundLabel'],'Championship')
        self.assertEqual(view['historical']['rows'][1]['teamA']['name'],'2025 Team 1')
        self.assertEqual(view['theoretical']['summary'],{'wins':0,'losses':0,'ties':1,'total':1})
        self.assertTrue(view['theoretical']['rows'][0]['actualMeeting'])

    def test_same_season_week_missing_team_and_different_sizes(self):
        data={2021:season(2021,ids=(1,3,4)),2025:season(2025),2026:season(2026,ids=(1,2,3,4))}
        view=pair_view(data,1,2)
        self.assertEqual(view['theoretical']['summary']['total'],2)
        self.assertEqual(view['theoretical']['seasons'],[2026,2025])
        reverse=pair_view(data,2,1)
        self.assertEqual(reverse['theoretical']['summary']['losses'],2)
        self.assertTrue(all(row['season']!=2021 for row in view['historical']['rows']))

    def test_nonmeeting_theoretical_zero_and_incomplete_exclusion(self):
        league,data=season(2025)
        data['matchups']=[]
        data['teams']['1']['weeks'][0]['score']=0
        result=pair_view({2025:(league,data)},1,2)
        self.assertEqual(result['historical']['summary']['total'],0)
        self.assertEqual(result['theoretical']['summary']['total'],1)
        self.assertEqual(result['theoretical']['summary']['losses'],1)
        self.assertFalse(result['theoretical']['rows'][0]['actualMeeting'])
