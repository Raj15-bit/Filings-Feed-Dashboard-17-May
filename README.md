# Filings Feed Dashboard

Turn a weekly Investor Feed HTML export into a single interactive dashboard that helps you find good companies fast — every company scored 0–120 with clear reasons, sector heat strip, full searchable filings table, light + dark mode, all on one page.

[![Made with Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![No dependencies](https://img.shields.io/badge/Dependencies-stdlib%20only-success.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What this does

You drop a weekly filings HTML export into the `input/` folder. You run one command. You get a fully interactive HTML dashboard in `output/` that you can open in any browser.

The dashboard shows:

- **Find Good Companies** — every company scored on quality with the exact reasons why
- **Sector Heat Strip** — Red-Hot / Hot / Warm / Cool / Cold rating per sector
- **Overview KPIs** — total filings, unique companies, market cap, signal mix
- **Heatmaps** — sector × signal type, sub-sector × signal type
- **Segments tree** — drill down sector → sub-sector
- **Rankings** — top by market cap, ROE, low P/E, most active
- **Themes** — cross-cutting patterns (AI, EV, exports, M&A wave, etc.)
- **All filings table** — every row, fully searchable / filterable
- **Insights** — narrative synthesis of the week

Light and dark mode toggle. Self-contained HTML — no server, no dependencies, works offline (except for two CDN scripts).

---

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/YOURUSERNAME/filings-dashboard.git
cd filings-dashboard

# 2. Drop your weekly HTML export into input/
cp ~/Downloads/Investor_Feed_Filings_May11-17_2026.html input/

# 3. Run the pipeline
python run_all.py

# 4. Open the dashboard
open output/filings_dashboard.html        # macOS
xdg-open output/filings_dashboard.html    # Linux
start output/filings_dashboard.html       # Windows
```

That's it. No `pip install`, no virtualenv — uses only Python's standard library.

---

## Updating each week

```bash
# 1. Add the new week's HTML to input/ (the old one can stay or be deleted)
cp ~/Downloads/Investor_Feed_Filings_NEW_WEEK.html input/

# 2. Run the pipeline (picks up the newest .html automatically)
python run_all.py

# 3. Commit + push
git add output/filings_dashboard.html input/*.html
git commit -m "Week of May 11-17, 2026"
git push
```

The intermediate JSON files in `data/` are regenerated each run and are git-ignored by default.

---

## Folder structure

```
filings-dashboard/
├── README.md                   ← you are here
├── PLAYBOOK.md                 ← detailed methodology + scoring math
├── run_all.py                  ← one-command pipeline runner
├── requirements.txt            ← (empty — stdlib only)
├── .gitignore
│
├── input/                      ← drop weekly HTML export here
│   └── .gitkeep
│
├── data/                       ← intermediate JSON files (auto-generated)
│   └── .gitkeep
│
├── output/
│   └── filings_dashboard.html  ← the dashboard
│
├── scripts/
│   ├── 1_parse.py              ← HTML → raw rows
│   ├── 2_classify.py           ← + signals, sentiment, sector groups
│   ├── 3_score.py              ← + company quality scores + sector strength
│   ├── 4_build_html.py         ← assembles the final dashboard
│   └── dashboard_template.html ← HTML template with __PAYLOAD__ placeholder
│
└── docs/
    └── (screenshots, etc.)
```

---

## How the scoring works (short version)

Every company in the week's feed gets a Quality Score from roughly 0 to 120 combining:

| Component             | Roughly contributes                |
|-----------------------|------------------------------------|
| Momentum signals      | +12 per order win, +11 per M&A, +10 per capex, +10 per buyback, +8 per dividend, +5 per partnership, etc. |
| Financial health      | up to +20 for elite ROE, +8 for attractive P/E, +6 for mega cap |
| Sentiment ratio       | +8 if 75%+ of filings are positive |
| Activity level        | +4 if 5+ filings in the week       |
| Sector tailwind       | +12 if in a Red-Hot sector, −4 if in a Cold one |
| Penalties             | −15 for litigation, −3 per management resignation |

Tiers based on total score:
- **70+** Exceptional
- **50-70** Strong
- **32-50** Good
- **15-32** Average
- **0-15** Watch
- **<0** Risk

Each card shows the top 6 weighted reasons, e.g. *"+ won new orders/contracts (3x) +18"*, *"★ elite ROE (34.2%) +16"*, *"★ in Red-Hot sector (Industrials, 101/100) +12"*.

Full scoring math, signal taxonomy, sector mapping, and tier thresholds are in **[PLAYBOOK.md](PLAYBOOK.md)**.

---

## Input file format

The pipeline expects an HTML file with a table structured like:

```html
<table>
  <tbody>
    <tr>
      <td>1</td>
      <td>Company Name Ltd</td>
      <td>May 17, 2026</td>
      <td>11 hrs ago</td>
      <td>
        P/B Ratio:<br>1.27<br>
        ROE:<br>13.63 %<br>
        Market Cap:<br>7,704.52 Cr<br>
        Sector:<br>Industrial Products - Capital Goods<br>
        P/E Ratio:<br>8.94<br>
        Sub-Sector:<br>Iron & Steel Products<br>
        Headline of the filing<br>
        - bullet point 1<br>
        - bullet point 2<br>
      </td>
    </tr>
  </tbody>
</table>
```

If your source has a different format, only `scripts/1_parse.py` needs adjusting.

---

## Hosting on GitHub Pages (live URL)

Want a public URL for your dashboard? After pushing to GitHub:

1. Go to **Settings → Pages**
2. Under **Source**, pick **Deploy from a branch → main → /(root)**
3. Save. Wait 60 seconds.
4. Your dashboard will be live at `https://YOURUSERNAME.github.io/filings-dashboard/output/filings_dashboard.html`

Or move the HTML to the repo root or `docs/` folder if you want a cleaner URL.

The HTML is fully self-contained — no build step needed, GitHub Pages just serves it as a static file.

---

## Customizing

Edit any of these to tune the dashboard to your taste:

| What to change            | Where                                               |
|---------------------------|-----------------------------------------------------|
| Add a new signal type     | `scripts/2_classify.py` → `SIGNAL_RULES`           |
| Change a signal's weight  | `scripts/3_score.py` → `POS_SIGNALS` / `NEG_SIGNALS`|
| Adjust tier cut-offs      | `scripts/3_score.py` → near the end of `score_company` |
| Re-map a sector → group   | `scripts/2_classify.py` → `SECTOR_GROUP_MAP`        |
| Tweak colours / fonts     | `scripts/dashboard_template.html` → `<style>` block |
| Add a new chart / section | `scripts/dashboard_template.html` + matching JS     |

---

## Limitations (honest caveats)

- **Classification is keyword-based.** Fast and explainable, but misses unusual phrasing. Manual sanity-check of edge cases is worth doing.
- **Sentiment is a heuristic** — "record loss" would count positive because "record" is positive. Naive but useful in aggregate.
- **The Quality Score is descriptive, not predictive.** Tells you who had a good filing week, not what stock will go up. Use it as a starting filter.
- **Numbers come from the source feed.** If the feed has stale or wrong values (ROE = 315%, P/E = 3,475), the score inherits that error.
- **No buy / sell recommendations.** Research tool only. Do your own diligence.

---

## License

MIT — do whatever you want with it. Credit appreciated but not required.

---

## Built with

- Plain Python 3 (no dependencies)
- [Chart.js](https://www.chartjs.org/) v4.5 (CDN, MIT)
- [Grid.js](https://gridjs.io/) v5.0 (CDN, MIT)
- Inter + JetBrains Mono fonts (Google Fonts)

Everything else is hand-written CSS and vanilla JavaScript.
