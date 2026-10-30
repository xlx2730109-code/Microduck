import json, urllib.request, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
def get(u):
    for i in range(3):
        try:
            req=urllib.request.Request(u, headers={'User-Agent':'dsh','Accept':'application/vnd.github+json'})
            return json.load(urllib.request.urlopen(req, timeout=40))
        except Exception as e:
            if i==2: raise
            time.sleep(1)
for path in ('CONTRIBUTING.md','.github/ISSUE_TEMPLATE/bug_report.md','.github/ISSUE_TEMPLATE/share_experience.md'):
    print('='*20, path)
    d=get(f'https://api.github.com/repos/Fishason/Claude-anti-ban/contents/{path}')
    print(urllib.request.urlopen(d['download_url'],timeout=40).read().decode('utf-8')[:2500])
print('='*20,'commits')
for c in get('https://api.github.com/repos/Fishason/Claude-anti-ban/commits?per_page=20'):
    print(c['sha'][:8], c['commit']['author']['date'], c['commit']['message'].splitlines()[0][:80])
print('='*20,'issues')
for x in get('https://api.github.com/repos/Fishason/Claude-anti-ban/issues?state=all&per_page=50'):
    print('#%s %s c=%s %s %s'%(x['number'],x['state'],x['comments'],x['created_at'][:10],x['title'][:80]))
