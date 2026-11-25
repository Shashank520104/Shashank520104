#!/usr/bin/env python3
"""Generate an animated dark-cyber Language Radar & GitHub Activity SVG card."""

import argparse
import datetime
import json
import math
import os
import urllib.request

COLOR_PALETTE = [
    "#ff4d2e",  # Coral Red
    "#a259ff",  # Electric Purple
    "#4d8dff",  # Cyber Blue
    "#ff5dc8",  # Neon Magenta
    "#e6ff2e",  # Acid Lime
]

LANG_COLORS = {
    "TypeScript": "#4d8dff",
    "JavaScript": "#e6ff2e",
    "Python": "#a259ff",
    "HTML": "#ff4d2e",
    "CSS": "#ff5dc8",
    "EJS": "#00f5c4",
    "C++": "#00b4d8",
    "Java": "#ff9f1c",
    "Jupyter Notebook": "#ff6b6b",
}


def fetch_github_stats(username: str, token: str) -> dict:
    """Fetch live repository, language, commit, PR, and star stats via GitHub GraphQL API."""
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
          totalCount
          nodes {
            name
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                }
              }
            }
          }
        }
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
          totalPullRequestContributions
        }
        pullRequests {
          totalCount
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Shashank520104-Radar-Bot",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "errors" in data and not data.get("data"):
        raise RuntimeError(f"GraphQL error: {data['errors']}")

    user = data["data"]["user"]
    repos = user["repositories"]["nodes"]
    total_repos = user["repositories"]["totalCount"]
    total_stars = sum(r.get("stargazerCount", 0) for r in repos)

    lang_sizes = {}
    for repo in repos:
        for edge in repo.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            lang_sizes[name] = lang_sizes.get(name, 0) + edge["size"]

    total_bytes = sum(lang_sizes.values()) or 1
    sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)

    # Keep top 5 languages (merge tiny rest if needed, or take top 5)
    top_langs = []
    for idx, (name, size) in enumerate(sorted_langs[:5]):
        pct = (size / total_bytes) * 100.0
        color = LANG_COLORS.get(name, COLOR_PALETTE[idx % len(COLOR_PALETTE)])
        top_langs.append({"name": name, "pct": pct, "color": color})

    contrib = user["contributionsCollection"]
    commits_last_year = contrib["totalCommitContributions"] + contrib.get("restrictedContributionsCount", 0)
    prs = max(user["pullRequests"]["totalCount"], contrib["totalPullRequestContributions"])

    return {
        "languages": top_langs,
        "repos": total_repos,
        "commits": commits_last_year,
        "prs": prs,
        "stars": total_stars,
        "updated": datetime.date.today().isoformat(),
    }


def get_seed_stats() -> dict:
    """Fallback snapshot based on observed public profile data until GitHub Action refreshes."""
    return {
        "languages": [
            {"name": "TypeScript", "pct": 38.0, "color": "#ff4d2e"},
            {"name": "JavaScript", "pct": 31.0, "color": "#a259ff"},
            {"name": "Python", "pct": 14.0, "color": "#4d8dff"},
            {"name": "HTML", "pct": 11.0, "color": "#ff5dc8"},
            {"name": "EJS", "pct": 6.0, "color": "#e6ff2e"},
        ],
        "repos": 18,
        "commits": 208,
        "prs": 2,
        "stars": 6,
        "updated": datetime.date.today().isoformat(),
    }


def fmt_pct(pct: float) -> str:
    if pct >= 10:
        return f"{pct:.0f}%"
    return f"{pct:.1f}%"


