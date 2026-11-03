import test from 'node:test';
import assert from 'node:assert/strict';
import worker,{dispatch} from '../src/worker.mjs';

test('disabled cron does not dispatch; no public dispatch endpoint',async()=>{
 let calls=0;assert.deepEqual(await dispatch({},()=>{calls++;}),{status:'disabled'});
 assert.equal(calls,0);assert.equal(worker.fetch().status,404);
});
test('constructs one auto dispatch to football main only',async()=>{
 let calls=0;
 const result=await dispatch({SCHEDULER_ENABLED:'true',GITHUB_TOKEN:'fixture'},async(url,options)=>{
  calls++;assert.equal(url,'https://api.github.com/repos/fliou0704/pocky-football/actions/workflows/pages.yml/dispatches');
  assert.equal(options.method,'POST');assert.equal(options.redirect,'error');
  assert.deepEqual(JSON.parse(options.body),{ref:'main',inputs:{mode:'auto'}});
  assert.equal(options.headers.Authorization,'Bearer fixture');return {status:204};
 });
 assert.equal(calls,1);assert.equal(result.status,'accepted');
});
test('errors are not treated as successful dispatches',async()=>{
 for (const status of [401,403,422,429,500]) {
  await assert.rejects(dispatch({SCHEDULER_ENABLED:'true',GITHUB_TOKEN:'fixture'},async()=>({status})),/GitHub dispatch HTTP/);
 }
 await assert.rejects(dispatch({SCHEDULER_ENABLED:'true'}),/Missing/);
});
