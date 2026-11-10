# Nepal in 1

**All of Nepal in one place:** news, the stock market, business, investment options, the economy and national projects, on one fast page that works on any phone.

Nepal in 1 is a public website, kept separate from any personal dashboard. Every story and figure links to its source.

## What's on it

| Tab | What you get |
|---|---|
| **Start here** | The front page: one question (how much can you put in?), the three best-fitting businesses with money to start and profit a month, and links to the rest |
| **Today in Nepal** | The day's key stories from across the country, filterable by topic, each with why it matters |
| **My builds** | A personal project board for each visitor: add a build, move it from Idea to Launched, track tasks, notes and a target month |
| **Mentor** | Businesses with published Nepal cost and profit studies, sized to the visitor's budget: money to start, profit a month, payback, first steps and what to watch out for. One tap adds a business to My builds with its first steps as tasks |
| **Business** | Key indicators, company news and upcoming business dates |
| **NEPSE** | Index chart (1M / 3M / all), sector moves, top gainers, losers and most traded, a fundamentals watchlist for banks, IPOs and share issues |
| **Invest** | A calculator comparing fixed deposits, savings bonds, NEPSE, gold and land: lump sum or monthly, low / expected / high, after tax and inflation; plus places to watch for property |
| **Economy** | GDP paths to 2036, IMF and ADB forecasts, what the economy is made of, hydropower export progress, a growth scorecard |
| **National projects** | Progress, cost and status of 25 national pride and major projects, by sector |

Light and dark mode follow the device setting.

**Visitor counting:** [GoatCounter](https://www.goatcounter.com) counts visits and tab views anonymously, with no cookies and no names. The numbers are at https://nepalin1.goatcounter.com (sign in with the owner's account).

**Where builds are saved:** only in the visitor's own browser, on that device. The site has no accounts and no server, so nobody else can see them, they don't follow the visitor to another device, and clearing the browser's data removes them. The calculator remembers its inputs the same way.

## How it's built

No framework and no build step: just two files.

| Path | What it is |
|---|---|
| `site/index.html` | The whole site: layout, styles and script in one file |
| `site/data.json` | The data: news, business, NEPSE, investment rates, places, mentor businesses |
| `scripts/check.mjs` | Health check: valid data, every tab wired up, script has no syntax errors |
| `.github/workflows/check.yml` | Runs the check on GitHub every time the site changes |
| `.github/workflows/deploy.yml` | Publishes `site/` to GitHub Pages every time it changes on `main` |
| `docs/slsa-generic-generator.yml` | Parked workflow for signing downloadable releases (not active) |

The economy and national-project figures live inside `index.html`. Everything that changes daily lives in `data.json`.

### Run it on your computer

```sh
cd site && python3 -m http.server 8000
# open http://localhost:8000
```

### Update the data

The data updates itself twice a day. A scheduled Claude task reads the public data that the Nepal Dashboard publishes (news, business, NEPSE, watchlist, investment rates, places) and runs:

```sh
python3 scripts/update_data.py public.json   # writes site/data.json
node scripts/check.mjs                       # should end with "Site check passed."
```

then commits to `main`, which publishes the site. The script keeps only public parts, keeps the Mentor section as it is, refuses to go backwards in time, and stops if a story is written to one person ("you", "your") so it can be reworded first. If anything fails, nothing is published.

To update by hand, run the same two commands with a fresh `public.json`, then commit and push.

### How the mentor's numbers work

Each business in `data.json` under `mentor.ideas` has four figures per unit (one hive, one tunnel, one kattha, one bird):

- `setup`: the one-off cost to build or buy it
- `first_cycle`: running costs until the first sale (a batch for chickens, a year for the others)
- `cost_year`: running costs for a year
- `profit`: profit a year in a cautious, expected and good case, each taken from a named study

The page works out how many units the visitor's budget covers, then multiplies. Every business lists its sources and explains its sums under "How these numbers are worked out".

**How solid are they?** In November 2026 the main figures for all five businesses were checked against the full papers (beekeeping: Chitwan 2026, 60 farms; bananas: Chitwan 2025, 135 farms; tunnel tomatoes: Kathmandu 2024, 150 farms; broilers: Rupandehi 2020 survey, 120 farms; carp ponds: Bara 2019 survey, 90 farms). Some figures still come from elsewhere and say so on the page: the price of a hive with bees, the broiler shed cost (Indian project models), the pond digging rate, and the cautious cases for bees and fish. Conversions from per hectare to per tunnel or per kattha, and the assumption of five chicken batches a year, are ours. Businesses without solid figures (dairy, goats, mushrooms, homestays) are listed without numbers.

## Hosting

The site is published with GitHub Pages at **https://saduanki9.github.io/Nepal-in-1/**

One-time setup, in the repo's settings on GitHub:

1. **Settings → General → Danger Zone → Change visibility → Public.** Free GitHub accounts can only publish Pages sites from public repos.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**

After that, every change to `site/` on `main` goes live by itself within a minute or two. The deploy runs the health check first and stops if it fails. To publish again by hand, open the **Actions** tab, pick **Deploy site** and tap **Run workflow**.

## Roadmap

1. **Grow the mentor:** add more businesses with solid Nepal figures, and recheck prices each year.
2. **Back up and move builds.** Export builds to a file and import them on another device.
3. **A custom domain,** such as a `.com.np` address, in place of the `github.io` one.
4. **Nepali language.** A नेपाली / English switch.
5. **More of Nepal:** weather and air quality by city, exchange rates, gold and silver prices, a festival and holiday calendar, a province-by-province view.
6. **Share cards.** A one-tap image of the day's NEPSE close or top story, for Facebook, Viber and X.

## Disclaimer

For general information only. Nothing here is investment, financial or legal advice. Projections are not promises; market investments can lose money.
