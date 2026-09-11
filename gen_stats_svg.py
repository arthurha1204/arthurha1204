# -*- coding: utf-8 -*-
import json, datetime, html

FONT = "'JetBrains Mono','Fira Code',ui-monospace,'SFMono-Regular',Consolas,monospace"

BG = "#0d1218"
BG_BAR = "#0a0d11"
BORDER = "#1f5c33"
BORDER_DIM = "#16351f"
GREEN = "#00ff5f"
GREEN_DIM = "#3fae62"
GREEN_MUTE = "#2b6b40"
TEXT = "#c8f7d4"
TEXT_DIM = "#6f9c7d"
WHITE = "#eaffef"
AMBER = "#ffcf4a"

def esc(s):
    return html.escape(s, quote=True)

def term_chrome(w, title):
    return f'''
  <rect x="0.5" y="0.5" width="{w-1}" height="27" rx="9" fill="{BG_BAR}"/>
  <rect x="0.5" y="18" width="{w-1}" height="10" fill="{BG_BAR}"/>
  <circle cx="15" cy="14" r="5" fill="#ff5f56"/>
  <circle cx="33" cy="14" r="5" fill="#ffbd2e"/>
  <circle cx="51" cy="14" r="5" fill="#27c93f"/>
  <text x="70" y="18" font-family="{FONT}" font-size="11" fill="{TEXT_DIM}">{esc(title)}</text>
  <line x1="0" y1="28" x2="{w}" y2="28" stroke="{BORDER_DIM}" stroke-width="1"/>
'''

