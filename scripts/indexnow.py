"""Notify changed public HTML URLs after verifying the deployed key file."""
import argparse,json,subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from seo import ROOT,BASE,pages,canonical
KEY='c4c0dc80b94f7dcc55c8791ba1277caf'
KEY_LOCATION=BASE+KEY+'.txt'
def changed_urls(before,after):
 if not before:return [canonical(p) for p in pages()]
 names=subprocess.check_output(['git','diff','--name-only',before,after],cwd=ROOT,text=True).splitlines()
 return sorted({BASE+(n.removesuffix('index.html') if n!='index.html' else '') for n in names if n=='index.html' or n.endswith('/index.html') and not n.startswith(('backend/','.','scripts/'))})
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--before');parser.add_argument('--after',default='HEAD');parser.add_argument('--report',default='/tmp/indexnow-receipt.json');args=parser.parse_args()
 urls=changed_urls(args.before,args.after)
 report={'urls':urls,'keyLocation':KEY_LOCATION,'outcome':'unchanged'}
 if urls:
  with urlopen(KEY_LOCATION,timeout=35) as r:assert r.status==200 and r.read().decode().strip()==KEY,'Invalid published key'
  payload={'host':'oluwafemi1x.github.io','key':KEY,'keyLocation':KEY_LOCATION,'urlList':urls}
  req=Request('https://api.indexnow.org/indexnow',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
  try:
   with urlopen(req,timeout=35) as r:code,body=r.status,r.read().decode()
  except HTTPError as e:code,body=e.code,e.read().decode()
  report.update(responseCode=code,body=body,outcome='received' if code==200 else 'key_validation_pending' if code==202 else 'rejected')
 Path(args.report).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 if urls and report['responseCode'] not in (200,202):raise SystemExit(1)
