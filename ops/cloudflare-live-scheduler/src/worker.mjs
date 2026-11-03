class DispatchError extends Error {
  constructor(category, httpStatus) {
    super('Pocky Football dispatch failed');
    this.category = category;
    if (Number.isInteger(httpStatus)) this.httpStatus = httpStatus;
  }
}

export async function dispatch(env, fetcher = fetch) {
  if (env.SCHEDULER_ENABLED !== 'true') return {status:'disabled'};
  if (typeof env.GITHUB_TOKEN !== 'string' || !env.GITHUB_TOKEN.trim()) throw new DispatchError('missing_token');
  let response;
  try {
    response = await fetcher('https://api.github.com/repos/fliou0704/pocky-football/actions/workflows/pages.yml/dispatches', {
    method:'POST', redirect:'error', signal:AbortSignal.timeout(15000),
    headers:{Authorization:`Bearer ${env.GITHUB_TOKEN}`,Accept:'application/vnd.github+json',
      'Content-Type':'application/json','User-Agent':'PockyFootballCron','X-GitHub-Api-Version':'2022-11-28'},
    body:JSON.stringify({ref:'main',inputs:{mode:'auto'}})
    });
  } catch (error) {
    throw new DispatchError(['TimeoutError','AbortError'].includes(error?.name) ? 'timeout' : 'network');
  }
  // Never log a response body, headers, token or exception from the network layer.
  if (response.status !== 204) throw new DispatchError('github_http', response.status);
  return {status:'accepted'};
}

export default {
  fetch() {return new Response('Not found',{status:404});},
  async scheduled(event,env) {
    try {
      const result = await dispatch(env);
      console.log(JSON.stringify({component:'pocky-football-dispatch',scheduledTime:event.scheduledTime,...result}));
    } catch (error) {
      const detail = error instanceof DispatchError
        ? {category:error.category, ...(error.httpStatus === undefined ? {} : {httpStatus:error.httpStatus})}
        : {category:'internal'};
      console.error(JSON.stringify({component:'pocky-football-dispatch',scheduledTime:event.scheduledTime,status:'error',...detail}));
      throw new Error('Pocky Football cron dispatch failed');
    }
  }
};
