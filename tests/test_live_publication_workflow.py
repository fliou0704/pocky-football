"""Evaluate the workflow's publication gates for full/live/unchanged outcomes."""
from pathlib import Path
import re
import unittest


class WorkflowTests(unittest.TestCase):
    def test_publication_paths(self):
        source=(Path(__file__).resolve().parents[1]/'.github/workflows/pages.yml').read_text()
        steps=[]
        for line in source.splitlines():
            if line.startswith('      - '):
                steps.append({});line='        '+line[8:]
            match=re.match(r'        (uses|id|if): (.*)',line)
            if steps and match: steps[-1][match[1]]=match[2]
        for mode,changed in [('live','true'),('live','false'),('full','true')]:
            context={'github.event_name':'workflow_dispatch','steps.refresh.outputs.mode':mode,
                     'steps.refresh.outputs.changed':changed,'steps.refresh.outcome':'success',
                     'steps.guard.outcome':'success','steps.persistence.outcome':'success',
                     'steps.supabase.outcome':'success','steps.verification.outcome':'success'}
            def enabled(step):
                expr=step['if'].replace("hashFiles('frontend/public/data/pocky-football/refresh.json')", "'present'")
                expr=re.sub(r'\b(?:github|steps)\.[A-Za-z0-9_.]+',lambda m:repr(context[m[0]]),expr)
                return eval(expr.replace('&&',' and ').replace('||',' or '),{'__builtins__':{}},{})
            for step in steps:
                if step.get('uses','').startswith(('pnpm/','actions/setup-node','actions/deploy-pages','actions/upload-pages')) or step.get('id')=='verification' or step.get('name') in ('Install frontend dependencies','Test and build frontend'):
                    self.assertEqual(enabled(step),mode=='full')
            for sid in ('guard','supabase','persistence'):
                actual=enabled(next(s for s in steps if s.get('id')==sid))
                expected=(mode=='live') if sid=='supabase' else changed=='true' if sid=='persistence' else True
                self.assertEqual(actual,expected)
        self.assertIn('      group: github-pages',source)


if __name__=='__main__':unittest.main()
