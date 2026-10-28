import unittest
from football_draft_analysis import (midranks, rookie_status, identity_lookup, identify, season_points, analyze_season, aggregate, tendencies)


class DraftAnalysisTests(unittest.TestCase):
    def test_ties_use_average_ranks_and_keep_zero(self):
        self.assertEqual(midranks([{'playerId':1,'points':0}, {'playerId':2,'points':10}, {'playerId':3,'points':10}], 'points'), {2:1.5,3:1.5,1:3})

    def test_missing_is_not_zero(self):
        p={'playerId':1,'pointsByWeek':{'1':0},'nflTeamsByWeek':{'1':'BUF'}}
        self.assertIsNone(season_points(p,[1,2],{}))
        self.assertEqual(season_points(p,[1],{}),0)
        games={'players':{'1':{'2':{'played':False}}}}
        self.assertEqual(season_points(p,[1,2],games),0)
        self.assertIsNone(season_points(p,[1,2],{'players':{'1':{'2':{'played':True}}}}))

    def test_rookies_require_metadata(self):
        self.assertTrue(rookie_status({'rookieSeason':2025},2025))
        self.assertFalse(rookie_status({'rookieSeason':2021},2025))
        self.assertIsNone(rookie_status({'nflDraft':None},2025))
        self.assertIsNone(rookie_status({'rookieSeason':2026},2025))
        self.assertIsNone(rookie_status({'entityType':'team_defense'},2025))

    def test_identity_does_not_follow_reused_team_id(self):
        identities=identity_lookup({'managers':{'alice':{'name':'Alice','memberships':[{'season':2025,'teamId':1,'expectedOwner':'Alice'}]}}})
        self.assertEqual(identify(2025,{'teamId':1,'name':'A','owner':'Alice'},identities)[0],'alice')
        self.assertNotEqual(identify(2026,{'teamId':1,'name':'B','owner':'Bob'},identities)[0],'alice')
        self.assertNotEqual(identify(2025,{'teamId':1,'name':'B','owner':'Bob'},identities)[0],'alice')
        with self.assertRaises(ValueError):
            identity_lookup({'managers':{'a':{'name':'A','memberships':[{'season':2025,'teamId':1,'expectedOwner':'A'}]*2}}})

    def fixture(self,complete=True):
        league={'league':{'complete':complete},'standings':[{'teamId':1,'name':'A','owner':'Alice'},{'teamId':2,'name':'B','owner':'Bob'}]}
        teams={'matchups':[{'week':1,'status':'final'}]}
        draft={'coverage':{'complete':True},'picks':[{'playerId':i,'playerName':str(i),'overallPick':i,'teamId':1 if i%2 else 2,'round':(i-1)//2+1,'pickInRound':(i-1)%2+1,'position':'QB' if i<=2 else 'RB'} for i in range(1,5)]}
        scoring={'weeks':[1],'players':[{'playerId':i,'position':'QB' if i<=2 else 'RB','pointsByWeek':{'1':v}} for i,v in [(1,200),(2,300),(3,10),(4,20),(5,400)]]}
        return [2025,league,teams,draft,scoring,{}, {},{}]

    def test_position_aware_value_and_undrafted_rank(self):
        data=analyze_season(*self.fixture());a,b,c,d=data['picks']
        self.assertEqual([p['value'] for p in data['picks']],[-100,100,-100,100])
        self.assertEqual(a['overallRank'],3)  # undrafted player is included in overall pool
        self.assertEqual(a['positionalRank'],2)
        self.assertEqual(c['value'],a['value'])  # QB points cannot dominate RB value
        self.assertEqual(sum(p['value'] for p in data['picks']),0)
        self.assertEqual([p['roundScore'] for p in data['picks']],[0,100,0,100])

    def test_incomplete_season_withholds_ranks_and_value(self):
        data=analyze_season(*self.fixture(False))
        self.assertFalse(data['performanceEligible'])
        self.assertEqual(data['picks'][0]['points'],200)
        for p in data['picks']:
            self.assertIsNone(p['value']);self.assertIsNone(p['positionalRank']);self.assertIsNone(p['roundRank'])

    def test_missing_pick_excludes_round_but_not_other_rounds(self):
        args=self.fixture();args[4]['players']=args[4]['players'][1:]
        data=analyze_season(*args)
        self.assertIsNone(data['picks'][0]['points']);self.assertIsNone(data['picks'][1]['roundRank'])
        self.assertEqual(data['picks'][2]['roundRank'],2)
        self.assertIsNone(data['picks'][1]['value']) # singleton cohort has no comparison

    def test_tied_round_winners_and_no_volume_reward(self):
        args=self.fixture();args[4]['players'][0]['pointsByWeek']['1']=300
        data=analyze_season(*args)
        self.assertTrue(all(p['roundWinner'] for p in data['picks'][:2]))
        self.assertEqual(data['picks'][0]['roundRank'],1.5)
        picks=data['picks'];a=aggregate(picks);b=aggregate(picks+picks)
        self.assertEqual([p['averageValue'] for p in a],[p['averageValue'] for p in b])

    def test_unused_nfl_week_is_excluded(self):
        args=self.fixture();args[4]['players'][0]['pointsByWeek']['18']=999
        self.assertEqual(analyze_season(*args)['picks'][0]['points'],200)

    def test_round_normalization_is_comparable_across_league_sizes(self):
        small=analyze_season(*self.fixture())
        args=self.fixture()
        for i in range(3,5):
            args[1]['standings'].append({'teamId':i,'name':str(i),'owner':str(i)})
        for p in args[3]['picks']:
            p.update(round=1,pickInRound=p['overallPick'],teamId=p['overallPick'])
        large=analyze_season(*args)
        self.assertEqual(max(p['roundScore'] for p in small['picks']),100)
        self.assertEqual(max(p['roundScore'] for p in large['picks']),100)
        self.assertEqual(min(p['roundScore'] for p in large['picks']),0)

    def test_conflicts_withhold_performance(self):
        args=self.fixture();args[4]['coverage']={'conflicts':[{'playerId':1}]}
        self.assertFalse(analyze_season(*args)['performanceEligible'])

    def test_first_position_selection_gets_one_vote_per_season(self):
        picks=analyze_season(*self.fixture())['picks'];picks[1]['managerId']=picks[0]['managerId']
        rows=tendencies(picks)['QB'];self.assertEqual(rows[0]['picks'],2);self.assertEqual(len(rows[0]['evidence']),1)

if __name__ == '__main__':
    unittest.main()
