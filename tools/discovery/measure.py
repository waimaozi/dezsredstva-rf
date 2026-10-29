#!/usr/bin/env python3
"""Read-only discovery snapshot. No scheduler, publication or account mutations."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shlex
import subprocess

# Credentials enter the remote process over stdin, never in command arguments.
REMOTE = r'''
import sys,json,urllib.request,urllib.parse,urllib.error,datetime,base64,ssl,socket,re,xml.etree.ElementTree as E
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
p=json.load(sys.stdin)
def get(url,headers,body=None,timeout=20):
 try:
  req=urllib.request.Request(url,data=json.dumps(body,ensure_ascii=False).encode() if body else None,headers=dict(headers,**({'Content-Type':'application/json'} if body else {})))
  with urllib.request.urlopen(req,timeout=timeout) as r:return {'status':r.status,'data':json.load(r)}
 except Exception as e:
  reason=getattr(e,'reason',e)
  category='timeout' if isinstance(reason,(TimeoutError,socket.timeout)) else 'tls' if isinstance(reason,ssl.SSLError) else 'http' if getattr(e,'code',None) else 'transport'
  result={'status':getattr(e,'code',None),'error':type(e).__name__,'category':category}
  if isinstance(e,urllib.error.HTTPError):
   try:
    code=json.loads(e.read(4096)).get('error_code')
    if isinstance(code,str) and re.fullmatch('[A-Z_]{1,64}',code):result['api_error_code']=code
   except (ValueError,OSError,AttributeError):pass
  return result
jobs=[
 ('totals',None,'ym:s:visits,ym:s:users,ym:s:pageviews,ym:s:goal672237966reaches',None),
 ('search_engines','ym:s:lastSearchEngineRoot','ym:s:visits',"ym:s:lastTrafficSource=='organic'"),
 ('landing_pages','ym:s:startURL','ym:s:visits,ym:s:goal672237966reaches',None),
 ('returning_visitors','ym:s:isNewUser','ym:s:visits,ym:s:users',None),
 ('reader_goals',None,','.join('ym:s:goal'+str(goal)+'reaches' for goal in p['reader_goals']['goals'].values()),None),
 ('reader_responses','ym:ep:actionGoal,ym:ep:eventParamsLevel1,ym:ep:eventParamsLevel2,ym:ep:eventParamsLevel3,ym:ep:eventParamsLevel4,ym:ep:eventParamsLevel5','ym:ep:eventsNumber,ym:ep:users',"ym:ep:eventParamsLevel1=='research_v1'"),
]
def metrika(job):
 name,dimension,metrics,filters=job
 args={'ids':'107711899','date1':p['start'],'date2':p['end'],'metrics':metrics,'accuracy':'full','limit':1000}
 if dimension:args['dimensions']=dimension
 if filters:args['filters']=filters
 return name,get('https://api-metrika.yandex.net/stat/v1/data?'+urllib.parse.urlencode(args),{'Authorization':'OAuth '+p['oauth']})
with ThreadPoolExecutor(max_workers=2) as pool:results=dict(pool.map(metrika,jobs))
out={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'period':[p['start'],p['end']],'metrika':results,'reader_measurement':p['reader_measurement'],'limitations':['Search API documents returned are not an authenticated index count.','Landing-page goal counts attribute downloads to visit entry, not necessarily to the article downloaded.','An API failure means unknown, not zero.','Reader events are measured only from the instrumented_since date; earlier zeros do not mean no engagement.','90 seconds in a focused visible tab with content onscreen and 50% reached is an engagement proxy, not proof of reading or usefulness.','Usefulness and role are voluntary self-reports, not verified professional identity. Analytics blockers and unavailable session storage limit coverage and deduplication.','Reader response rows use event parameters, not landing-page attribution. Users across rows or overlapping daily periods must not be added.']}
if p.get('search_key_file'):
 try:
  key=Path(p['search_key_file']).expanduser().read_text().strip()
  body={'query':{'searchType':'SEARCH_TYPE_RU','queryText':'site:дезинфицирующиесредства.рф','fixTypoMode':'FIX_TYPO_MODE_OFF'},'groupSpec':{'groupMode':'GROUP_MODE_FLAT','groupsOnPage':'20','docsInGroup':'1'},'maxPassages':'1','region':'193','responseFormat':'FORMAT_XML'}
  result=get('https://searchapi.api.cloud.yandex.net/v2/web/search',{'Authorization':'Api-Key '+key},body)
  if result['status']==200 and 'rawData' in result.get('data',{}):
   raw=base64.b64decode(result['data']['rawData']).decode();root=E.fromstring(raw)
   error=root.find('.//error')
   result={'status':200,'region':'193','query':body['query']['queryText'],'documents':[{'url':d.findtext('url'),'title':''.join(d.find('title').itertext()) if d.find('title') is not None else ''} for d in root.findall('.//group/doc')],'search_error':root.findtext('.//error'),'search_error_code':error.get('code') if error is not None else None,'xml':raw}
  out['yandex_search']=result
 except Exception as e:out['yandex_search']={'error':type(e).__name__}
if p.get('webmaster'):
 result=get('https://api.webmaster.yandex.net/v4/user',{'Authorization':'OAuth '+p['oauth']},timeout=12)
 out['webmaster_access']=result
 if result['status']==200:
  user=result['data'].get('user_id')
  if user:
   hosts=get(f'https://api.webmaster.yandex.net/v4/user/{user}/hosts/',{'Authorization':'OAuth '+p['oauth']})
   target=next((x for x in hosts.get('data',{}).get('hosts',[]) if 'xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai' in x.get('host_id','')),None)
   out['webmaster_target_host']=target
   if target:out['webmaster_summary']=get(f"https://api.webmaster.yandex.net/v4/user/{user}/hosts/{target['host_id']}/summary",{'Authorization':'OAuth '+p['oauth']})
print(json.dumps(out,ensure_ascii=False))
'''

def reader_measurement(start, end, config):
    since = dt.date.fromisoformat(config['instrumented_since'])
    pending = config.get('deployment_pending', False)
    coverage = 'awaiting_deployment' if pending else 'not_measured' if end < since else 'partial_period' if start <= since else 'measured'
    return {**config, 'coverage': coverage,
            'observed_period': None if pending or end < since else [str(max(start, since)), str(end)],
            'goal_metric_order': list(config['goals']),
            'response_dimensions': ['goal', 'schema', 'content_kind', 'article_path', 'self_reported_role', 'response']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--oauth-file', type=Path, required=True)
    parser.add_argument('--ssh', help='Existing SSH alias; omit to run API reads locally')
    parser.add_argument('--search-key-file', help='Optional API-key path on the machine performing the requests')
    parser.add_argument('--webmaster', action='store_true')
    parser.add_argument('--reader-goals', type=Path, default=Path(__file__).with_name('reader-goals.json'))
    parser.add_argument('--start', type=dt.date.fromisoformat)
    parser.add_argument('--end', type=dt.date.fromisoformat)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    end = args.end or dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date() - dt.timedelta(days=1)
    start = args.start or end - dt.timedelta(days=6)
    if start > end:
        parser.error('--start must not be after --end')
    config = json.loads(args.reader_goals.read_text())
    if not config.get('goals') or any(type(value) is not int or value <= 0 for value in config['goals'].values()):
        parser.error('Reader goal IDs must be positive integers')
    payload = {'oauth': args.oauth_file.expanduser().read_text().splitlines()[0].strip(),
               'start': str(start), 'end': str(end), 'search_key_file': args.search_key_file,
               'webmaster': args.webmaster, 'reader_goals': config,
               'reader_measurement': reader_measurement(start, end, config)}
    command = ['python3', '-c', REMOTE]
    if args.ssh:
        command = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=50', args.ssh,
                   'python3 -c ' + shlex.quote(REMOTE)]
    result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True, timeout=125)
    if result.returncode:
        raise SystemExit('Snapshot transport failed; no data accepted.')
    data = json.loads(result.stdout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'period': data['period'], 'metrika_statuses': {k:v['status'] for k,v in data['metrika'].items()},
                      'search_status': data.get('yandex_search',{}).get('status'),
                      'webmaster_status': data.get('webmaster_access',{}).get('status'), 'out': str(args.out)}))

if __name__ == '__main__':
    main()
