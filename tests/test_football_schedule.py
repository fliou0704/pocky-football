from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from football_schedule import decide, plan, complete, instant, normalize

UTC=timezone.utc
NOW=datetime(2026,11,1,17,0,tzinfo=UTC)


def event(kickoff=NOW+timedelta(minutes=30), state='pre', name='STATUS_SCHEDULED', eid='1', completed=False):
    return {'id':eid,'kickoff':kickoff.isoformat(),'state':state,'name':name,'completed':completed}


class ScheduleTests(unittest.TestCase):
    def test_every_weekday_international_holiday_and_pregame(self):
        for day in range(7):
            for hour in (1,9,14,20):
                now=NOW+timedelta(days=day,hours=hour-17)
                with self.subTest(day=day,hour=hour):
                    d,_=decide([event(now+timedelta(minutes=60))],now=now)
                    self.assertTrue(d['due']);self.assertEqual(d['mode'],'live')
                    d,_=decide([event(now+timedelta(minutes=61))],now=now)
                    self.assertFalse(d['due'])

    def test_no_game_empty_day_and_future(self):
        for events in ([],[event(NOW+timedelta(days=3))]):
            d,_=decide(events,now=NOW);self.assertFalse(d['due'])

    def test_overlap_sunday_late_finish_and_gap(self):
        early=event(NOW-timedelta(hours=5),'in','STATUS_IN_PROGRESS')
        evening=event(NOW+timedelta(minutes=40),eid='2')
        d,_=decide([early,evening],now=NOW);self.assertTrue(d['due'])
        early['completed']=True
        d,s=decide([early,evening],now=NOW)
        d,s=decide([early,evening],s,NOW+timedelta(hours=2));self.assertTrue(d['due'])
        d,_=decide([event(NOW+timedelta(hours=3))],now=NOW);self.assertFalse(d['due'])

    def test_actual_final_time_drives_postgame_and_full_once(self):
        final=event(NOW-timedelta(hours=2),'post','STATUS_FINAL',completed=True)
        d,s=decide([final],now=NOW);self.assertEqual(d['mode'],'live')
        d,s=decide([final],s,NOW+timedelta(minutes=59));self.assertEqual(d['mode'],'live')
        d,s=decide([final],s,NOW+timedelta(minutes=61));self.assertEqual(d['mode'],'full')
        s['reconciledIds']=['1'];d,_=decide([final],s,NOW+timedelta(minutes=62));self.assertFalse(d['due'])

    def test_delay_postponement_reschedule_and_unknown_timeout(self):
        delayed=event(NOW-timedelta(hours=6),'in','STATUS_DELAYED')
        d,_=decide([delayed],now=NOW);self.assertTrue(d['due'])
        delayed['name']='STATUS_POSTPONED'
        d,_=decide([delayed],now=NOW);self.assertFalse(d['due'])
        delayed.update(kickoff=(NOW+timedelta(days=1)).isoformat(),name='STATUS_SCHEDULED',state='pre')
        d,_=decide([delayed],now=NOW+timedelta(days=1,minutes=-30));self.assertTrue(d['due'])
        d,_=decide([event(NOW-timedelta(hours=25),'in','STATUS_SUSPENDED')],now=NOW)
        self.assertFalse(d['due']);self.assertEqual(d['needsAttention'],['1'])

    def test_late_action_duplicate_prevention_and_next_slot(self):
        events=[event(NOW-timedelta(hours=2),'in','STATUS_IN_PROGRESS')]
        state={'lastSuccessfulAt':(NOW+timedelta(minutes=3)).isoformat()}
        d,_=decide(events,state,NOW+timedelta(minutes=14));self.assertFalse(d['due'])
        d,_=decide(events,state,NOW+timedelta(minutes=17));self.assertTrue(d['due'])

    def test_dst_and_utc_equivalent_clocks(self):
        a=instant('2026-11-01T01:30:00-04:00'); b=instant('2026-11-01T01:30:00-05:00')
        self.assertEqual(b-a,timedelta(hours=1))
        spring=instant('2026-03-08T03:30:00-04:00')
        self.assertEqual(spring,datetime(2026,3,8,7,30,tzinfo=UTC))
        for clock in [a,b,spring]:
            d,_=decide([event(clock+timedelta(minutes=20))],now=clock);self.assertTrue(d['due'])

    def test_disabled_no_requests_dry_run_no_state_and_failure_preserves(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.json';fetch=Mock()
            self.assertFalse(plan(path,fetch=fetch)['due']);fetch.assert_not_called()
            raw={'leagues':[{}],'events':[{'id':'1','date':(NOW+timedelta(minutes=30)).isoformat(),
                 'status':{'type':{'state':'pre','name':'STATUS_SCHEDULED','completed':False}}}]}
            fetch.return_value=raw
            self.assertTrue(plan(path,dry_run=True,now=NOW,fetch=fetch)['due']);self.assertFalse(path.exists())
            self.assertTrue(plan(path,enabled=True,now=NOW,fetch=fetch)['due'])
            complete(path,'live',NOW)
            self.assertFalse(plan(path,enabled=True,now=NOW,fetch=fetch)['due'])
            before=path.read_bytes();fetch.side_effect=ValueError()
            self.assertFalse(plan(path,enabled=True,now=NOW,fetch=fetch)['due']);self.assertEqual(before,path.read_bytes())

    def test_invalid_source_and_baseline_full_suppresses_reconciliation(self):
        with self.assertRaises(ValueError):normalize({'events':[]})
        final=event(NOW-timedelta(hours=3),'post','STATUS_FINAL',completed=True)
        state={'finalSeenAt':{'1':(NOW-timedelta(hours=2)).isoformat()},'lastFullAt':(NOW-timedelta(hours=1)).isoformat()}
        d,_=decide([final],state,NOW);self.assertFalse(d['due'])

    def test_holiday_and_saturday_windows_are_timestamp_driven(self):
        for kickoff in [instant('2026-11-26T17:30:00Z'),instant('2026-12-19T21:30:00Z')]:
            d,_=decide([event(kickoff)],now=kickoff-timedelta(minutes=45));self.assertTrue(d['due'])

    def test_long_observed_game_gets_real_postgame_window_and_old_cold_final_does_not(self):
        delayed=event(NOW-timedelta(hours=14),'in','STATUS_DELAYED')
        _,state=decide([delayed],now=NOW)
        final={**delayed,'completed':True,'state':'post','name':'STATUS_FINAL'}
        d,_=decide([final],state,NOW+timedelta(minutes=10));self.assertEqual(d['mode'],'live')
        d,state=decide([final],now=NOW);self.assertEqual(d['mode'],'full')
        d,_=decide([final],state,NOW+timedelta(minutes=15));self.assertEqual(d['mode'],'full')


if __name__ == '__main__': unittest.main()
