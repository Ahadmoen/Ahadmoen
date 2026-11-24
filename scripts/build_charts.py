"""Build the animated SVG charts shown on the GitHub profile README.

Outputs (in assets/):
  commit-trend.svg     monthly contributions, last 12 months (live data via GitHub GraphQL)
  expertise-radar.svg  core technical expertise radar + bars (static values below)
  pipeline-flow.svg    animated Sources -> Ingest -> Warehouse -> Decisions diagram

Run:  GITHUB_TOKEN=... python scripts/build_charts.py
"""
import datetime as dt
import json
import math
import os
import urllib.request
from pathlib import Path

USER = "Ahadmoen"
OUT = Path(__file__).resolve().parent.parent / "assets"

BG1, BG2 = "#0f2027", "#203a43"
ACCENT = "#36BCF7"
TEXT = "#e6edf3"
MUTED = "#9fb3c8"
GRID = "#2c5364"
FONT = "Segoe UI, Helvetica Neue, Helvetica, Arial, sans-serif"

EXPERTISE = [  # (label, level %)
    ("Python", 96),
    ("PySpark", 94),
    ("SQL / BigQuery", 95),
    ("Dashboards", 98),
    ("Cloud (GCP)", 88),
    ("ML / DL", 92),
    ("n8n / Workflows", 80),
]


def frame(w, h, body, title=None, subtitle=None):
    head = ""
    if title:
        head += f'<text x="32" y="44" class="t">{title}</text>'
    if subtitle:
        head += f'<text x="32" y="68" class="s">{subtitle}</text>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG1}"/><stop offset="1" stop-color="{BG2}"/></linearGradient>
  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".45"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<style>
  text {{ font-family: {FONT}; }}
  .t {{ fill: {TEXT}; font-size: 22px; font-weight: 700; }}
  .s {{ fill: {MUTED}; font-size: 13px; }}
  .l {{ fill: {TEXT}; font-size: 13px; font-weight: 600; }}
  .m {{ fill: {MUTED}; font-size: 11px; }}
  .v {{ fill: {ACCENT}; font-size: 13px; font-weight: 700; }}
  .fade {{ opacity: 0; animation: fade .8s ease forwards; }}
  @keyframes fade {{ to {{ opacity: 1; }} }}
  @keyframes grow {{ from {{ transform: scale(0); }} to {{ transform: scale(1); }} }}
  @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
