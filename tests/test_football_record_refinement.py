import copy
import json
import unittest
from pathlib import Path
from football_record_book import build_record_book,season_candidates,view
from football_record_rankings import ranked,player_seasons,pickup_rows
from football_player_scoring import normalize_player_scoring
from test_football_record_book import fixture


class RefinementTests(unittest.TestCase):
    def test_rank_cutoff_retains_ties_and_competition_ranks(self):
        rows=[{'season':2025,'team':{'teamId':i},'value':20-i} for i in range(12)]
        rows[10]['value']=rows[9]['value']
        leaders=ranked(rows,10)
        self.assertEqual(len(leaders),11);self.assertEqual([r['rank'] for r in leaders][-2:],[10,10])
        self.assertEqual(len(ranked(rows,5)),5)
        tied=ranked([{'season':2021,'value':.5,'wins':7,'losses':7},{'season':2022,'value':.5,'wins':6,'losses':6}],5)
        self.assertEqual([r['rank'] for r in tied],[1,1])

    def test_lowest_score_excludes_consolation_without_deleting_data(self):
        league,data,lineups=fixture();data['matchups'][-1]['bracket']='placement'
        c=season_candidates(2025,league,data,lineups);v=view({2025:c})
        low=next(r for r in v['teamRecords'] if r['id']=='team-low')
        self.assertEqual(low['value'],4);self.assertEqual(len(c['weekly']),8)
        high=next(r for r in v['teamRecords'] if r['id']=='team-high')
        self.assertEqual(high['value'],100)
        self.assertEqual(high['leaders'][0]['matchup']['week'],4)

    def test_completed_season_views_omit_aggregate_and_negative_records(self):
        league,data,lineups=fixture();c=season_candidates(2025,league,data,lineups)
        v=view({2025:c},individual=True)
        ids={r['id'] for r in v['teamRecords']+v['playerRecords']}
        self.assertFalse(ids&{'season-high','season-low','record-best','record-worst','starter-high'})
        self.assertEqual(v['negativeStarterWeeks'],[])
        self.assertTrue(all(r['limit']==5 for r in v['playerRecords']))
        self.assertEqual({r['label'] for r in v['positionRecords']},{f'Highest {p} Score in One Week' for p in ('QB','RB','WR','TE','D/ST','K')})

    def test_dst_negative_exclusion_and_real_position(self):
        league,data,lineups=fixture();lineups[1]['teams']['1'][0].update(position='D/ST',points=-3)
        lineups[1]['teams']['1'][1].update(position='RB',slot='FLEX',points=99)
        v=view({2025:season_candidates(2025,league,data,lineups)})
        self.assertEqual(v['negativeStarterWeeks'],[])
        rb=next(r for r in v['positionRecords'] if r['id']=='position-RB')
        self.assertEqual(rb['value'],99)

    def scoring(self):
        return {'weeks':[1,2,3,4],'coverage':{'conflicts':[]},'players':[{'playerId':10,'name':'Player','position':'RB','nflTeam':'BUF',
          'pointsByWeek':{'1':10,'2':20,'3':30,'4':40},'nflTeamsByWeek':{str(w):'BUF' for w in range(1,5)}}],
          'games':[{'week':w,'kickoff':w*1000,'home':'BUF','away':'NYJ'} for w in range(1,5)]}

    def test_player_season_all_configured_weeks_no_ownership_double_count(self):
        scoring=self.scoring();scoring['players'][0]['pointsByWeek']['18']=999
        rows=player_seasons(2025,scoring,True)
        self.assertEqual(rows[0]['value'],100)
        self.assertFalse(player_seasons(2026,scoring,False))
        del scoring['players'][0]['pointsByWeek']['2'];self.assertFalse(player_seasons(2025,scoring,True))
        scoring['games']=[g for g in scoring['games'] if g['week']!=2]
        self.assertEqual(player_seasons(2025,scoring,True)[0]['value'],80)

    def test_score_normalization_deduplicates_actual_week_and_ignores_projections_trailing(self):
        stats=[{'seasonId':2025,'statSourceId':0,'statSplitTypeId':1,'scoringPeriodId':1,'appliedTotal':10,'proTeamId':2}]*2
        stats+=[{**stats[0],'statSourceId':1,'appliedTotal':999},{**stats[0],'scoringPeriodId':18,'appliedTotal':999}]
        x=normalize_player_scoring({'players':[{'id':10,'player':{'fullName':'A','proTeamId':2,'defaultPositionId':2,'stats':stats}}]},2025,{1,2})
        self.assertEqual(x['players'][0]['pointsByWeek'],{'1':10})
        self.assertEqual(x['coverage']['conflicts'],[])

    def test_pickup_pre_acquisition_drop_reacquire_and_trade_exclusion(self):
        def e(kind,time,add=False,drop=False,identity='id'):
            from datetime import datetime,timezone
            return {'id':identity,'timestamp':datetime.fromtimestamp(time,timezone.utc).isoformat(),'week':1,'type':kind,'faab':None,
              'teams':[{'teamId':1,'playersAdded':[{'playerId':10}] if add else [],'playersDropped':[{'playerId':10}] if drop else []}]}
        a={'coverage':{'status':'likely_complete'},'events':[e('draft',0,add=True),e('drop',1,drop=True),
               e('waiver_add',1.5,add=True,identity='first'),e('drop',2.5,drop=True),e('free_agent_add',3.5,add=True,identity='second')]}
        rows=pickup_rows(2025,a,self.scoring(),{1:{'teamId':1,'name':'A','logo':None}})
        self.assertEqual([r['value'] for r in rows],[20,40])
        self.assertEqual([r['creditedWeeks'] for r in rows],[[2],[4]])
        self.assertEqual([r['acquisitionType'] for r in rows],['waiver_add','free_agent_add'])
        a['events']=[e('trade',0,add=True)];self.assertFalse(pickup_rows(2025,a,self.scoring(),{1:{'teamId':1}}))

    def test_nfl_opponent_uses_weekly_team_schedule_only(self):
        league,data,lineups=fixture()
        c=season_candidates(2025,league,data,lineups,self.scoring())
        holder=next(p for p in c['players'] if p['playerId']==10 and p['week']==1)
        self.assertEqual(holder['nflOpponent'],'NYJ')
        self.assertEqual(holder['nflTeam'],'BUF')
        source=self.scoring();source['games']=[]
        holder=next(p for p in season_candidates(2025,league,data,lineups,source)['players'] if p['playerId']==10)
        self.assertNotIn('nflOpponent',holder)

    def test_source_score_conflicts_prevent_player_season_and_pickup_awards(self):
        source=self.scoring();source['coverage']['lineupComparison']={'scoreConflicts':[{'playerId':10,'week':1}]}
        self.assertFalse(player_seasons(2025,source,True))
        activity={'coverage':{'status':'likely_complete'},'events':[]}
        self.assertFalse(pickup_rows(2025,activity,source,{1:{'teamId':1}}))

    def test_generated_contract_complete_seasons_ranked_lists_lineup_refs_and_roster(self):
        root=Path(__file__).resolve().parents[1]/'frontend/public/data/pocky-football'
        x=json.loads((root/'record-book.json').read_text())
        self.assertNotIn('2026',x['seasons']);self.assertEqual(x['years'],[2025,2024,2023,2022,2021])
        self.assertTrue(any(r['season']==2026 for c in x['allTime']['coverage'] for r in [c]))
        for season,v in x['seasons'].items():
            roster=v['allFantasyTeam'];self.assertEqual(len(roster),16)
            self.assertEqual(sum(p['awardSlot']=='BE' for p in roster),7)
            self.assertNotIn('IR',[p['awardSlot'] for p in roster]);self.assertEqual(len({p['playerId'] for p in roster}),16)
            self.assertTrue(any(r['id']=='best-pickup' for r in v['playerRecords']))
        for r in x['allTime']['teamRecords']:
            for h in r['leaders']:
                self.assertLessEqual(h['rank'],r['limit'])
                if r['matchupDetails']:
                    m=h['matchup'];lineups=json.loads((root/str(m['season'])/'lineups'/f"{m['week']}.json").read_text())
                    self.assertIn(str(m['teamA']['teamId']),lineups['teams']);self.assertIn(str(m['teamB']['teamId']),lineups['teams'])
        for season in x['years']:
            draft=json.loads((root/str(season)/'draft.json').read_text())
            self.assertTrue(all(p.get('position') in ('QB','RB','WR','TE','D/ST','K') for p in draft['picks']))

if __name__=='__main__':unittest.main()
