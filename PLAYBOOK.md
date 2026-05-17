# Filings Feed Dashboard — Reusable Playbook

This is the full recipe for turning a weekly Investor Feed HTML file into an interactive dashboard with a Good Company Finder.

**Next week, just say:** "use the FILINGS_DASHBOARD_PLAYBOOK.md and build the dashboard for this week's file."

---

## 1. What this dashboard does

Takes a raw HTML export of the week's company filings (the file looks like `Investor_Feed_Filings_MayXX-XX_2026.html`) and produces a single self-contained interactive HTML dashboard with:

- **Find Good Companies** — every company scored 0-120 with reasons WHY
- **Sector heat strip** — Red-Hot to Cold rating per sector group
- **Overview** — KPIs, daily activity, sentiment, signal mix
- **Heatmaps** — sector × signal type, sub-sector × signal type
- **Segments tree** — drill down sector → sub-sector
- **Rankings** — top by market cap, ROE, low P/E, most active
- **Themes** — cross-cutting patterns (AI, EV, exports, M&A wave, etc.)
- **All filings table** — every row searchable / filterable
- **Insights** — narrative synthesis of the week

All on one page. Light + dark mode toggle. No pagination needed.

---

## 2. Input file format expected

The source is an HTML file with this structure:

```html
<table>
  <thead>
    <tr><th>#</th><th>Company</th><th>Date</th><th>Posted</th><th>Filing Details / Summary</th></tr>
  </thead>
  <tbody>
    <tr>
      <td>1</td>
      <td class="company">Maharashtra Seamless Ltd</td>
      <td class="date">May 17, 2026</td>
      <td class="time">11 hrs 55 mins ago</td>
      <td class="content">
        P/B Ratio:<br>1.27<br>
        ROE:<br>13.63 %<br>
        Market Cap:<br>7,704.52 Cr<br>
        Sector:<br>Industrial Products - Capital Goods<br>
        P/E Ratio:<br>8.94<br>
        Sub-Sector:<br>Iron & Steel Products<br>
        Headline of the filing here<br>
        - bullet point 1<br>
        - bullet point 2<br>
      </td>
    </tr>
    ...
  </tbody>
</table>
```

**Key fields inside each filing's content cell** (each on its own line, separated by `<br>`):

| Field         | Format                                  | Notes |
|---------------|-----------------------------------------|-------|
| P/B Ratio     | number                                   | optional |
| ROE           | "X.XX %" or "X.XX%"                       | optional |
| Market Cap    | "X,XXX.XX Cr"                            | optional |
| Sector        | "Primary - GroupSuffix"                  | e.g. "Pharmaceuticals & Biotechnology - Healthcare" |
| P/E Ratio     | number                                   | can be very large or missing |
| Sub-Sector    | string                                   | finer category |
| Headline      | first non-structured line (often emoji)  | extract here |
| Bullets       | lines starting with "-"                   | summary detail |

If the source format changes, only the parsing step needs adjustment.

---

## 3. Pipeline overview (4 steps)

```
[Input HTML]  →  parse_filings.py  →  filings_raw.json
              →  classify.py       →  filings_enriched.json
              →  score3.py         →  scored.json + sector_strength.json
              →  build_html.py + inject_finder.py → filings_dashboard.html
```

Working directory used in this session: `/tmp/` (Linux sandbox).
Final output goes to the outputs folder so it's clickable from chat.

---

## 4. Step 1 — Parse filings (extract raw rows)

Logic:

1. Find the `<tbody>...</tbody>` block in the source HTML.
2. Split on `<tr>` tags.
3. For each row, extract 5 `<td>` cells (#, company, date, posted, content).
4. Inside the content cell, convert `<br>` to newlines, strip remaining tags, unescape HTML entities, split on newlines.
5. Pull structured fields by finding the line that matches each key (e.g. "P/B Ratio:") and taking the next line as the value.
6. The "headline" is the first line that's not a structured key/value pair (usually emoji + sentence).
7. The "summary" is the rest of the non-structured lines.

Output: `filings_raw.json` — array of records with `{idx, company, date, posted, lines, pb, roe, mcap, pe, sector, subsector, headline, summary}`.

---

## 5. Step 2 — Enrich + classify signals

Add to each record:

- **`signals`** — list of signal-type tags (e.g. `["Results/Earnings", "Dividend"]`)
- **`primary_signal`** — first one in the list (the most specific match)
- **`sentiment`** — Positive / Neutral / Negative
- **`group`** — broad sector group (Industrials, Financials, Healthcare, etc.)
- **`mcap_bucket`** — Mega / Large / Mid / Small / Micro / Nano
- **`iso`** — date in YYYY-MM-DD format

### Signal taxonomy (22 types, ordered by specificity)

```python
SIGNAL_RULES = [
    ('Results/Earnings',     ['record date for q','q4fy','quarterly result','financial result',
                              'earnings','board meeting','revenue from operations','pat',
                              'profit after tax','ebitda','consolidated financial','reports',
                              'reported','crore in q','crore in fy','revenue reached',
                              'revenue grew','revenue surged','reports record','profit grew',
                              'profit rose','net profit','annual report','fy26','fy25 results']),
    ('Dividend',             ['dividend','interim dividend','final dividend',
                              'record date for dividend','book closure for dividend',
                              'declared a dividend','equity dividend']),
    ('Order Win',            ['order','contract','loi','letter of intent','letter of award',
                              'awarded','bagged','secured','export order','tender',
                              'work order','purchase order','supply','agreement worth']),
    ('Acquisition/M&A',      ['acquisition','acquire','acquired','acquires','to acquire',
                              'sells stake','divest','strategic stake','merger','amalgamation',
                              'scheme of arrangement','open offer','takeover','majority stake']),
    ('Subsidiary/JV',        ['subsidiary','wholly owned','wholly-owned','wos','joint venture',
                              ' jv ','incorporated','incorporation','step-down','new entity']),
    ('Demerger/Restructure', ['demerger','spin-off','restructuring','hive off','slump sale']),
    ('Fundraise/QIP',        ['qip','rights issue','preferential allotment','allotment of equity',
                              'allotment of warrant','fpo','ofs','ipo','capital infusion',
                              'bond issue','ncd','debenture','commercial paper','term loan',
                              'debt raising','fund raising','equity infusion']),
    ('Buyback',              ['buyback','buy-back','buy back','tender buyback']),
    ('Stock Split/Bonus',    ['stock split','split of equity','sub-division','bonus issue',
                              'bonus share','bonus shares']),
    ('Capex/Expansion',      ['capex','capital expenditure','expansion','new plant',
                              'new facility','commissioning','commissioned','commencement',
                              'commenced','greenfield','brownfield','new factory',
                              'capacity expansion','plant expansion']),
    ('Product Launch',       ['product launch','launches','launched','unveils','unveiled',
                              'new product','rollout','rolled out','to launch','introduces',
                              'new model','new variant']),
    ('Partnership/MOU',      ['partnership','partner','mou','memorandum of understanding',
                              'collaboration','strategic tie','alliance','tie-up',
                              'strategic agreement','license','licensing']),
    ('Regulatory/Approval',  ['approval','approved by','clearance','sebi','rbi','irdai','cci',
                              'cdsco','dgca','noc','license granted','permission','sanction',
                              'environmental clearance']),
    ('Credit Rating',        ['credit rating','rating','reaffirmed','upgrade','downgrade',
                              'crisil','icra','care ratings','india ratings','brickwork',
                              'negative outlook','positive outlook','stable outlook']),
    ('Litigation/Legal',     ['litigation','lawsuit','court order','show cause','sebi order',
                              'tribunal','nclat','nclt','penalty','fine imposed','arbitration']),
    ('Insider/Shareholding', ['insider','sast','pledge','pledged','released pledge',
                              'encumbrance','promoter holding','promoter shareholding']),
    ('AGM/EGM',              ['agm','annual general meeting','egm','extraordinary general',
                              'postal ballot','e-voting','evoting']),
    ('Management Change',    ['appointment','appointed','resignation','resigned','cessation',
                              'ceased','retirement','retired','re-designation','elevated',
                              'promoted to','new ceo','new cfo','new md','new chairman',
                              'reshuffle','director appointment']),
    ('Investor Meet/Concall', ['investor meet','investor presentation','analyst meet',
                              'earnings call','conference call','concall','road show']),
    ('Production Update',    ['production update','production volume','sales volume',
                              'monthly sales','vehicle sales','dispatch','dispatches',
                              'offtake','utilization']),
    ('ESG/CSR',              ['esg','sustainability','carbon','net zero','renewable','green',
                              'csr','corporate social responsibility']),
]
```

Match logic: lowercase the headline + summary, check if any keyword is in the text. Order matters — earlier rules are more specific. A filing can match multiple signals.

If nothing matches → `Other/General Update`.

### Sentiment (keyword heuristic)

```python
POSITIVE = ['record','highest','strong','growth','surge','surged','rose','jumped','grew',
            'beat','beats','win','wins','secured','bagged','approval','approved','expansion',
            'upgrade','positive','dividend','launch','launches','partnership','breakthrough']

NEGATIVE = ['decline','declined','fall','fell','loss','losses','penalty','fine','downgrade',
            'negative','litigation','resign','resignation','show cause','breach','default',
            'suspended','revoked','warning','concern']
```

Logic: count P (positive hits) and N (negative hits) in the lowercase text.
- If `P − N >= 2` → Positive
- If `N − P >= 1` → Negative
- Else → Neutral

### Sector group mapping (18 broad groups)

```python
SECTOR_GROUP_MAP = {
    'Pharmaceuticals & Biotechnology': 'Healthcare',
    'Healthcare Services':              'Healthcare',
    'Healthcare Equipment & Supplies':  'Healthcare',
    'Finance':                          'Financials',
    'Banks':                            'Financials',
    'Insurance':                        'Financials',
    'Capital Markets':                  'Financials',
    'Diversified Financials':           'Financials',
    'Chemicals & Petrochemicals':       'Materials',
    'Cement & Cement Products':         'Materials',
    'Metals & Mining':                  'Materials',
    'Ferrous Metals':                   'Materials',
    'Non-Ferrous Metals':               'Materials',
    'Paper Products':                   'Materials',
    'Industrial Products':              'Industrials',
    'Industrial Manufacturing':         'Industrials',
    'Electrical Equipment':             'Industrials',
    'Capital Goods':                    'Industrials',
    'Construction':                     'Industrials',
    'Construction Services':            'Industrials',
    'Aerospace & Defense':              'Industrials',
    'Transport Services':               'Industrials',
    'Transportation Infrastructure':    'Industrials',
    'Logistics':                        'Industrials',
    'Engineering':                      'Industrials',
    'Auto Components':                  'Consumer Discretionary',
    'Automobiles':                      'Consumer Discretionary',
    'Consumer Durables':                'Consumer Discretionary',
    'Leisure Services':                 'Consumer Discretionary',
    'Textiles & Apparels':              'Consumer Discretionary',
    'Realty':                           'Real Estate',
    'IT - Services':                    'Information Technology',
    'IT - Software':                    'Information Technology',
    'IT - Hardware':                    'Information Technology',
    'Telecom - Services':               'Communication',
    'Telecom - Equipment':              'Communication',
    'Media':                            'Communication',
    'Entertainment':                    'Communication',
    'Power':                            'Utilities',
    'Gas':                              'Utilities',
    'Utilities':                        'Utilities',
    'Food Products':                    'Consumer Staples',
    'Beverages':                        'Consumer Staples',
    'Personal Products':                'Consumer Staples',
    'Household Products':               'Consumer Staples',
    'Agricultural':                     'Consumer Staples',
    'Tobacco Products':                 'Consumer Staples',
    'Oil':                              'Energy',
    'Oil & Gas':                        'Energy',
    'Coal':                             'Energy',
    'Petroleum Products':               'Energy',
    'Renewable Energy':                 'Energy',
    'Retailing':                        'Consumer Discretionary',
    'Hotels':                           'Consumer Discretionary',
    'Travel':                           'Consumer Discretionary',
}
```

### Market-cap buckets

```python
if   mcap >= 100000: 'Mega (>1 Lakh Cr)'
elif mcap >=  50000: 'Large (50k-1L Cr)'
elif mcap >=  20000: 'Large (20-50k Cr)'
elif mcap >=   5000: 'Mid (5-20k Cr)'
elif mcap >=   1000: 'Small (1-5k Cr)'
elif mcap >=    250: 'Micro (250-1000 Cr)'
else:                'Nano (<250 Cr)'
```

Output: `filings_enriched.json` — same fields as raw plus `signals, primary_signal, sentiment, group, mcap_bucket, iso, headline_clean`.

---

## 6. Step 3 — Score every company

Aggregate filings by company, then compute one Quality Score per company.

### A. Positive signal weights

| Signal              | Points |
|---------------------|-------:|
| Order Win           | +12    |
| Acquisition / M&A   | +11    |
| Capex / Expansion   | +10    |
| Buyback             | +10    |
| Dividend            | +8     |
| Subsidiary / JV     | +6     |
| Partnership / MOU   | +5     |
| Product Launch      | +5     |
| Stock Split / Bonus | +5     |
| Results / Earnings  | +4     |
| Regulatory Approval | +4     |
| Fundraise / QIP     | +3     |
| Credit Rating       | +2     |
| Production Update   | +2     |
| Investor Meet/Concall | +2   |
| AGM / EGM           | +1     |
| ESG / CSR           | +1     |

Multiple occurrences of the same signal get diminishing returns:
`pts = base + base × 0.4 × ln(count)` when count > 1.

### B. Negative signal weights

| Signal               | Points |
|----------------------|-------:|
| Litigation / Legal   | −15    |
| Management Change    | −3     |
| Demerger / Restructure | −1   |
| Insider / Shareholding | −2   |

Multiple occurrences cap at 2x.

### C. Financial health

**ROE (use the maximum across the company's filings):**

| ROE Range  | Points | Label                |
|------------|-------:|----------------------|
| ≥ 30%      | +20    | world-class ROE      |
| ≥ 22%      | +16    | elite ROE            |
| ≥ 16%      | +11    | strong ROE           |
| ≥ 12%      | +7     | decent ROE           |
| ≥ 8%       | +3     | modest ROE           |
| 5-8%       | 0      | (neutral)            |
| < 5%       | −3     | low ROE              |
| < 0%       | −8     | negative ROE         |

**P/E (use the average; ignore values > 5000):**

| P/E Range  | Points | Label              |
|------------|-------:|--------------------|
| 5-22       | +8     | attractive P/E     |
| < 5        | +4     | deep value P/E     |
| 22-35      | +4     | growth P/E         |
| 35-60      | 0      | (neutral)          |
| 60-100     | −2     | high P/E           |
| > 100      | −4     | very high P/E      |

**P/B:**
- 0.5-4 → +3
- > 10  → −3

**Market cap (size / liquidity bonus):**
- ≥ 1 Lakh Cr → +6
- ≥ 20k Cr   → +4
- ≥ 5k Cr    → +2
- ≥ 1k Cr    → +1

### D. Sentiment bonus

Compute `pos_pct = positive_filings / total_filings` for that company.

- `pos_pct ≥ 0.75` and total ≥ 2 → +8 ("75%+ positive filings")
- `pos_pct ≥ 0.50` and total ≥ 2 → +4 ("50%+ positive filings")
- Negative > Positive             → −6 ("more negative than positive")

### E. Activity bonus

- ≥ 5 filings in the week → +4 ("highly active management")
- ≥ 3 filings             → +2

### F. Sector tailwind (the new piece you asked for)

**First compute sector group strength** (per group, on filings where `total >= 10`):

```python
hot_signals  = ['Order Win','Acquisition/M&A','Capex/Expansion',
                'Partnership/MOU','Product Launch','Buyback','Dividend']
cold_signals = ['Litigation/Legal','Demerger/Restructure']

hot_ratio = hot_signal_count / total_filings
pos_ratio = positive_filings / total_filings
neg_ratio = negative_filings / total_filings

sector_score = 30 + (hot_ratio * 50) + (pos_ratio * 40) - (neg_ratio * 30) - (cold_ratio * 10)
```

Labels:
- ≥ 75 → **Red-Hot**
- ≥ 60 → **Hot**
- ≥ 45 → **Warm**
- ≥ 30 → **Cool**
- < 30 → **Cold**

Groups with total < 10 filings get tagged "Small Sample" and score 50 (neutral).

**Then apply tailwind bonus to each company:**

| Sector State | Bonus |
|--------------|------:|
| Red-Hot      | +12   |
| Hot          | +8    |
| Warm         | +4    |
| Cool         | 0     |
| Cold         | −4    |

The reason "in Red-Hot sector (Industrials, 101/100)" appears in the company's WHY list.

### G. Tier thresholds (final classification)

| Total Score | Tier         |
|-------------|--------------|
| ≥ 70        | Exceptional  |
| ≥ 50        | Strong       |
| ≥ 32        | Good         |
| ≥ 15        | Average      |
| ≥ 0         | Watch        |
| < 0         | Risk         |

### H. The reasons array

Each scoring rule that fires contributes one entry to a `reasons` list with `{sign, txt, pts, sig}`. Sort by `|pts|` descending and keep the top 7 — that's what shows on the card.

`sign` is one of `+` (positive signal), `★` (positive financial/sentiment/sector), or `−` (negative).

---

## 7. Step 4 — Build the HTML dashboard

### A. Design system

**Light mode palette:**
```
--bg #fafbfc · --bg2 #ffffff · --bg3 #f3f5f8 · --text #0f172a · --text2 #475569
--accent #2563eb · --pos #059669 · --neg #dc2626 · --warn #d97706 · --neu #64748b
```

**Dark mode:**
```
--bg #0a0e1a · --bg2 #11172a · --bg3 #1a2236 · --text #f1f5f9 · --text2 #cbd5e1
--accent #3b82f6 · --pos #10b981 · --neg #f87171 · --warn #fbbf24
```

Toggle stored in `localStorage` as `ff-theme`.

**Typography:** Inter for sans, JetBrains Mono for numbers (via Google Fonts import).

**Heatmap scale (sqrt-normalized so mid-values pop):** `--heat-0` through `--heat-6`, blue ramp from `#f8fafc` to `#1e3a8a`.

### B. CDN libraries (artifact-allowed)

- Chart.js 4.5.0 (bars, doughnuts, horizontal bars)
- Grid.js 5.0.2 (the All Filings table — sortable, paginated 25/page, fixed header)
- Grid.js theme `mermaid.min.css`

### C. Page sections (in order)

1. **Sticky header** — logo, title, subtitle, theme toggle (SVG moon/sun), scroll-top button
2. **Sticky nav** — tab buttons that scroll-jump to each section
3. **Find Good Companies** (new main attraction) — sector strip + filter bar + card grid (top 60, show more)
4. **Overview** — 6 KPI tiles + 7 charts (daily, sentiment, signals, groups, mcap, sub-sectors, active companies)
5. **Heatmaps** — sector group × signal, sub-sector × signal, sentiment stack
6. **Segments** — 3-level tree (group → sector → sub-sector)
7. **Rankings** — top by mcap, ROE, low P/E, most active
8. **Themes** — 14 cross-cutting theme chips
9. **All Filings** — Grid.js table with 5 dropdown filters + free-text search
10. **Insights** — 6 narrative cards
11. **Footer**

### D. Card layout (Find Good Companies)

```
┌─────────────────────────────────────────┐
│ Company Name                  ┌──────┐  │
│ Sector → Sub-Sector           │ 100  │  │
│                               │STRONG│  │
│ [M.Cap bucket] [Red-Hot sec]  └──────┘  │
│ [3 filings]                             │
│                                         │
│ ┌────┬────┬────┬────┐                  │
│ │ROE │P/E │P/B │Mkt │                  │
│ │21% │18.2│2.1 │5k  │                  │
│ └────┴────┴────┴────┘                  │
│                                         │
│ Why this score        2↑ 1→ 0↓         │
│ ─────────────────────────────────────  │
│ ★  elite ROE (21.4%)            +16    │
│ +  won new orders/contracts     +12    │
│ ★  in Red-Hot sector            +12    │
│ +  reported results (2x)        +6     │
│ +  declared dividend            +8     │
│                                         │
│ ▓▓▓▓▓░░░░░ (sentiment bar)             │
└─────────────────────────────────────────┘
```

The left border color indicates the tier (green=Exceptional, cyan=Strong, blue=Good, gray=Average, amber=Watch, red=Risk).

### E. Filter wiring

Every dropdown change triggers `renderFinder()` which:
1. Filters the `DATA.scored` array by all active criteria
2. Sorts by the chosen key
3. Renders the first 60 cards (limit can be expanded)

State held in `_ffState = {q, g, mb, tier, roe, signal, sort, limit}`.

### F. Building the payload

Single JSON object embedded in `<script id="payload" type="application/json">...</script>`:

```js
{
  meta:   {total, companies, sectors, subsectors, groups, total_mcap, period},
  agg:    {dates, sentiments, signals, groups, sectors, subsectors, buckets, companies_top, themes},
  heatmap:{groups, signals, matrix, sub_groups, sub_matrix, sent_by_group},
  rankings:{mcap_top, roe_top, pe_low},
  records:[ {i, c, d, iso, p, sec, sub, g, mc, pe, pb, roe, mb, sg, ps, st, h, s}, ... 1282 rows ],
  scored: [ {company, score, tier, filings, sector, group, subsector, sec_label, sec_score,
             mcap, mcap_bucket, roe, pe, pb, pos, neu, neg, signals, reasons, headlines}, ... 568 ],
  sector_strength: { "Industrials": {score, label, total, pos, neg, hot, cold, ...}, ... }
}
```

---

## 8. How to run this next week

### Quick request to Claude

> "Build the filings dashboard for this week — use FILINGS_DASHBOARD_PLAYBOOK.md as the recipe. The input HTML is in my uploads folder."

Claude should then:

1. Read this MD file.
2. Find the new week's HTML in uploads (filename pattern `Investor_Feed_Filings_*.html`).
3. Run the 4-step pipeline.
4. Update the artifact and save the new dashboard HTML to outputs.

### What may need adjusting

- **If the source HTML format changes** — only the regex extraction in step 1 needs tweaking.
- **If new signal types appear** — add to `SIGNAL_RULES` in step 2 (more specific rules go first).
- **If new sectors appear** — add to `SECTOR_GROUP_MAP` in step 2.
- **If scoring feels off** — adjust the weight tables in step 3 (positive signals, ROE thresholds, etc.).
- **If you want a new tier cutoff** — change the thresholds in section 6G.

### What stays the same

- All four Python scripts (parse, classify, score, build_html).
- The full CSS / JS / HTML template.
- The CDN libraries.
- The artifact output path / id.

---

## 9. Files this pipeline produces

| File                          | Purpose                                 |
|-------------------------------|-----------------------------------------|
| `filings_raw.json`            | parsed rows, structured                  |
| `filings_enriched.json`       | raw + signals + sentiment + groups      |
| `scored.json`                 | 1 row per company, with score & reasons |
| `sector_strength.json`        | per-group hotness score                 |
| `filings_dashboard.html`      | **the final artifact**                  |

Only the last one is delivered to the user. The intermediate JSON files live in `/tmp/` and can be deleted after building.

---

## 10. Limitations / honest caveats

- **Signal classification is keyword-based.** It's fast and explainable, but it will miss things where the language is unusual or use unusual phrasing. Manual review of edge cases is worthwhile.
- **Sentiment is a heuristic.** "Record loss" would count as positive (because "record" is positive) — the rule is naive. Two factors get counted but context isn't fully understood.
- **The Quality Score is descriptive, not predictive.** It tells you which companies had a good filing week, not which stocks will do well. Use it as a starting filter, not a buy list.
- **ROE / P/E come from the source feed.** If the feed has stale or wrong values, the score inherits that error. Sanity-check outliers (e.g. ROE = 315%, P/E = 3,475) before relying on them.
- **No buy / sell recommendations.** This is a research tool. Do your own diligence.

---

## 11. Quick mental model

> **A company gets a high score this week if:**
> 1. It made several filings (active management)
> 2. The filings include order wins, M&A, capex, dividends, results — not just procedural stuff
> 3. The headlines lean positive
> 4. It has a real ROE (>15%) and a reasonable P/E (<35)
> 5. It's in a sector that's also hot this week
>
> **A company gets penalized if:**
> 1. There's litigation or a downgrade
> 2. Multiple management resignations
> 3. ROE is negative or P/E is absurd (>100)
> 4. Sentiment skews negative
> 5. Its sector is cold this week

That's the whole logic in seven lines. Everything else in this file is the implementation detail.

---

*Saved May 17, 2026. Pipeline tested on a 1,282-filing / 568-company week. Ready to re-use next week.*