# ---------------------------------------------------------------
# 1) STATS CARD
# ---------------------------------------------------------------
def build_stats_card(data):
    u = data["user"]
    repos = u["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    followers = u["followers"]["totalCount"]
    following = u["following"]["totalCount"]
    cc = u["contributionsCollection"]
    commits_12m = cc["totalCommitContributions"] + cc.get("restrictedContributionsCount", 0)
    repos_contrib = cc["totalRepositoriesWithContributedCommits"]

    # language aggregation
    totals = {}
    colors = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            totals[name] = totals.get(name, 0) + e["size"]
            colors[name] = e["node"]["color"] or GREEN_DIM
    grand = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    top = ranked[:5]
    rest = ranked[5:]
    rest_sum = sum(v for _, v in rest)

    w, h = 495, 300
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    parts.append(f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="{BG}" stroke="{BORDER}"/>')
    parts.append(term_chrome(w, "gh_stats.sh"))

    y = 50
    parts.append(f'<text x="20" y="{y}" font-family="{FONT}" font-size="12" fill="{GREEN_DIM}">arthur@github:~$ <tspan fill="{WHITE}">gh stats --user arthurha1204</tspan></text>')

    rows = [
        ("repositorios publicos", str(repos)),
        ("seguidores", f"{followers}  ·  seguindo {following}"),
        ("estrelas recebidas", str(stars)),
        ("contribuicoes (12m)", str(commits_12m)),
        ("repos c/ contribuicao", str(repos_contrib)),
    ]
    ry = y + 26
    for label, value in rows:
        parts.append(f'<text x="24" y="{ry}" font-family="{FONT}" font-size="12" fill="{TEXT_DIM}">&gt; {esc(label)}</text>')
        parts.append(f'<text x="475" y="{ry}" text-anchor="end" font-family="{FONT}" font-size="12" font-weight="700" fill="{GREEN}">{esc(value)}</text>')
        ry += 21

    # separator
    sep_y = ry + 6
    parts.append(f'<line x1="20" y1="{sep_y}" x2="{w-20}" y2="{sep_y}" stroke="{BORDER_DIM}" stroke-dasharray="2,3"/>')

    ly = sep_y + 22
    parts.append(f'<text x="20" y="{ly}" font-family="{FONT}" font-size="12" fill="{GREEN_DIM}">~$ <tspan fill="{WHITE}">cat top_langs.json</tspan></text>')

    # stacked bar
    bar_y = ly + 14
    bar_x = 20
    bar_w = w - 40
    bar_h = 10
    parts.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="{BORDER_DIM}"/>')
    cx = bar_x
    segs = list(top)
    if rest_sum > 0:
        segs = segs + [("outros", rest_sum)]
    for i, (name, size) in enumerate(segs):
        seg_w = bar_w * (size / grand)
        color = colors.get(name, TEXT_DIM) if name != "outros" else BORDER
        rx = 5 if (i == 0 or i == len(segs) - 1) else 0
        parts.append(f'<rect x="{cx:.2f}" y="{bar_y}" width="{max(seg_w,1):.2f}" height="{bar_h}" fill="{color}"/>')
        cx += seg_w
    parts.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="none" stroke="{BG}" stroke-width="1"/>')

    # legend, two columns
    leg_y = bar_y + 28
    col_w = bar_w / 2
    for i, (name, size) in enumerate(top):
        pct = 100 * size / grand
        col = i % 2
        row = i // 2
        lx = bar_x + col * col_w
        yy = leg_y + row * 18
        color = colors.get(name, TEXT_DIM)
        parts.append(f'<circle cx="{lx+4}" cy="{yy-4}" r="4" fill="{color}"/>')
        parts.append(f'<text x="{lx+14}" y="{yy}" font-family="{FONT}" font-size="11" fill="{TEXT}">{esc(name)}</text>')
        parts.append(f'<text x="{lx+col_w-6}" y="{yy}" text-anchor="end" font-family="{FONT}" font-size="11" fill="{TEXT_DIM}">{pct:.1f}%</text>')

    parts.append('</svg>')
    return "\n".join(parts)

# ---------------------------------------------------------------
# 2) CONTRIBUTION HEATMAP
# ---------------------------------------------------------------
MONTHS_PT = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]

def bucket(count, q):
    if count == 0: return 0
    if count <= q[0]: return 1
    if count <= q[1]: return 2
    if count <= q[2]: return 3
    return 4

LEVEL_COLOR = [BORDER_DIM, BORDER, GREEN_MUTE, GREEN_DIM, GREEN]

def build_activity_svg(cal):
    weeks = cal["weeks"]
    all_counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"] > 0)
    if all_counts:
        def pct(p):
            idx = min(len(all_counts)-1, int(len(all_counts)*p))
            return all_counts[idx]
        q = [max(1,pct(0.25)), max(2,pct(0.55)), max(3,pct(0.85))]
    else:
        q = [1,2,3]

    cell = 11
    gap = 3
    left_pad = 34
    top_pad = 34
    n_weeks = len(weeks)
    w = left_pad + n_weeks * (cell + gap) + 16
    h = top_pad + 7 * (cell + gap) + 34
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    parts.append(f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="{BG}" stroke="{BORDER}"/>')
    parts.append(term_chrome(w, "gh_activity.sh"))

    total = cal["totalContributions"]
    parts.append(f'<text x="20" y="50" font-family="{FONT}" font-size="12" fill="{GREEN_DIM}">arthur@github:~$ <tspan fill="{WHITE}">cat activity.log</tspan> <tspan fill="{TEXT_DIM}"># {total} contribuicoes nos ultimos 12 meses</tspan></text>')

    grid_top = 64
    day_labels = {1: "seg", 3: "qua", 5: "sex"}
    for dow, label in day_labels.items():
        yy = grid_top + dow * (cell + gap) + cell - 2
        parts.append(f'<text x="{left_pad-6}" y="{yy}" text-anchor="end" font-family="{FONT}" font-size="9" fill="{TEXT_DIM}">{label}</text>')

    last_month = None
    for wi, wk in enumerate(weeks):
        x = left_pad + wi * (cell + gap)
        first_day = wk["contributionDays"][0]["date"]
        m = int(first_day.split("-")[1])
        if m != last_month:
            parts.append(f'<text x="{x}" y="{grid_top-8}" font-family="{FONT}" font-size="9" fill="{TEXT_DIM}">{MONTHS_PT[m-1]}</text>')
            last_month = m
        for di, day in enumerate(wk["contributionDays"]):
            y = grid_top + di * (cell + gap)
            lvl = bucket(day["contributionCount"], q)
            color = LEVEL_COLOR[lvl]
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{color}">'
                         f'<title>{day["date"]}: {day["contributionCount"]} contrib.</title></rect>')

    # legend
    leg_y = h - 14
    parts.append(f'<text x="{left_pad}" y="{leg_y}" font-family="{FONT}" font-size="9" fill="{TEXT_DIM}">menos</text>')
    lx = left_pad + 42
    for lvl in range(5):
        parts.append(f'<rect x="{lx}" y="{leg_y-9}" width="{cell}" height="{cell}" rx="2" fill="{LEVEL_COLOR[lvl]}"/>')
        lx += cell + gap
    parts.append(f'<text x="{lx+2}" y="{leg_y}" font-family="{FONT}" font-size="9" fill="{TEXT_DIM}">mais</text>')

    parts.append('</svg>')
    return "\n".join(parts)


STATS_QUERY = '''
query($login:String!) {
  user(login:$login) {
    followers { totalCount }
    following { totalCount }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first:6, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalRepositoriesWithContributedCommits
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
'''

def fetch(login):
    import subprocess
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={STATS_QUERY}", "-f", f"login={login}"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)["data"]["user"]


if __name__ == "__main__":
    import sys, os
    login = sys.argv[1] if len(sys.argv) > 1 else "arthurha1204"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    user = fetch(login)

    svg1 = build_stats_card({"user": user})
    svg2 = build_activity_svg(user["contributionsCollection"]["contributionCalendar"])

    p1 = os.path.join(out_dir, "gh-stats.svg")
    p2 = os.path.join(out_dir, "gh-activity.svg")
    open(p1, "w", encoding="utf-8").write(svg1)
    open(p2, "w", encoding="utf-8").write(svg2)
    print("wrote", p1, len(svg1), "bytes")
    print("wrote", p2, len(svg2), "bytes")
