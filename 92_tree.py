import json, urllib.request, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
def get(u):
    req=urllib.request.Request(u, headers={'User-Agent':'dsh','Accept':'application/vnd.github+json'})
    return json.load(urllib.request.urlopen(req, timeout=40))
r=get('https://api.github.com/repos/Fishason/Claude-anti-ban')
for k in ('full_name','description','created_at','pushed_at','stargazers_count','forks_count','open_issues_count','size','default_branch','license','homepage','topics'):
    print(k,'=',r.get(k))
t=get(f"https://api.github.com/repos/Fishason/Claude-anti-ban/git/trees/{r['default_branch']}?recursive=1")
json.dump(t,open('92_antib an_tree.json','w',encoding='utf-8'),ensure_ascii=False)
print('truncated',t.get('truncated'),'entries',len(t['tree']))
for f in sorted(t['tree'],key=lambda x:x['path']):
    if f['type']=='blob': print(f"{f.get('size',0):8} {f['path']}")
