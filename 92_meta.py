import json, urllib.request, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
def get(u):
    req=urllib.request.Request(u, headers={'User-Agent':'dsh','Accept':'application/vnd.github+json'})
    return json.load(urllib.request.urlopen(req, timeout=40))
for path in ('CONTRIBUTING.md','.github/ISSUE_TEMPLATE/bug_report.md','.github/ISSUE_TEMPLATE/share_experience.md'):
    print('='*20, path)
    print(get(f'https://api.github.com/repos/Fishason/Claude-anti-ban/contents/{path}')['download_url'])
print('='*20,'commits')
cs=get('https://api.github.com/repos/Fishason/Claude-anti-ban/commits?per_page=20')
for c in cs:
    print(c['sha'][:8], c['commit']['author']['date'], c['commit']['message'].splitlines()[0][:80])
print('='*20,'issues')
iss=get('https://api.github.com/repos/Fishason/Claude-anti-ban/issues?state=all&per_page=50')
for x in iss:
    print('#%s %s c=%s %s %s'%(x['number'],x['state'],x['comments'],x['created_at'][:10],x['title'][:80]))
