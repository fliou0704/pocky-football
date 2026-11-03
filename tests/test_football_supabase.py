import copy
import unittest
from unittest.mock import Mock, patch
from datetime import datetime,timezone

from football_live import digest
from football_supabase import publish, PublicationError, PROJECT, main


class SupabaseTests(unittest.TestCase):
    def setUp(self):
        self.snapshot={'schemaVersion':1,'leagueId':668411840,'season':2026,'week':9,
          'matchups':[{'homeTeamId':1,'awayTeamId':2,'homeScore':1,'awayScore':0}],
          'lineups':{'teams':{'1':[{'playerId':1,'points':1}],'2':[{'playerId':2,'points':0}]}},
          'adjustments':{'1':0,'2':0},'semantics':'fixture','baseGenerationId':'b'*64,'sourceFileHashes':{}}
        self.snapshot['snapshotId']=digest(self.snapshot)
        self.snapshot['fetchedAt']=datetime.now(timezone.utc).isoformat()
        self.meta={'mode':'live','generationId':'a'*64}
        self.row={'snapshot':self.snapshot,'revision':self.snapshot['snapshotId'],
                  'generation_id':self.meta['generationId'],'source_at':self.snapshot['fetchedAt'],'is_public':True}

    def response(self,value,status=200):return Mock(status_code=status,json=lambda:value)

    def run_publish(self,values):
        request=Mock(side_effect=[self.response(v) for v in values])
        result=publish(self.snapshot,self.meta,PROJECT,'server-test','public-test',request)
        return result,request

    def test_success_and_independent_public_readback(self):
        action,request=self.run_publish([[],{'action':'published'},[self.row],[self.row]])
        self.assertEqual(action,'published');self.assertEqual(request.call_count,4)
        self.assertEqual(request.call_args_list[-1].kwargs['headers']['apikey'],'public-test')
        self.assertFalse(request.call_args_list[1].kwargs['allow_redirects'])

    def test_unchanged_has_no_write(self):
        action,request=self.run_publish([[self.row],[self.row],[self.row]])
        self.assertEqual(action,'unchanged');self.assertTrue(all(c.args[0]=='GET' for c in request.call_args_list))

    def test_stale_and_invalid_rejected(self):
        row={**self.row,'source_at':'2099-01-01T00:00:00Z'}
        with self.assertRaises(PublicationError):self.run_publish([[row]])
        self.snapshot['week']=10
        with self.assertRaises(PublicationError):self.run_publish([])

    def test_failed_write_or_readback_not_reported_success(self):
        with self.assertRaises(PublicationError):self.run_publish([[],{'action':'stale'}])
        with self.assertRaises(PublicationError):self.run_publish([[],{'action':'published'},[self.row],[]])
        request=Mock(return_value=self.response({},503))
        with self.assertRaises(PublicationError):publish(self.snapshot,self.meta,PROJECT,'server','public',request)

    def test_entrypoint_validates_before_publication_and_handles_failure(self):
        import football_supabase as module
        with patch.object(module,'load_dotenv'),patch.object(module,'read',side_effect=[self.meta,self.snapshot]),patch.object(module,'validate') as validate,patch.object(module,'publish',side_effect=PublicationError()):
            self.assertEqual(main(),1);validate.assert_called_once()

    def test_sql_restricts_writes_and_serializes_publication(self):
        from pathlib import Path
        sql=(Path(__file__).resolve().parents[1]/'supabase/migrations/202611030001_football_live.sql').read_text()
        for requirement in ('enable row level security','using (is_public)','from public,anon,authenticated',
                            'to service_role','pg_advisory_xact_lock','v_source <= v_old.source_at'):
            self.assertIn(requirement,sql)
        self.assertEqual(sql.count('create policy '),1)


if __name__=='__main__':unittest.main()
