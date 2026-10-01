import copy
import json
from pathlib import Path
import tempfile
import unittest
from football_activity import normalize_transaction, reconcile_activity
from football_activity_audit import validate_events, ownership_audit, lineup_window_audit, draft_activity_audit
from football_draft import normalize_draft,draft_issues


def raw(identity='one',kind='FREEAGENT',items=None,time=1750000000000):
    return {'id':identity,'type':kind,'status':'EXECUTED','proposedDate':time,'scoringPeriodId':1,
            'items':items if items is not None else [{'type':'ADD','playerId':10,'fromTeamId':0,'toTeamId':1}]}

def event(**kwargs):return normalize_transaction(raw(**kwargs),2025,{10:'A',11:'B',12:'C'}, {1,2,3})

def board():
    return normalize_draft({'draftDetail':{'drafted':True,'picks':[
        {'overallPickNumber':1,'roundId':1,'roundPickNumber':1,'teamId':1,'playerId':10},
        {'overallPickNumber':2,'roundId':1,'roundPickNumber':2,'teamId':2,'playerId':11},
        {'overallPickNumber':3,'roundId':2,'roundPickNumber':1,'teamId':2,'playerId':12},
        {'overallPickNumber':4,'roundId':2,'roundPickNumber':2,'teamId':1,'playerId':-16001}]},
        'settings':{'draftSettings':{'type':'SNAKE','pickOrder':[1,2]},'rosterSettings':{'lineupSlotCounts':{'0':1,'20':1,'21':1}}}},2025,{}, {1,2})


