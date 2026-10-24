#!/usr/bin/env python3
"""Generate the SVG assets used by the profile README.

Reads live data through the GitHub CLI (`gh api`), so it needs `gh auth login`
locally or GH_TOKEN in CI. Output goes to ../assets.
"""
import datetime
import html
import base64
import io
import json
import subprocess
import textwrap
from pathlib import Path

USER = "SecreTavin"
OUT = Path(__file__).resolve().parent.parent / "assets"

BG = "#0b1020"
PANEL = "#0f1b2a"
ACCENT = "#2de6a0"
TEXT = "#e6edf3"
SOFT = "#c9d4e0"
MUTED = "#8b98a9"
SANS = "'Segoe UI', -apple-system, Helvetica, Arial, sans-serif"
MONO = "SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"

LANG_COLORS = {
    "TypeScript": "#3178c6", "Python": "#3572A5", "C#": "#178600",
    "PLpgSQL": "#336790", "HTML": "#e34c26", "JavaScript": "#f1e05a",
    "Astro": "#ff5a03", "CSS": "#563d7c", "Swift": "#F05138",
    "Shell": "#89e051", "Dockerfile": "#384d54", "Batchfile": "#C1F12E",
}

FEATURED = [
    ("octavio-os", "octavio-os",
     "Portfólio pessoal em Next.js e TypeScript.",
     ["Next.js"]),
    ("metal-rush", "metal-rush",
     "Run-and-gun 2D estilo Metal Slug: o último dev contra as IAs. Publicado no Cloudflare.",
     ["Phaser 3", "Vite"]),
    ("analise-preditiva-acidentes-transito-V2", "analise-preditiva-acidentes-transito-V2",
     "Pipeline de ML para prever a gravidade de acidentes de trânsito. Random Forest com 0.98 AUC-ROC.",
     ["Random Forest", "SVM"]),
    ("Sistema-de-monitoramento-de-filtros-de-manga-industriais",
     "Sistema-de-monitoramento-de-filtros-de-manga-industriais",
     "Monitoramento em tempo real da perda de pressão (deltaP) de filtros de manga industriais.",
     ["Real-time"]),
    ("Drone-DTI", "Drone-DTI",
     "Simulador fullstack de logística de frotas de drones em tempo real, com SPA em Vanilla JS.",
     ["Node.js", "Express"]),
    ("System-Pulse", "System-Pulse",
     "Utilitário nativo para macOS que mostra o uso de CPU em tempo real na barra de menus.",
     ["macOS"]),
]


def gh(*args):
    return json.loads(subprocess.check_output(["gh", "api", *args], text=True))


def esc(s):
    return html.escape(str(s), quote=True)


def shade(hex_color, k):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
PORTRAIT_PX = 88


def portrait(avatar_url):
    """Ordered-dither (4 levels per channel) version of the profile photo, as base64 PNG."""
    cache = OUT / "portrait.png"
    try:
        from PIL import Image, ImageEnhance
        raw = subprocess.check_output(["curl", "-fsSL", "--max-time", "30", avatar_url + ("&" if "?" in avatar_url else "?") + "s=460"])
        im = Image.open(io.BytesIO(raw)).convert("RGB").resize((PORTRAIT_PX, PORTRAIT_PX), Image.LANCZOS)
        im = ImageEnhance.Brightness(ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(1.1)).enhance(1.25)).enhance(1.1)
        out = Image.new("RGB", im.size)
        src, dst, step = im.load(), out.load(), 255 / 3
        for y in range(PORTRAIT_PX):
            for x in range(PORTRAIT_PX):
                t = (BAYER[y % 4][x % 4] + 0.5) / 16 - 0.5
                dst[x, y] = tuple(int(max(0, min(3, int(c / step + t + 0.5))) * step) for c in src[x, y])
        OUT.mkdir(parents=True, exist_ok=True)
        out.save(cache, optimize=True)
    except Exception as exc:
        print("portrait: using cached image (", exc, ")")
    return base64.b64encode(cache.read_bytes()).decode() if cache.exists() else None


def fetch():
    profile = gh(f"users/{USER}")
    repos = [r for r in gh(f"users/{USER}/repos?per_page=100") if not r["fork"]]
    langs = {}
    for r in repos:
        for k, v in gh(f"repos/{USER}/{r['name']}/languages").items():
            langs[k] = langs.get(k, 0) + v
    query = ('{ user(login:"%s"){ contributionsCollection{ contributionCalendar{ '
             'totalContributions weeks{ contributionDays{ date contributionCount } } } } } }' % USER)
    cal = gh("graphql", "-f", f"query={query}")["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return {
        "name": profile["name"] or USER,
        "portrait": portrait(profile["avatar_url"]),
        "public_repos": profile["public_repos"],
        "followers": profile["followers"],
        "stars": sum(r["stargazers_count"] for r in repos),
        "repos": {r["name"]: r for r in repos},
        "langs": sorted(((k, v) for k, v in langs.items() if v > 0), key=lambda kv: -kv[1]),
        "calendar": cal,
    }


