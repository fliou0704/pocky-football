import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from football_activity import normalize_transaction, collect_activity, generate_activity, movements_for_team


def transaction(kind='WAIVER',status='EXECUTED'):
    return {'id':'event-source','type':kind,'status':status,'isPending':False,
            'processDate':1750000000000,'proposedDate':1740000000000,'scoringPeriodId':4,
            'bidAmount':7,'executionType':'PROCESS','memberId':'private-member','cookie':'private-cookie',
            'items':[{'type':'ADD','playerId':10,'fromTeamId':0,'toTeamId':1},
                     {'type':'DROP','playerId':11,'fromTeamId':1,'toTeamId':0}]}


class ActivityTests(unittest.TestCase):
    def test_minimal_executed_add_drop_and_faab(self):
        event=normalize_transaction(transaction(),2025,{10:'Added',11:'Dropped'},{1,2},True)
        self.assertEqual(event['type'],'waiver_add')
        self.assertEqual(event['faab'],7)
        self.assertEqual(event['timestampKind'],'processed')
        self.assertEqual(event['teams'][0]['playersAdded'][0]['playerId'],10)
        self.assertEqual(event['teams'][0]['playersDropped'][0]['playerId'],11)
        self.assertNotIn('private',str(event))
        self.assertIsNone(normalize_transaction(transaction(),2025,{}, {1},False)['faab'])

    def test_failed_pending_and_empty_trade_status_not_assumed_executed(self):
        for status in ('PENDING','CANCELED',None,'FAILED_INVALIDPLAYERSOURCE'):
            self.assertIsNone(normalize_transaction(transaction(status=status),2021,{}, {1}))
        self.assertIsNotNone(normalize_transaction({**transaction('TRADE_ACCEPT'), 'isPending':True,
            'items':[{'type':'TRADE','playerId':10,'fromTeamId':1,'toTeamId':2}]},2021,{}, {1,2}))

    def test_trade_participants_and_player_transfers(self):
        raw={**transaction('TRADE_ACCEPT'),'items':[{'type':'TRADE','playerId':10,'fromTeamId':1,'toTeamId':2},
                                                  {'type':'TRADE','playerId':11,'fromTeamId':2,'toTeamId':1}]}
        event=normalize_transaction(raw,2025,{10:'A',11:'B'},{1,2})
        self.assertEqual(event['type'],'trade')
        self.assertEqual([t['teamId'] for t in event['teams']],[1,2])
        self.assertEqual(event['teams'][0]['playersAdded'][0]['playerId'],11)
        self.assertEqual(event['teams'][1]['playersAdded'][0]['playerId'],10)
        self.assertEqual(movements_for_team({'events':[event]},1)[0]['type'],'trade')

    def test_historical_period_sweep_deduplicates_and_marks_partial(self):
        calls=[]
        class Client:
            def league_get(self,params):
                if params['view']==['mStatus','mSettings']:
                    return {'status':{'latestScoringPeriod':2,'transactionScoringPeriod':3,'finalScoringPeriod':2},
                            'settings':{'acquisitionSettings':{'isUsingAcquisitionBudget':False}}}
                calls.append(params['scoringPeriodId'])
                if params['scoringPeriodId']==2:raise ValueError('Unavailable')
                return {'status':{},'transactions':[transaction()]}
            def get_player_card(self,ids,max_period):
                return {'players':[{'id':i,'player':{'fullName':str(i)},'transactions':[transaction()]} for i in ids]}
        result=collect_activity(Client(),2021,{10:'A'},{1})
        self.assertEqual(calls,[0,1,2,3])
        self.assertFalse(result['coverage']['complete'])
        self.assertEqual(result['coverage']['failedPeriods'],[2])
        self.assertEqual(len(result['events']),1)
        self.assertEqual(result['events'][0]['season'],2021)

    def test_playercard_restores_executed_trade_not_in_period_feed(self):
        class Client:
            def league_get(self,params):
                if isinstance(params['view'],list):return {'status':{'latestScoringPeriod':1,'transactionScoringPeriod':1,'finalScoringPeriod':17},'settings':{'acquisitionSettings':{}}}
                return {'status':{},'transactions':[]}
            def get_player_card(self,ids,max_period):
                return {'players':[{'id':10,'player':{'fullName':'A'},'transactions':[{**transaction('TRADE_ACCEPT'),'items':[{'type':'TRADE','playerId':10,'fromTeamId':1,'toTeamId':2}]}]}]}
        data=collect_activity(Client(),2025,{10:'A'},{1,2})
        self.assertEqual(data['events'][0]['type'],'trade')
        self.assertFalse(data['coverage']['complete'])

    def test_failed_refresh_preserves_previous_events_with_stale_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            event=normalize_transaction(transaction(),2025,{10:'A',11:'B'},{1})
            path=Path(folder)/'activity.json'
            path.write_text(json.dumps({'schemaVersion':1,'season':2025,'events':[event],'coverage':{'complete':False}}))
            with patch('football_activity.collect_activity',side_effect=ValueError('Failure')):
                result=generate_activity(None,folder,2025,{1})
            self.assertEqual(result['events'],[event])
            self.assertEqual(result['coverage']['status'],'stale')
            self.assertFalse(result['coverage']['complete'])

    def test_lineup_only_moves_and_unknown_teams_are_excluded(self):
        self.assertIsNone(normalize_transaction({**transaction('ROSTER'),'items':[{'type':'LINEUP','playerId':10}]},2025,{}, {1}))
        self.assertIsNone(normalize_transaction(transaction(),2025,{}, {9}))


if __name__=='__main__':unittest.main()