class AuditTests(unittest.TestCase):
    def test_unique_identity_and_cross_id_semantics(self):
        e=event();duplicate=event(identity='other')
        a=validate_events([e,e,duplicate],{1})
        self.assertEqual(a['duplicateEventIds'],[e['id']]);self.assertEqual(len(a['semanticDuplicateGroups']),1)

    def test_genuine_later_repeat_is_preserved(self):
        self.assertEqual(validate_events([event(),event(identity='later',time=1750000001000)],{1})['semanticDuplicateGroups'],[])

    def test_three_team_trade_edges_balance(self):
        e=event(kind='TRADE_ACCEPT',items=[{'type':'TRADE','playerId':10,'fromTeamId':1,'toTeamId':2},
            {'type':'TRADE','playerId':11,'fromTeamId':2,'toTeamId':3}, {'type':'TRADE','playerId':12,'fromTeamId':3,'toTeamId':1}])
        self.assertEqual(validate_events([e],{1,2,3})['issues'],[])
        e['transfers'].pop();self.assertEqual(validate_events([e],{1,2,3})['issues'][0]['issue'],'unbalanced_trade')

    def test_invalid_trade_endpoint_flagged(self):
        e=event(kind='TRADE_ACCEPT',items=[{'type':'TRADE','playerId':10,'fromTeamId':99,'toTeamId':1}])
        self.assertTrue(validate_events([e],{1})['issues'])

    def test_invalid_players_and_missing_id_rejected(self):
        for pid in (None,True,0,'10'):
            self.assertIsNone(event(items=[{'type':'ADD','playerId':pid,'toTeamId':1}]))
        self.assertIsNone(normalize_transaction({**raw(),'id':None},2025,{}, {1}))
        self.assertIsNotNone(event(items=[{'type':'ADD','playerId':-16001,'toTeamId':1}]))

    def test_counter_agreement_is_scoped_and_retrieval_gated(self):
        t=raw();cards=[{'playerId':10,'name':'A','transactions':[t]}]
        meta={'through':0,'teamCounters':{'1':{'acquisitions':1,'drops':0,'trades':0,'matchupAcquisitionTotals':{'1':1}}}}
        d=reconcile_activity(2025,{}, {1},{0:[t],1:[t]},cards,meta)
        self.assertEqual(d['coverage']['status'],'independently_verified_counts')
        self.assertTrue(d['coverage']['complete']);self.assertEqual(len(d['events']),1)
        self.assertEqual(d['coverage']['repeatedSourceIdAppearancesMerged'],2)
        for periods,failed,universe in (({0:[t]},[],True),({0:[t]},[1],True),({0:[t],1:[t]},[],False)):
            d=reconcile_activity(2025,{}, {1},periods,cards,meta,failed,universe)
            self.assertFalse(d['coverage']['complete'])

    def test_known_player_missing_prevents_completeness(self):
        d=reconcile_activity(2025,{99:'Missing'}, {1},{0:[raw()],1:[]},[{'playerId':10,'name':'A','transactions':[]}],{'through':0})
        self.assertEqual(d['coverage']['missingPlayerCount'],1);self.assertEqual(d['coverage']['status'],'partial')

    def test_source_extra_fields_not_a_movement_conflict(self):
        t=raw();card=copy.deepcopy(t);card['items'][0]['lineupSlotId']=20
        d=reconcile_activity(2025,{}, {1},{0:[t],1:[]},[{'playerId':10,'name':'A','transactions':[card]}],{'through':0})
        self.assertEqual(d['coverage']['executedPayloadConflictCount'],0)
        card['items'][0]['toTeamId']=2
        d=reconcile_activity(2025,{}, {1,2},{0:[t],1:[]},[{'playerId':10,'name':'A','transactions':[card]}],{'through':0})
        self.assertEqual(d['coverage']['executedPayloadConflictCount'],1)

    def test_ownership_drop_readd_and_wrong_origin(self):
        add=event();drop=event(identity='drop',kind='FREEAGENT',time=1750000001000,items=[{'type':'DROP','playerId':10,'fromTeamId':1,'toTeamId':0}])
        again=event(identity='again',time=1750000002000)
        self.assertEqual(ownership_audit([add,drop,again])['anomalies'],[])
        self.assertEqual(ownership_audit([add,drop,again])['reAcquisitionsChecked'],1)
        self.assertTrue(ownership_audit([drop])['anomalies'])

    def test_lineup_period_windows_and_missing_movement(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'lineups';p.mkdir();(p/'1.json').write_text(json.dumps({'teams':{'1':[{'playerId':10}]}}))
            self.assertEqual(lineup_window_audit([event()],folder)['anomalies'],[])
            self.assertEqual(len(lineup_window_audit([],folder)['anomalies']),1)

    def test_full_draft_size_order_negative_defense_id(self):
        d=board();self.assertTrue(d['coverage']['complete']);self.assertEqual(d['coverage']['expectedSelections'],4)
        self.assertEqual(d['picks'][2]['draftSlot'],2);self.assertIsNone(d['picks'][0]['auctionPrice'])

    def test_draft_validation_regressions(self):
        for field,value,issue in [('overallPick',2,'duplicate_overall_pick'),('playerId',11,'duplicate_drafted_player'),
                                  ('round',None,'invalid_round_pick_relationship'),('pickInRound',3,'invalid_round_pick_relationship'),
                                  ('teamId',99,'invalid_team_or_player')]:
            d=board();d['picks'][0][field]=value;self.assertIn(issue,draft_issues(d,{1,2}))
        d=board();d['picks'].pop();self.assertIn('selection_count_mismatch',draft_issues(d,{1,2}))

    def test_draft_activity_assignments_checked(self):
        self.assertFalse(draft_activity_audit(board(),[])['matchesAuthoritativeBoard'])

    def test_all_generated_seasons_contract(self):
        root=Path(__file__).resolve().parents[1]/'frontend/public/data/pocky-football'
        for year in range(2021,2027):
            with self.subTest(year=year):
                d=json.loads((root/str(year)/'activity.json').read_text());draft=json.loads((root/str(year)/'draft.json').read_text())
                teams={t['teamId'] for t in json.loads((root/str(year)/'league.json').read_text())['standings']}
                self.assertEqual(draft_issues(draft,teams),[])
                self.assertTrue(draft['coverage']['complete']);self.assertTrue(draft_activity_audit(draft,d['events'])['matchesAuthoritativeBoard'])
                self.assertEqual(validate_events(d['events'],teams),{'duplicateEventIds':[],'semanticDuplicateGroups':[],'issues':[]})
                c=d['coverage'];self.assertEqual(c['requestedPeriods'],c['successfulPeriods']);self.assertEqual(c['failedPeriods'],[])
                self.assertEqual(c['executedMovementCount'],len(d['events']));self.assertEqual(c['missingPlayerCount'],0)
                self.assertEqual(d['validation']['ownership']['anomalies'],[]);self.assertEqual(d['validation']['lineupWindows']['anomalies'],[])
                self.assertTrue(c['independentCounters']['dropsAndTradesMatch'])
                forbidden=('memberId','email','espn_s2','swid','cookie','token')
                def visit(v):
                    if isinstance(v,dict):
                        self.assertFalse(any(k.lower() in [f.lower() for f in forbidden] for k in v));[visit(x) for x in v.values()]
                    elif isinstance(v,list):[visit(x) for x in v]
                visit(d);visit(draft)

if __name__=='__main__':unittest.main()