def panel(w, h, extra_defs=""):
    return f"""<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG}"/><stop offset="1" stop-color="#0c2230"/></linearGradient>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="{ACCENT}" fill-opacity=".12"/></pattern>
  <clipPath id="clip"><rect width="{w}" height="{h}" rx="18"/></clipPath>
  {extra_defs}
</defs>
<rect width="{w}" height="{h}" rx="18" fill="url(#bg)"/>
<rect width="{w}" height="{h}" rx="18" fill="url(#dots)"/>
<rect class="edge" x="1" y="1" width="{w - 2}" height="{h - 2}" rx="17" fill="none" stroke="{ACCENT}" stroke-width="1.5"/>"""


def svg(w, h, body, css="", pad=0):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="{-pad} {-pad} {w + 2 * pad} {h + 2 * pad}" '
            f'width="{w + 2 * pad}" height="{h + 2 * pad}" '
            f'font-family="{SANS}">\n<style>\n'
            f'.edge{{stroke-opacity:.45;animation:edge 3s ease-in-out infinite}}\n'
            f'@keyframes edge{{0%,100%{{stroke-opacity:.3}}50%{{stroke-opacity:.8}}}}\n{css}</style>\n{body}\n</svg>\n')


def header(d):
    w, h = 1000, 280
    top = [k for k, _ in d["langs"]][:4]
    pills, x = "", 48
    for name in top:
        pw = len(name) * 7.4 + 42
        color = LANG_COLORS.get(name, MUTED)
        pills += (f'<g transform="translate({x:.0f},192)"><rect width="{pw:.0f}" height="30" rx="15" fill="#10202e" '
                  f'stroke="{ACCENT}" stroke-opacity=".35"/><circle cx="16" cy="15" r="4.5" fill="{color}"/>'
                  f'<text x="28" y="20" font-size="13" fill="{TEXT}">{esc(name)}</text></g>')
        x += pw + 10
    tagline = "> Fullstack Developer · Software Engineer"
    tw = len(tagline) * 10.2
    tiles = ""
    items = [(d["public_repos"], "Repositories"), (d["stars"], "Stars"),
             (d["calendar"]["totalContributions"], "Contributions"), (d["followers"], "Followers")]
    for i, (num, label) in enumerate(items):
        fit = 'textLength="84" lengthAdjust="spacingAndGlyphs"' if len(label) > 11 else ""
        tx, ty = 516 + (i % 2) * 124, 62 + (i // 2) * 92
        tiles += (f'<g transform="translate({tx},{ty})"><rect width="116" height="78" rx="12" fill="{PANEL}" '
                  f'stroke="{ACCENT}" stroke-opacity=".28"/><text x="16" y="45" font-size="32" font-weight="700" '
                  f'fill="{ACCENT}">{num}</text><text x="16" y="65" font-size="10" letter-spacing=".4" {fit} '
                  f'fill="{MUTED}">{label.upper()}</text></g>')
    frame = ""
    if d["portrait"]:
        frame = (f'<g transform="translate(776,52)"><rect x="-7" y="-7" width="190" height="190" rx="17" fill="#0a1320" '
                 f'stroke="{ACCENT}" stroke-opacity=".5" class="edge"/>'
                 f'<image width="176" height="176" clip-path="url(#pclip)" style="image-rendering:pixelated" '
                 f'xlink:href="data:image/png;base64,{d["portrait"]}"/>'
                 f'<rect class="pscan" width="176" height="3" fill="{ACCENT}" fill-opacity=".35" clip-path="url(#pclip)"/></g>')
    body = panel(w, h, f'<clipPath id="pclip"><rect width="176" height="176" rx="12"/></clipPath>'
                       f'<linearGradient id="scan" x1="0" x2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/>'
                       f'<stop offset=".5" stop-color="{ACCENT}" stop-opacity=".09"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>')
    body += f"""
<g clip-path="url(#clip)"><rect class="scan" x="0" y="0" width="160" height="{h}" fill="url(#scan)"/></g>
<circle class="pulse" cx="54" cy="56" r="5" fill="{ACCENT}"/>
<text x="68" y="61" font-family="{MONO}" font-size="15" fill="{ACCENT}">@{USER} · session: active</text>
<text x="48" y="124" font-size="48" font-weight="700" fill="{TEXT}">{esc(d['name'])}</text>
<text x="48" y="166" font-family="{MONO}" font-size="17" fill="{SOFT}" textLength="{tw:.0f}" lengthAdjust="spacing">{esc(tagline)}</text>
<rect class="cursor" x="{48 + tw + 6:.0f}" y="151" width="10" height="20" fill="{ACCENT}"/>
{pills}
{frame}
<text x="48" y="252" font-family="{MONO}" font-size="13" fill="{MUTED}">→ octavio-os2-0.vercel.app  ·  Belo Horizonte, MG, BR</text>
{tiles}"""
    css = (".pulse{animation:pulse 2.2s ease-in-out infinite}\n"
           "@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}\n"
           ".cursor{animation:blink 1s steps(1) infinite}\n"
           "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}\n"
           ".scan{animation:sweep 7s linear infinite}\n"
           ".pscan{animation:pscan 4.5s ease-in-out infinite}\n"
           "@keyframes pscan{0%{transform:translateY(-4px)}100%{transform:translateY(178px)}}\n"
           "@keyframes sweep{from{transform:translateX(-200px)}to{transform:translateX(1100px)}}\n")
    return svg(w, h, body, css)


def city(d):
    w, h = 1000, 430
    weeks = d["calendar"]["weeks"]
    days = [x for wk in weeks for x in wk["contributionDays"]]
    counts = [x["contributionCount"] for x in days]
    peak = max(counts)
    active = sum(1 for c in counts if c)
    busiest = max(days, key=lambda x: x["contributionCount"])
    busiest_date = datetime.date.fromisoformat(busiest["date"]).strftime("%b %d")
    nz = sorted(c for c in counts if c)
    q = [nz[len(nz) // 4], nz[len(nz) // 2], nz[3 * len(nz) // 4]]
    palette = ["#1b6b57", "#22a67a", "#2de6a0", "#7dffd0"]

    def level(c):
        return 0 if c <= q[0] else 1 if c <= q[1] else 2 if c <= q[2] else 3

    ax, ay, g = 11.4, 4.7, 0.88
    cells = []
    for wi, wk in enumerate(weeks):
        for di, day in enumerate(wk["contributionDays"]):
            c = day["contributionCount"]
            ht = 1.6 if c == 0 else 4 + 125 * (c / peak) ** 0.75
            cells.append((wi, di, c, ht))
    max_x = max((wi - di) * ax for wi, di, _, _ in cells) + ax
    max_y = max((wi + di) * ay + ay for wi, di, _, _ in cells)
    ox, oy = 962 - max_x, (h - 30) - max_y

    cols = ""
    for wi in range(len(weeks)):
        polys = ""
        for wj, di, c, ht in sorted((x for x in cells if x[0] == wi), key=lambda x: x[1]):
            cx, cy = ox + (wi - di) * ax, oy + (wi + di) * ay
            top_c = "#12303a" if c == 0 else palette[level(c)]
            gx, gy = ax * g, ay * g
            T, R, B, L = (cx, cy - ht - gy), (cx + gx, cy - ht), (cx, cy - ht + gy), (cx - gx, cy - ht)
            B0, L0, R0 = (cx, cy + gy), (cx - gx, cy), (cx + gx, cy)
            f = lambda pts: " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
            polys += (f'<polygon points="{f([L, B, B0, L0])}" fill="{shade(top_c, .72)}"/>'
                      f'<polygon points="{f([B, R, R0, B0])}" fill="{shade(top_c, .5)}"/>'
                      f'<polygon points="{f([T, R, B, L])}" fill="{top_c}"/>')
        cols += f'<g class="col" style="animation-delay:{wi * 22}ms">{polys}</g>\n'

    legend = "".join(f'<rect x="{92 + i * 16}" y="{h - 42}" width="11" height="11" rx="2" fill="{c}"/>'
                     for i, c in enumerate(["#12303a"] + palette))
    body = panel(w, h) + f"""
<text x="48" y="62" font-size="26" font-weight="700" fill="{TEXT}">The city I built this year</text>
<text x="952" y="58" text-anchor="end" font-family="{MONO}" font-size="14" fill="{ACCENT}">&gt; github-profile-3d_</text>
<text x="48" y="116" font-family="{MONO}" font-size="12" letter-spacing="1.4" fill="{ACCENT}">CONTRIBUTIONS</text>
<text x="48" y="166" font-size="54" font-weight="700" fill="{TEXT}">{d['calendar']['totalContributions']}</text>
<text x="48" y="194" font-size="15" fill="{MUTED}">{active} active days</text>
<text x="48" y="216" font-size="15" fill="{MUTED}">Busiest day: {peak} · {busiest_date}</text>
{cols}
<text x="48" y="{h - 33}" font-family="{MONO}" font-size="11" fill="{MUTED}">Less</text>{legend}
<text x="176" y="{h - 33}" font-family="{MONO}" font-size="11" fill="{MUTED}">More</text>"""
    css = (".col{animation:rise .7s ease-out both}\n"
           "@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}\n")
    return svg(w, h, body, css)


def languages(d):
    w, h = 1000, 268
    total = sum(v for _, v in d["langs"])
    top = d["langs"][:6]
    items = ""
    for i, (name, val) in enumerate(top):
        pct = 100 * val / total
        x, y = 48 + (i % 2) * 472, 92 + (i // 2) * 52
        color = LANG_COLORS.get(name, MUTED)
        items += (f'<circle cx="{x + 6}" cy="{y - 5}" r="5" fill="{color}"/>'
                  f'<text x="{x + 20}" y="{y}" font-size="15" fill="{TEXT}">{esc(name)}</text>'
                  f'<text x="{x + 432}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="14" fill="{MUTED}">{pct:.1f}%</text>'
                  f'<rect x="{x}" y="{y + 12}" width="432" height="8" rx="4" fill="#16283a"/>'
                  f'<rect class="bar" style="animation-delay:{i * 120}ms" x="{x}" y="{y + 12}" width="{max(6, 432 * pct / 100):.1f}" height="8" rx="4" fill="{color}"/>')
    body = panel(w, h) + f"""
<text x="48" y="58" font-size="24" font-weight="700" fill="{TEXT}">Language Stack</text>
<text x="952" y="56" text-anchor="end" font-family="{MONO}" font-size="13" fill="{ACCENT}">&gt; stack.scan_ · bytes in public repos</text>
{items}"""
    css = (".bar{transform-box:fill-box;transform-origin:left center;animation:grow 1s ease-out both}\n"
           "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}\n")
    return svg(w, h, body, css)


def card(repo, label, desc, tags, live):
    w, h = 480, 168
    lang = live.get("language")
    lines = textwrap.wrap(desc, 60)[:3]
    shown = label if len(label) <= 34 else label[:33] + "…"
    pills, x = "", 24
    names = ([lang] if lang else []) + [t for t in tags if t != lang]
    for i, name in enumerate(names):
        pw = len(name) * 6.8 + (40 if i == 0 and lang else 26)
        if x + pw > 456:
            break
        dot = (f'<circle cx="15" cy="12" r="4" fill="{LANG_COLORS.get(lang, MUTED)}"/>' if i == 0 and lang else "")
        tx = 25 if dot else 13
        pills += (f'<g transform="translate({x:.0f},108)"><rect width="{pw:.0f}" height="24" rx="12" fill="#10202e" '
                  f'stroke="{ACCENT}" stroke-opacity=".3"/>{dot}<text x="{tx}" y="16" font-size="11.5" fill="{SOFT}">{esc(name)}</text></g>')
        x += pw + 8
    pushed = datetime.datetime.fromisoformat(live["pushed_at"].replace("Z", "+00:00")).strftime("%d %b %Y")
    desc_svg = "".join(f'<text x="24" y="{62 + i * 19}" font-size="13" fill="{SOFT}">{esc(l)}</text>' for i, l in enumerate(lines))
    body = f"""<rect width="{w}" height="{h}" rx="14" fill="{PANEL}"/>
<rect class="edge" x="1" y="1" width="{w - 2}" height="{h - 2}" rx="13" fill="none" stroke="{ACCENT}" stroke-width="1.2"/>
<path d="M24 22h6l2 2.5h8a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1-1.5 1.5H24A1.5 1.5 0 0 1 22.5 35V23.5A1.5 1.5 0 0 1 24 22z" transform="translate(-4,-6)" fill="none" stroke="{ACCENT}" stroke-width="1.5"/>
<text x="46" y="31" font-family="{MONO}" font-size="15" font-weight="700" fill="{ACCENT}">{esc(shown)}</text>
<text x="456" y="31" text-anchor="end" font-family="{MONO}" font-size="13" fill="{MUTED}">★ {live['stargazers_count']}</text>
{desc_svg}{pills}
<text x="456" y="152" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">last push {pushed}</text>"""
    return svg(w, h, body, pad=6)


def main():
    d = fetch()
    (OUT / "projects").mkdir(parents=True, exist_ok=True)
    (OUT / "header.svg").write_text(header(d), encoding="utf-8")
    (OUT / "city.svg").write_text(city(d), encoding="utf-8")
    (OUT / "languages.svg").write_text(languages(d), encoding="utf-8")
    for repo, label, desc, tags in FEATURED:
        (OUT / "projects" / f"{repo}.svg").write_text(card(repo, label, desc, tags, d["repos"][repo]), encoding="utf-8")
    print("assets written to", OUT)


if __name__ == "__main__":
    main()