</style>
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" fill="url(#bg)" stroke="{ACCENT}" stroke-opacity=".35"/>
{head}
{body}
</svg>
"""


# ---------------------------------------------------------------- trend
def fetch_monthly():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    q = '{user(login:"%s"){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}' % USER
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    months = {}
    for w in weeks:
        for d in w["contributionDays"]:
            months[d["date"][:7]] = months.get(d["date"][:7], 0) + d["contributionCount"]
    keys = sorted(months)[-12:]
    return [(k, months[k]) for k in keys]


def trend_svg(series):
    W, H = 900, 345
    x0, x1, y0, y1 = 70, 870, 300, 110
    vmax = max(v for _, v in series) or 1
    step = 10 ** max(0, len(str(vmax)) - 1)
    top = math.ceil(vmax * 1.15 / step) * step
    n = len(series)
    pts = [(x0 + i * (x1 - x0) / (n - 1), y0 - v / top * (y0 - y1)) for i, (_, v) in enumerate(series)]

    grid = ""
    for i in range(5):
        val = top * i / 4
        y = y0 - i / 4 * (y0 - y1)
        grid += f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{GRID}" stroke-dasharray="3 5"/>'
        grid += f'<text x="{x0-12}" y="{y+4:.1f}" text-anchor="end" class="m">{int(val)}</text>'

    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    length = sum(math.dist(pts[i], pts[i + 1]) for i in range(n - 1))
    area = path + f" L{pts[-1][0]:.1f},{y0} L{pts[0][0]:.1f},{y0} Z"

    labels, dots = "", ""
    peak = max(range(n), key=lambda i: series[i][1])
    for i, ((m, v), (x, y)) in enumerate(zip(series, pts)):
        d = 0.25 + i * 0.12
        mon = dt.date(int(m[:4]), int(m[5:]), 1).strftime("%b")
        yr = f"'{m[2:4]}" if (i == 0 or m[5:] == "01") else ""
        labels += f'<text x="{x:.1f}" y="{y0+22}" text-anchor="middle" class="m">{mon}{yr}</text>'
        dots += (
            f'<g class="fade" style="animation-delay:{d:.2f}s">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{BG1}" stroke="{ACCENT}" stroke-width="2.5"/>'
            f'<text x="{x:.1f}" y="{y-12:.1f}" text-anchor="middle" class="v">{v}</text></g>'
        )
    px, py = pts[peak]
    pulse = (
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="none" stroke="{ACCENT}" stroke-width="2">'
        f'<animate attributeName="r" values="6;16;6" dur="2.2s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="1;0;1" dur="2.2s" repeatCount="indefinite"/></circle>'
    )
    total = sum(v for _, v in series)
    body = (
        grid
        + f'<path d="{area}" fill="url(#area)" class="fade" style="animation-delay:1.4s"/>'
        + f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="3" stroke-linejoin="round" filter="url(#glow)" '
        f'stroke-dasharray="{length:.0f}" stroke-dashoffset="{length:.0f}" style="animation: draw 2s ease-out forwards"/>'
        + dots + pulse + labels
        + f'<text x="{x1}" y="44" text-anchor="end" class="v" style="font-size:20px">{total}</text>'
        + f'<text x="{x1}" y="64" text-anchor="end" class="m">contributions · 12 months</text>'
    )
    return frame(W, H, body, "Contribution Trend", "Monthly commits, PRs and reviews · refreshed daily")


# ---------------------------------------------------------------- radar
def radar_svg():
    W, H = 900, 420
    cx, cy, R = 230, 240, 135
    n = len(EXPERTISE)
    ang = [-math.pi / 2 + i * 2 * math.pi / n for i in range(n)]

    def p(r, a):
        return r * math.cos(a), r * math.sin(a)

    rings = ""
    for k in (0.25, 0.5, 0.75, 1):
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in (p(R * k, a) for a in ang))
        rings += f'<polygon points="{poly}" fill="none" stroke="{GRID}"/>'
        rings += f'<text x="4" y="{-R*k+4:.1f}" class="m" style="font-size:9px">{int(k*100)}</text>'
    spokes = "".join(f'<line x1="0" y1="0" x2="{x:.1f}" y2="{y:.1f}" stroke="{GRID}"/>' for x, y in (p(R, a) for a in ang))
    axis_lbl = ""
    for (name, _), a in zip(EXPERTISE, ang):
        x, y = p(R + 22, a)
        anchor = "middle" if abs(x) < 10 else ("start" if x > 0 else "end")
        axis_lbl += f'<text x="{x:.1f}" y="{y+4:.1f}" text-anchor="{anchor}" class="l" style="font-size:12px">{name}</text>'
    vals = [p(R * v / 100, a) for (_, v), a in zip(EXPERTISE, ang)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in vals)
    dots = ""
    for i, (x, y) in enumerate(vals):
        dots += (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{ACCENT}" filter="url(#glow)">'
            f'<animate attributeName="r" values="4;6.5;4" dur="2.4s" begin="{1.2+i*0.25:.2f}s" repeatCount="indefinite"/></circle>'
        )
    radar = (
        f'<g transform="translate({cx},{cy})">{rings}{spokes}{axis_lbl}'
        f'<g style="animation: grow 1.2s cubic-bezier(.2,.8,.2,1) forwards; transform: scale(0)">'
        f'<polygon points="{poly}" fill="{ACCENT}" fill-opacity=".22" stroke="{ACCENT}" stroke-width="2.5" filter="url(#glow)"/>'
        f'{dots}</g></g>'
    )

    bars = ""
    bx, bw, by0 = 520, 230, 120
    for i, (name, v) in enumerate(EXPERTISE):
        y = by0 + i * 40
        d = 0.4 + i * 0.15
        bars += (
            f'<circle cx="{bx}" cy="{y-4}" r="5" fill="{ACCENT}"/>'
            f'<text x="{bx+14}" y="{y}" class="l">{name}</text>'
            f'<rect x="{bx+14}" y="{y+8}" width="{bw}" height="6" rx="3" fill="{GRID}"/>'
            f'<rect x="{bx+14}" y="{y+8}" width="0" height="6" rx="3" fill="{ACCENT}">'
            f'<animate attributeName="width" from="0" to="{bw*v/100:.1f}" dur="1.1s" begin="{d:.2f}s" fill="freeze" '
            f'calcMode="spline" keySplines=".2 .8 .2 1" keyTimes="0;1"/></rect>'
            f'<text x="{bx+bw+30}" y="{y+14}" class="v" text-anchor="start">{v}%</text>'
        )
    return frame(W, H, radar + bars, "Core Technical Expertise",
                 "Each corner is a core tool, the net shows how deep I go")


# ---------------------------------------------------------------- pipeline
def pipeline_svg():
    W, H = 900, 250
    stages = [
        ("Sources", ["Shopify", "Meta · Google Ads", "GA4 · Klaviyo", "REST APIs"]),
        ("Ingest", ["Python + REST", "n8n · Airflow", "PySpark"]),
        ("Warehouse", ["BigQuery", "SQL models", "Validation checks"]),
        ("Decisions", ["Power BI · Looker", "Forecasts", "Gemini AI agent"]),
    ]
    bw, bh, gap, top = 180, 150, 46, 60
    left = (W - (4 * bw + 3 * gap)) / 2
    body = ""
    for i, (name, items) in enumerate(stages):
        x = left + i * (bw + gap)
        d = 0.2 + i * 0.35
        lines = "".join(f'<text x="{x+bw/2:.1f}" y="{top+62+j*20}" text-anchor="middle" class="s">{t}</text>' for j, t in enumerate(items))
        body += (
            f'<g class="fade" style="animation-delay:{d:.2f}s">'
            f'<rect x="{x:.1f}" y="{top}" width="{bw}" height="{bh}" rx="12" fill="{BG1}" stroke="{ACCENT}" stroke-opacity=".6"/>'
            f'<rect x="{x:.1f}" y="{top}" width="{bw}" height="4" rx="2" fill="{ACCENT}"/>'
            f'<text x="{x+bw/2:.1f}" y="{top+34}" text-anchor="middle" class="l" style="font-size:15px">{name}</text>'
            f'{lines}</g>'
        )
        if i < 3:
            ax, ay = x + bw + 4, top + bh / 2
            bx = ax + gap - 8
            pid = f"p{i}"
            body += (
                f'<path id="{pid}" d="M{ax:.1f},{ay} L{bx:.1f},{ay}" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="4 4">'
                f'<animate attributeName="stroke-dashoffset" from="16" to="0" dur=".8s" repeatCount="indefinite"/></path>'
                f'<polygon points="{bx:.1f},{ay-5} {bx+7:.1f},{ay} {bx:.1f},{ay+5}" fill="{ACCENT}"/>'
            )
            for k in range(2):
                body += (
                    f'<circle r="3.5" fill="{TEXT}" filter="url(#glow)">'
                    f'<animateMotion dur="1.6s" begin="{k*0.8:.1f}s" repeatCount="indefinite"><mpath href="#{pid}"/></animateMotion></circle>'
                )
    body += f'<text x="{W/2}" y="38" text-anchor="middle" class="s">raw data in  →  trusted decisions out</text>'
    return frame(W, H, body)


# ---------------------------------------------------------------- impact tiles
IMPACT = [  # (final label, count-up frames, caption line 1, caption line 2, fill fraction)
    ("16M+", ["2M", "5M", "8M", "11M", "14M", "16M+"], "retail records", "processed (PySpark)", 1.0),
    ("168/168", ["24/168", "60/168", "96/168", "132/168", "160/168", "168/168"], "audited periods", "matched by AI agent", 1.0),
    ("0.3%", ["5.0%", "3.1%", "1.8%", "0.9%", "0.5%", "0.3%"], "max revenue", "variance (5 stores)", 0.997),
    ("+28%", ["+4%", "+9%", "+15%", "+20%", "+25%", "+28%"], "inventory-planning", "accuracy gain", 0.28),
]


def impact_svg():
    W, H = 900, 190
    n = len(IMPACT)
    gap, pad = 16, 20
    tw = (W - 2 * pad - (n - 1) * gap) / n
    th, top = 150, 20
    body = ""
    for i, (final, frames, c1, c2, frac) in enumerate(IMPACT):
        x = pad + i * (tw + gap)
        cx = x + tw / 2
        d0 = 0.15 + i * 0.2
        tile = (
            f'<rect x="{x:.1f}" y="{top}" width="{tw:.1f}" height="{th}" rx="12" fill="{BG1}" stroke="{ACCENT}" stroke-opacity=".55"/>'
            f'<rect x="{x+18:.1f}" y="{top+92}" width="{tw-36:.1f}" height="4" rx="2" fill="{GRID}"/>'
            f'<rect x="{x+18:.1f}" y="{top+92}" width="0" height="4" rx="2" fill="{ACCENT}">'
            f'<animate attributeName="width" from="0" to="{(tw-36)*frac:.1f}" dur="1.2s" begin="{d0+0.2:.2f}s" fill="freeze" '
            f'calcMode="spline" keySplines=".2 .8 .2 1" keyTimes="0;1"/></rect>'
            f'<text x="{cx:.1f}" y="{top+122}" text-anchor="middle" class="s">{c1}</text>'
            f'<text x="{cx:.1f}" y="{top+140}" text-anchor="middle" class="s">{c2}</text>'
        )
        # count-up: each frame text is shown for a moment, the last one stays
        step = 0.16
        for k, label in enumerate(frames):
            on = d0 + 0.2 + k * step
            last = k == len(frames) - 1
            show = f'<set attributeName="opacity" to="1" begin="{on:.2f}s"/>'
            hide = "" if last else f'<set attributeName="opacity" to="0" begin="{on+step:.2f}s"/>'
            style = f'fill:{TEXT if last else ACCENT};font-size:30px;font-weight:700'
            glow = ' filter="url(#glow)"' if last else ""
            tile += (
                f'<text x="{cx:.1f}" y="{top+66}" text-anchor="middle" opacity="0" style="{style}"{glow}>'
                f'{show}{hide}{label}</text>'
            )
        body += f'<g class="fade" style="animation-delay:{d0:.2f}s">{tile}</g>'
    return frame(W, H, body)


# ---------------------------------------------------------------- skill buttons
SKILL_BTN = [  # (file key, label, level)
    ("python", "Python", 96), ("pyspark", "PySpark", 94), ("bigquery", "SQL / BigQuery", 95),
    ("dashboards", "Dashboards", 98), ("gcp", "Cloud (GCP)", 88), ("ml", "ML / DL", 92),
    ("workflows", "n8n / Workflows", 80),
]


def skill_button_svg(i, label, level):
    w = 34 + len(label) * 8.2 + 62
    h = 36
    lw = w - 62
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h}" viewBox="0 0 {w:.0f} {h}">
<defs>
  <linearGradient id="shine" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <clipPath id="c"><rect width="{w:.0f}" height="{h}" rx="8"/></clipPath>
</defs>
<g clip-path="url(#c)">
  <rect width="{w:.0f}" height="{h}" fill="{BG1}"/>
  <rect x="{lw:.0f}" width="62" height="{h}" fill="{ACCENT}"/>
  <circle cx="17" cy="18" r="4" fill="{ACCENT}"><animate attributeName="opacity" values="1;.3;1" dur="2s" begin="{i*0.3:.1f}s" repeatCount="indefinite"/></circle>
  <text x="29" y="23" style="font-family:{FONT};font-size:13px;font-weight:600;fill:{TEXT}">{label}</text>
  <text x="{lw+31:.0f}" y="23" text-anchor="middle" style="font-family:{FONT};font-size:13px;font-weight:800;fill:{BG1}">{level}%</text>
  <rect x="-80" width="60" height="{h}" fill="url(#shine)" transform="skewX(-20)">
    <animate attributeName="x" values="-80;{w+60:.0f};{w+60:.0f}" keyTimes="0;.35;1" dur="5s" begin="{i*0.6:.1f}s" repeatCount="indefinite"/>
  </rect>
</g>
<rect x=".5" y=".5" width="{w-1:.0f}" height="{h-1}" rx="8" fill="none" stroke="{ACCENT}" stroke-opacity=".6"/>
</svg>
"""


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "impact.svg").write_text(impact_svg(), encoding="utf-8")
    for i, (key, label, level) in enumerate(SKILL_BTN):
        (OUT / f"skill-{key}.svg").write_text(skill_button_svg(i, label, level), encoding="utf-8")
    (OUT / "expertise-radar.svg").write_text(radar_svg(), encoding="utf-8")
    (OUT / "pipeline-flow.svg").write_text(pipeline_svg(), encoding="utf-8")
    (OUT / "commit-trend.svg").write_text(trend_svg(fetch_monthly()), encoding="utf-8")
    print("charts written to", OUT)


if __name__ == "__main__":
    main()
