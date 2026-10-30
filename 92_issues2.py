import json, urllib.request, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
def get(u):
    for i in range(3):
        try:
            req=urllib.request.Request(u, headers={'User-Agent':'dsh','Accept':'application/vnd.github+json'})
            return json.load(urllib.request.urlopen(req, timeout=40))
        except Exception:
            if i==2: raise
            time.sleep(1)
for n in (3,4):
    issue=get(f'https://api.github.com/repos/Fishason/Claude-anti-ban/issues/{n}')
    print('='*30, '#%s'%n, issue['title'], 'body=',repr(issue['body'])[:500])
    for c in get(f'https://api.github.com/repos/Fishason/Claude-anti-ban/issues/{n}/comments'):
        print('---',c['user']['login'],c['created_at'][:10]); print(c['body'][:800])
