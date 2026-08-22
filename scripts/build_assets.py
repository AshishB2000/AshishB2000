"""Generate dist/stats.svg and dist/now.svg (Tokyo Night themed) from the GitHub API."""
import json, os, urllib.request, datetime, re
from xml.sax.saxutils import escape

LOGIN = "AshishB2000"
TOKEN = os.environ["GITHUB_TOKEN"]
FONT = 'font-family="Segoe UI, Helvetica, Arial, sans-serif"'
os.makedirs("dist", exist_ok=True)


def gh(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"Authorization": f"bearer {TOKEN}", "User-Agent": LOGIN,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


# ---------------- stats ----------------
Q = """query($login:String!){ user(login:$login){
  followers{totalCount}
  repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC){ totalCount
    nodes{ stargazerCount isFork languages(first:10, orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name color } } } } }
  contributionsCollection{ totalCommitContributions totalPullRequestContributions totalIssueContributions totalRepositoriesWithContributedCommits }
}}"""
u = gh("https://api.github.com/graphql", {"query": Q, "variables": {"login": LOGIN}})["data"]["user"]
repos = [r for r in u["repositories"]["nodes"] if not r["isFork"]]
stars = sum(r["stargazerCount"] for r in repos)
c = u["contributionsCollection"]
langs = {}
for r in repos:
    for e in r["languages"]["edges"]:
        n = e["node"]["name"]
        langs.setdefault(n, [0, e["node"]["color"] or "#7aa2f7"])[0] += e["size"]
top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]
total = sum(v[0] for _, v in top) or 1

tiles = [("Stars", stars), ("Repos", u["repositories"]["totalCount"]), ("Commits · 12mo", c["totalCommitContributions"]),
         ("Pull requests", c["totalPullRequestContributions"]), ("Issues", c["totalIssueContributions"]), ("Followers", u["followers"]["totalCount"])]

parts = []
for i, (label, val) in enumerate(tiles):
    col, row = i % 3, i // 3
    x, y = 40 + col * 190, 50 + row * 90
    d = 0.15 * i
    parts.append(f'''<g><animate attributeName="opacity" values="0;0;1" keyTimes="0;{d/(d+0.6):.4f};1" dur="{d+0.6:.2f}s" begin="0s" fill="freeze"/>
  <rect x="{x}" y="{y}" width="170" height="72" rx="12" fill="#161728" stroke="#24283b"/>
  <text x="{x+16}" y="{y+36}" {FONT} font-size="28" font-weight="800" fill="url(#shine)">{val:,}</text>
  <text x="{x+16}" y="{y+58}" {FONT} font-size="12" fill="#787c99" letter-spacing="1">{escape(label.upper())}</text></g>''')

bars = [f'<text x="640" y="58" {FONT} font-size="12" fill="#787c99" letter-spacing="2">TOP LANGUAGES</text>']
for i, (name, (size, color)) in enumerate(top):
    pct = 100 * size / total
    y = 80 + i * 32
    w = 220 * pct / 100
    bars.append(f'''<text x="640" y="{y+12}" {FONT} font-size="13" fill="#c0caf5">{escape(name)}</text>
  <text x="960" y="{y+12}" text-anchor="end" {FONT} font-size="12" fill="#787c99">{pct:.0f}%</text>
  <rect x="730" y="{y+3}" width="180" height="8" rx="4" fill="#1f2235"/>
  <rect x="730" y="{y+3}" width="{180*pct/100:.1f}" height="8" rx="4" fill="{color}"><animate attributeName="width" values="0;0;{180*pct/100:.1f}" keyTimes="0;{(0.3+0.15*i)/(1.5+0.15*i):.4f};1" dur="{1.5+0.15*i:.2f}s" begin="0s" fill="freeze"/></rect>''')

