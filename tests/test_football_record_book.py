import copy
import unittest
from football_record_book import season_candidates, view, record, streak_rows


def fixture(complete=True):
    teams=[{'teamId':1,'name':'Old A','logo':None},{'teamId':2,'name':'Old B','logo':None}]
    matches=[]; weeks={str(t['teamId']):{'weeks':[]} for t in teams}; lineups={}
    for week,a,b in ((1,10,5),(2,20,20),(3,4,9),(4,100,1)):
        playoff=week==4; winner=1 if a>b else 2 if b>a else None
        matches.append({'week':week,'status':'final','homeTeamId':1,'awayTeamId':2,
                        'homeScore':a,'awayScore':b,'winnerTeamId':winner,'isBye':False,
                        'phase':'playoffs' if playoff else 'regular','bracket':'championship' if playoff else 'regular',
                        'roundLabel':'Championship' if playoff else None})
        for t,opp,score,opp_score in ((1,2,a,b),(2,1,b,a)):
            weeks[str(t)]['weeks'].append({'week':week,'status':'final','opponentTeamId':opp,
                                          'score':score,'opponentScore':opp_score,'phase':'playoffs' if playoff else 'regular',
                                          'result':'T' if winner is None else 'W' if t==winner else 'L','isBye':False})
        lineups[week]={'teams':{'1':[
            {'playerId':10,'name':'Starter','nflTeam':'BUF','position':'QB','slot':'QB','points':a},
            {'playerId':11,'name':'Bench','nflTeam':'SEA','position':'WR','slot':'BE','points':40 if week==1 else 0},
            {'playerId':12,'name':'IR','nflTeam':'CHI','position':'RB','slot':'IR','points':50 if week==1 else None},
            {'playerId':13,'name':'Missing','nflTeam':'GB','position':'TE','slot':'TE','points':None}], '2':[]}}
    league={'league':{'regularSeasonWeeks':3,'complete':complete},'standings':teams}
    return league,{'teams':weeks,'matchups':matches},lineups


class RecordBookTests(unittest.TestCase):
    def setUp(self):
        self.league,self.data,self.lineups=fixture()
        self.c=season_candidates(2025,self.league,self.data,self.lineups)
        self.v=view({2025:self.c})
        self.records={r['id']:r for r in self.v['teamRecords']+self.v['playerRecords']}

    def test_team_high_low_margin_and_closest_include_ties(self):
        self.assertEqual(self.records['team-high']['value'],100)
        self.assertEqual(self.records['team-low']['value'],1)
        self.assertEqual(self.records['margin-high']['value'],99)
        self.assertEqual(self.records['margin-low']['value'],0)
        self.assertTrue(self.records['margin-low']['holders'][0]['isTie'])
        self.assertEqual(self.records['team-high']['holders'][0]['team']['name'],'Old A')

    def test_regular_season_totals_and_percentage_exclude_playoffs(self):
        self.assertEqual(self.records['season-high']['value'],34)
        self.assertEqual(self.records['season-low']['value'],34)
        self.assertEqual(self.records['record-best']['value'],.5)
        self.assertEqual(self.records['record-worst']['value'],.5)
        self.assertEqual(len(self.records['record-best']['holders']),2)
        self.assertEqual(self.records['record-best']['holders'][0]['games'],3)

    def test_current_season_not_compared_as_a_complete_season(self):
        self.data['matchups'][2]['status']='upcoming'
        c=season_candidates(2026,{**self.league,'league':{**self.league['league'],'complete':False}},self.data,self.lineups)
        self.assertFalse(c['regularSeasonComplete'])
        self.assertFalse(c['totals'])
        self.assertTrue(c['weekly'])
        self.assertIsNone(c['champion'])

    def test_completed_regular_season_can_finish_before_playoffs(self):
        league=copy.deepcopy(self.league);league['league']['complete']=False
        c=season_candidates(2026,league,self.data,self.lineups)
        self.assertTrue(c['regularSeasonComplete'])
        self.assertTrue(c['totals'])
        self.assertIsNone(c['champion'])

    def test_byes_self_games_and_nonfinal_high_scores_excluded(self):
        for extra in ({'awayTeamId':None,'isBye':True},{'awayTeamId':1},{'status':'live'}):
            m={**self.data['matchups'][0], 'week':5,'homeScore':9999,**extra}
            self.data['matchups'].append(m)
        c=season_candidates(2025,self.league,self.data,self.lineups)
        self.assertEqual(max(r['value'] for r in c['weekly']),100)
        self.assertEqual(len(c['margins']),4)

    def test_player_starter_bench_ir_and_missing_points(self):
        self.assertEqual(self.records['player-high']['value'],100)
        self.assertEqual(self.records['starter-high']['value'],100)
        self.assertEqual(self.records['bench-high']['value'],40)
        self.assertEqual(self.records['bench-high']['holders'][0]['slot'],'BE')
        self.assertFalse(any(p['name']=='Missing' for p in self.c['players']))
        self.assertGreater(self.c['missingPlayerPoints'],0)
        self.assertEqual(self.v['mvp']['value'],34)

    def test_exact_ties_deterministic_order(self):
        rows=[{'season':2025,'week':2,'team':{'teamId':2},'value':10},
              {'season':2021,'week':1,'team':{'teamId':1},'value':10}]
        r=record('x','X',rows)
        self.assertEqual(len(r['holders']),2)
        self.assertEqual(r['holders'][0]['season'],2021)

    def test_season_and_all_time_scope(self):
        other=copy.deepcopy(self.c);other['weekly'][0]['value']=200
        all_time=view({2021:other,2025:self.c})
        single=view({2025:self.c})
        self.assertEqual(all_time['teamRecords'][0]['value'],200)
        self.assertEqual(single['teamRecords'][0]['value'],100)
        self.assertEqual(len(all_time['coverage']),2)

    def test_streak_ties_interrupt_byes_do_not_extend_playoffs_excluded(self):
        def w(n,result,phase='regular',bye=False):
            return {'week':n,'result':result,'phase':phase,'status':'final','isBye':bye,'opponentTeamId':None if bye else 2}
        rows=streak_rows(2025,self.league['standings'][0],[w(1,'W'),w(2,'W'),w(3,'BYE',bye=True),w(4,'T'),w(5,'L'),w(6,'L'),w(7,'L','playoffs')])
        self.assertEqual([(r['result'],r['value'],r['endWeek']) for r in rows],[('W',2,2),('L',2,6)])

    def test_missing_weekly_lineup_only_reduces_player_coverage(self):
        del self.lineups[4]
        c=season_candidates(2025,self.league,self.data,self.lineups)
        self.assertEqual(c['missingLineupWeeks'],[1,2,3,4]) # Team B lacks lineups in this fixture.
        self.assertEqual(max(p['value'] for p in c['weekly']),100)

    def test_negative_week_table_uses_starters_only(self):
        self.lineups[1]['teams']['1'][0]['points']=-2
        self.lineups[1]['teams']['1'][1]['points']=-10
        c=season_candidates(2025,self.league,self.data,self.lineups)
        negatives=view({2025:c})['negativeStarterWeeks']
        self.assertEqual(len(negatives),1)
        self.assertEqual(negatives[0]['slot'],'QB')

    def test_champion_and_fantasy_roster_use_source_season(self):
        self.assertEqual(self.c['champion']['teamId'],1)
        self.assertEqual(self.c['allFantasyTeam'][0]['awardSlot'],'QB')
        self.assertEqual(self.c['allFantasyTeam'][0]['value'],34)


if __name__=='__main__':unittest.main()
