import unittest
from football_player_scoring import preserve_observed_weeks

class PreservationTests(unittest.TestCase):
    def test_sparse_week_preserved_but_correction_wins(self):
        old={'players':[{'playerId':4241474,'pointsByWeek':{'7':8.5,'8':2},'nflTeamsByWeek':{'7':'SF'}}]}
        new={'players':[{'playerId':4241474,'pointsByWeek':{'8':3},'nflTeamsByWeek':{}}],'coverage':{}}
        preserve_observed_weeks(new,old)
        self.assertEqual(new['players'][0]['pointsByWeek'],{'7':8.5,'8':3})
        self.assertEqual(new['coverage']['retainedObservedWeeks'][0]['source'],'previous-validated-snapshot')
    def test_missing_player_not_silently_restored(self):
        new={'players':[],'coverage':{}}
        preserve_observed_weeks(new,{'players':[{'playerId':1,'pointsByWeek':{'1':2}}]})
        self.assertEqual(new['players'],[])