def build_svg(stats: dict) -> str:
    langs = stats["languages"]
    if len(langs) < 4:
        while len(langs) < 4:
            langs.append({"name": "Other", "pct": 1.0, "color": "#e6ff2e"})

    # Radar geometry
    cx, cy = 172.0, 185.0
    max_r = 80.0
    n = len(langs)
    angles = [(-math.pi / 2.0) + (2.0 * math.pi * i / n) for i in range(n)]

    # Concentric grid polygons (4 rings)
    grid_polys = []
    for ring in (0.25, 0.50, 0.75, 1.0):
        r = max_r * ring
        pts = " ".join(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}" for a in angles)
        grid_polys.append(
            f'<polygon points="{pts}" fill="none" stroke="#ffffff" stroke-opacity="0.2" stroke-width="1"/>'
        )

    # Axis lines
    axis_lines = []
    for a in angles:
        x2 = cx + max_r * math.cos(a)
        y2 = cy + max_r * math.sin(a)
        axis_lines.append(
            f'<line x1="{cx:.0f}" y1="{cy:.0f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#ffffff" stroke-opacity="0.2" stroke-width="1"/>'
        )

    # Square-root scale relative to top language
    max_pct = max(l["pct"] for l in langs) or 1.0
    data_pts = []
    data_pts_inner = []
    vertex_dots = []
    axis_labels = []

    for i, lang in enumerate(langs):
        a = angles[i]
        norm = math.sqrt(max(lang["pct"], 0.5) / max_pct)
        r = max(14.0, max_r * norm)
        r_in = max(10.0, r * 0.90)
        px = cx + r * math.cos(a)
        py = cy + r * math.sin(a)
        ix = cx + r_in * math.cos(a)
        iy = cy + r_in * math.sin(a)
        data_pts.append(f"{px:.1f},{py:.1f}")
        data_pts_inner.append(f"{ix:.1f},{iy:.1f}")

        delay = i * 0.35
        vertex_dots.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="#00f5c4">'
            f'<animate attributeName="r" values="3;5.2;3" dur="2.4s" begin="{delay:.2f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.75;1;0.75" dur="2.4s" begin="{delay:.2f}s" repeatCount="indefinite"/>'
            f'</circle>'
        )

        # Label positioning
        lx = cx + (max_r + 12.0) * math.cos(a)
        ly = cy + (max_r + 12.0) * math.sin(a)
        cos_a = math.cos(a)
        sin_a = math.sin(a)
        if abs(cos_a) < 0.25:
            anchor = "middle"
        elif cos_a > 0:
            anchor = "start"
        else:
            anchor = "end"
        if sin_a < -0.5:
            ly += 2.0
        elif sin_a > 0.5:
            ly += 10.0
        else:
            ly += 4.0

        axis_labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif" '
            f'font-size="11" fill="#ffffff" font-weight="400">{lang["name"]}</text>'
        )

    pts_str = " ".join(data_pts)
    pts_in_str = " ".join(data_pts_inner)

    # Radar sweep sector (subtle rotating cyber radar beam)
    sweep_x = cx + max_r * math.cos(-math.pi / 2)
    sweep_y = cy + max_r * math.sin(-math.pi / 2)
    sweep_x2 = cx + max_r * math.cos(-math.pi / 2 + 0.55)
    sweep_y2 = cy + max_r * math.sin(-math.pi / 2 + 0.55)

    # Stacked top language bar (x=363..652 -> width=289)
    bar_x = 363.0
    total_bar_w = 289.0
    stacked_rects = []
    cur_x = bar_x
    pct_sum = sum(l["pct"] for l in langs) or 100.0
    for i, lang in enumerate(langs):
        w = (lang["pct"] / pct_sum) * total_bar_w
        if i == len(langs) - 1:
            w = (bar_x + total_bar_w) - cur_x
        stacked_rects.append(
            f'<rect x="{cur_x:.1f}" y="56" width="{max(w, 0):.1f}" height="8" fill="{lang["color"]}"/>'
        )
        cur_x += w

    # Language rows
    lang_rows = []
    start_y = 84.0
    row_step = 42.0
    for i, lang in enumerate(langs[:5]):
        ry = start_y + i * row_step
        bar_w = max(4.0, (lang["pct"] / 100.0) * total_bar_w * (100.0 / max(max_pct, 45.0)))
        bar_w = min(total_bar_w, max(6.0, (lang["pct"] / max_pct) * total_bar_w))
        shimmer_delay = i * 0.45
        lang_rows.append(
            f'''<g>
<circle cx="369" cy="{ry + 10:.1f}" r="5" fill="{lang['color']}"/>
<text x="382" y="{ry + 14:.1f}" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="13" fill="#ffffff" font-weight="500">{lang['name']}</text>
<text x="652" y="{ry + 14:.1f}" text-anchor="end" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="13" fill="#00f5c4" font-weight="500">{fmt_pct(lang['pct'])}</text>
<rect x="363" y="{ry + 24:.1f}" width="289" height="4" rx="2" fill="#1f1f26"/>
<rect x="363" y="{ry + 24:.1f}" width="{bar_w:.1f}" height="4" rx="2" fill="{lang['color']}"/>
<rect x="363" y="{ry + 24:.1f}" width="36" height="4" rx="2" fill="#ffffff" fill-opacity="0.55" clip-path="url(#barClip{i})">
  <animate attributeName="x" values="{363 - 40};{363 + bar_w + 10}" dur="2.8s" begin="{shimmer_delay:.2f}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;0.75;0" dur="2.8s" begin="{shimmer_delay:.2f}s" repeatCount="indefinite"/>
</rect>
</g>'''
        )

    bar_clips = "\n".join(
        f'<clipPath id="barClip{i}"><rect x="363" y="{start_y + i * row_step + 24:.1f}" width="{min(total_bar_w, max(6.0, (lang["pct"] / max_pct) * total_bar_w)):.1f}" height="4" rx="2"/></clipPath>'
        for i, lang in enumerate(langs[:5])
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 412" width="680" height="412" role="img" aria-label="Language Radar and GitHub Activity for Shashank Kumar">
<defs>
  <clipPath id="cl"><rect x="363" y="56" width="289" height="8" rx="4"/></clipPath>
  <linearGradient id="sweepGrad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#00f5c4" stop-opacity="0.28"/>
    <stop offset="100%" stop-color="#00f5c4" stop-opacity="0.0"/>
  </linearGradient>
  <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="2.5" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
  {bar_clips}
</defs>

<rect width="680" height="412" rx="8" fill="#030305"/>
<rect x="10" y="10" width="325" height="300" rx="6" fill="#0b0b0f" stroke="#ffffff" stroke-width="1.5"/>
<rect x="345" y="10" width="325" height="300" rx="6" fill="#0b0b0f" stroke="#ffffff" stroke-width="1.5"/>
<rect x="10" y="322" width="660" height="80" rx="6" fill="#0b0b0f" stroke="#ffffff" stroke-width="1.5"/>

<!-- Left Card: Language Radar -->
<text x="28" y="38" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="14" fill="#00f5c4" font-weight="600">Language Radar</text>
<circle cx="314" cy="33" r="3.5" fill="#00f5c4">
  <animate attributeName="opacity" values="0.3;1;0.3" dur="2s" repeatCount="indefinite"/>
</circle>

{"".join(grid_polys)}
{"".join(axis_lines)}

<!-- Rotating cyber radar sweep -->
<g>
  <path d="M {cx:.0f},{cy:.0f} L {sweep_x:.1f},{sweep_y:.1f} A {max_r:.0f},{max_r:.0f} 0 0,1 {sweep_x2:.1f},{sweep_y2:.1f} Z" fill="url(#sweepGrad)"/>
  <line x1="{cx:.0f}" y1="{cy:.0f}" x2="{sweep_x:.1f}" y2="{sweep_y:.1f}" stroke="#00f5c4" stroke-opacity="0.55" stroke-width="1.2"/>
  <animateTransform attributeName="transform" type="rotate" from="0 {cx:.0f} {cy:.0f}" to="360 {cx:.0f} {cy:.0f}" dur="7s" repeatCount="indefinite"/>
</g>

<!-- Pulsing radar polygon -->
<polygon points="{pts_str}" fill="#00f5c4" fill-opacity="0.25" stroke="#00f5c4" stroke-width="2" filter="url(#glow)">
  <animate attributeName="points" values="{pts_str};{pts_in_str};{pts_str}" dur="3.6s" repeatCount="indefinite"/>
  <animate attributeName="fill-opacity" values="0.20;0.36;0.20" dur="3.6s" repeatCount="indefinite"/>
</polygon>

{"".join(axis_labels)}
{"".join(vertex_dots)}

<text x="28" y="296" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="10.5" fill="#9ca3af" font-weight="400">Code proportion by language, square-root scale</text>

<!-- Right Card: Top Languages -->
<text x="363" y="38" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="14" fill="#00f5c4" font-weight="600">Top Languages</text>
<g clip-path="url(#cl)">
  {"".join(stacked_rects)}
</g>
{"".join(lang_rows)}
<text x="363" y="298" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="10.5" fill="#9ca3af" font-weight="400">updated {stats['updated']}</text>

<!-- Bottom Card: Activity Metrics -->
<text x="28" y="350" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="11" fill="#d1d5db" font-weight="400">Repositories</text>
<text x="28" y="382" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="22" fill="#00f5c4" font-weight="600">{stats['repos']}</text>
<line x1="176" y1="338" x2="176" y2="386" stroke="#ffffff" stroke-opacity="0.2"/>

<text x="193" y="350" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="11" fill="#d1d5db" font-weight="400">Commits (last year)</text>
<text x="193" y="382" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="22" fill="#00f5c4" font-weight="600">{stats['commits']}</text>
<line x1="341" y1="338" x2="341" y2="386" stroke="#ffffff" stroke-opacity="0.2"/>

<text x="358" y="350" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="11" fill="#d1d5db" font-weight="400">Pull requests</text>
<text x="358" y="382" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="22" fill="#00f5c4" font-weight="600">{stats['prs']}</text>
<line x1="506" y1="338" x2="506" y2="386" stroke="#ffffff" stroke-opacity="0.2"/>

<text x="523" y="350" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="11" fill="#d1d5db" font-weight="400">Stars received</text>
<text x="523" y="382" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="22" fill="#00f5c4" font-weight="600">{stats['stars']}</text>
</svg>
'''
    return svg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=os.environ.get("GITHUB_ACTOR", "Shashank520104"))
    parser.add_argument("--output", default="assets/radar.svg")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token and not args.seed:
        stats = fetch_github_stats(args.username, token)
    else:
        stats = get_seed_stats()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(build_svg(stats))
    print(f"Generated {args.output} for {args.username}: {stats['repos']} repos, {stats['commits']} commits")


if __name__ == "__main__":
    main()
