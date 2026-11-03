export async function dispatch(env, fetcher = fetch) {
  if (env.SCHEDULER_ENABLED !== 'true') return {status:'disabled'};
  if (!env.GITHUB_DISPATCH_TOKEN) throw new Error('Missing GitHub dispatch credential');
  const response = await fetcher('https://api.github.com/repos/fliou0704/pocky-football/actions/workflows/pages.yml/dispatches', {
    method:'POST', redirect:'error', signal:AbortSignal.timeout(15000),
    headers:{Authorization:`Bearer ${env.GITHUB_DISPATCH_TOKEN}`,Accept:'application/vnd.github+json',
      'Content-Type':'application/json','User-Agent':'PockyFootballCron','X-GitHub-Api-Version':'2022-11-28'},
    body:JSON.stringify({ref:'main',inputs:{mode:'auto'}})
  });
  // Never log a response body, headers, token or exception from the network layer.
  if (response.status !== 204) throw new Error(`GitHub dispatch HTTP ${response.status}`);
  return {status:'accepted'};
}

export default {
  fetch() {return new Response('Not found',{status:404});},
  async scheduled(event,env) {
    try {
      const result = await dispatch(env);
      console.log(JSON.stringify({component:'pocky-football-dispatch',scheduledTime:event.scheduledTime,...result}));
    } catch {
      console.error('Pocky Football dispatch failed; check GitHub credential, permissions and API availability');
      throw new Error('Pocky Football cron dispatch failed');
    }
  }
};
