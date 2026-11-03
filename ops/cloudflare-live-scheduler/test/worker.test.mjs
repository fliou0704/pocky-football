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
  assert.equal(options.method,'POST');assert.equal(options.redirect,'manual');
  assert.deepEqual(JSON.parse(options.body),{ref:'main',inputs:{mode:'auto'}});
  assert.equal(options.headers.Authorization,'Bearer fixture');return {status:204};
 });
 assert.equal(calls,1);assert.equal(result.status,'accepted');
});
test('errors are not treated as successful dispatches',async()=>{
 for (const status of [401,403,422,429,500]) {
  await assert.rejects(dispatch({SCHEDULER_ENABLED:'true',GITHUB_TOKEN:'fixture'},async()=>({status})),e=>e.category==='github_http' && e.httpStatus===status);
 }
 await assert.rejects(dispatch({SCHEDULER_ENABLED:'true'}),e=>e.category==='missing_token');
});

test('scheduled logs distinguish safe failure categories and acceptance',async()=>{
 const originalFetch=globalThis.fetch, originalLog=console.log, originalError=console.error;
 const logs=[];
 console.log=console.error=value=>logs.push(JSON.parse(value));
 try {
  for (const token of [undefined,'','   ']) {
   globalThis.fetch=()=>{throw Error('must not fetch');};
   await assert.rejects(worker.scheduled({scheduledTime:1},{SCHEDULER_ENABLED:'true',GITHUB_TOKEN:token}));
   assert.equal(logs.at(-1).category,'missing_token');
  }
  const env={SCHEDULER_ENABLED:'true',GITHUB_TOKEN:'sensitive-fixture'};
  globalThis.fetch=async()=>({status:403,body:'private-response'});
  await assert.rejects(worker.scheduled({scheduledTime:1},env));
  assert.deepEqual(logs.at(-1),{component:'pocky-football-dispatch',scheduledTime:1,status:'error',category:'github_http',httpStatus:403});
  for (const [name,category] of [['TimeoutError','timeout'],['AbortError','timeout'],['TypeError','network']]) {
   globalThis.fetch=async()=>{throw Object.assign(Error('sensitive-fixture Authorization private-response'),{name});};
   await assert.rejects(worker.scheduled({scheduledTime:1},env));
   assert.equal(logs.at(-1).category,category);
  }
  globalThis.fetch=async()=>({status:204});
  await worker.scheduled({scheduledTime:1},env);
  assert.equal(logs.at(-1).status,'accepted');
  assert.doesNotMatch(JSON.stringify(logs),/sensitive-fixture|Authorization|private-response/);
 } finally {
  globalThis.fetch=originalFetch;console.log=originalLog;console.error=originalError;
 }
});