open("dist/stats.svg", "w").write(f'''<svg width="100%" viewBox="0 0 1000 240" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="shine" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#7aa2f7"/><stop offset="50%" stop-color="#bb9af7"/><stop offset="100%" stop-color="#7dcfff"/>
      <animate attributeName="x1" values="-100%;100%" dur="4s" repeatCount="indefinite"/>
      <animate attributeName="x2" values="0%;200%" dur="4s" repeatCount="indefinite"/>
    </linearGradient>
  </defs>
  <rect x="1.5" y="1.5" width="997" height="237" rx="16" fill="#0f1019" stroke="url(#shine)" stroke-width="2"/>
  <path d="M610 30 V210" stroke="#24283b"/>
  {chr(10).join(parts)}
  {chr(10).join(bars)}
</svg>''')

# ---------------- now building ----------------
now = json.load(open("now.json"))
msg, repo, ago = "nothing yet — check back soon", "", ""
events = gh(f"https://api.github.com/users/{LOGIN}/events/public?per_page=100")
pushes = [e for e in events if e["type"] == "PushEvent" and e["payload"].get("head")]
# prefer real project work over edits to this profile repo
pushes = [e for e in pushes if e["repo"]["name"].lower() != f"{LOGIN}/{LOGIN}".lower()] or pushes
for ev in pushes[:1]:
    try:
        msg = gh(f"https://api.github.com/repos/{ev['repo']['name']}/commits/{ev['payload']['head']}")["commit"]["message"].split("\n")[0]
    except Exception:
        continue
    repo = ev["repo"]["name"].split("/")[-1]
    dt = datetime.datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))
    h = int((datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() // 3600)
    ago = "just now" if h < 1 else f"{h}h ago" if h < 48 else f"{h//24}d ago"
msg = (msg[:64] + "…") if len(msg) > 65 else msg
pct = max(0, min(100, int(now.get("progress", 0))))
open("dist/now.svg", "w").write(f'''<svg width="100%" viewBox="0 0 1000 120" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="shine" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#7aa2f7"/><stop offset="50%" stop-color="#bb9af7"/><stop offset="100%" stop-color="#7dcfff"/>
      <animate attributeName="x1" values="-100%;100%" dur="4s" repeatCount="indefinite"/>
      <animate attributeName="x2" values="0%;200%" dur="4s" repeatCount="indefinite"/>
    </linearGradient>
  </defs>
  <rect x="1.5" y="1.5" width="997" height="117" rx="16" fill="#0f1019" stroke="url(#shine)" stroke-width="2"/>
  <circle cx="36" cy="38" r="5" fill="#9ece6a"><animate attributeName="opacity" values="1;0.2;1" dur="1.6s" repeatCount="indefinite"/></circle>
  <text x="52" y="43" {FONT} font-size="12" fill="#9ece6a" letter-spacing="3" font-weight="700">NOW BUILDING</text>
  <text x="180" y="44" {FONT} font-size="20" font-weight="700" fill="#c0caf5">{escape(now["project"])}</text>
  <text x="180" y="66" {FONT} font-size="13" fill="#787c99">{escape(now.get("note", ""))}</text>
  <rect x="640" y="32" width="280" height="10" rx="5" fill="#1f2235"/>
  <rect x="640" y="32" width="{2.8*pct:.0f}" height="10" rx="5" fill="url(#shine)"><animate attributeName="width" values="0;0;{2.8*pct:.0f}" keyTimes="0;0.18;1" dur="1.7s" begin="0s" fill="freeze"/></rect>
  <text x="960" y="42" text-anchor="end" {FONT} font-size="14" font-weight="700" fill="#7dcfff">{pct}%</text>
  <path d="M36 82 H964" stroke="#1f2235"/>
  <text x="36" y="104" {FONT} font-size="13" fill="#787c99">⚡ latest commit</text>
  <text x="150" y="104" {FONT} font-size="13" fill="#c0caf5">“{escape(msg)}”</text>
  <text x="964" y="104" text-anchor="end" {FONT} font-size="13" fill="#787c99">{escape(repo)} · {ago}</text>
</svg>''')
print("built dist/stats.svg and dist/now.svg")
