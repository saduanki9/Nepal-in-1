# Nepal in 1

**All of Nepal in one place:** news, the stock market, business, investment options, the economy and national projects, on one fast page that works on any phone.

Nepal in 1 is a public website, kept separate from any personal dashboard. Every story and figure links to its source.

## What's on it

| Tab | What you get |
|---|---|
| **Start here** | The front page: one question (how much can you put in?), the three best-fitting businesses with money to start and profit a month, and links to the rest |
| **Today in Nepal** | The day's key stories from across the country, filterable by topic, each with why it matters |
| **My builds** | A personal project board for each visitor: add a build, move it from Idea to Launched, track tasks, notes and a target month |
| **Mentor** | Seven businesses with published Nepal cost and profit studies (beekeeping, bananas, tunnel tomatoes, broilers, carp ponds, ginger, goats). Each opens at the smallest size the studies support, with the money it needs to start, profit a month, payback, first steps and what to watch out for. Visitors can enter any budget (optional) to size them to their money. A new Mentor's pick every Sunday. Below them: a growth table and sector guides for every part of Nepal's economy, refreshed weekly One tap adds a business to My builds with its first steps as tasks |
| **Business** | Business opportunities open now (loans, subsidies, grants, training, tenders, trade fairs, share issues, each with its deadline and source), key indicators, company news and upcoming business dates. The Start page shows the three closing soonest |
| **NEPSE** | Index chart (1M / 3M / all), sector moves, top gainers, losers and most traded, a fundamentals watchlist for banks, IPOs and share issues |
| **Invest** | A calculator comparing fixed deposits, savings bonds, NEPSE, gold and land: lump sum or monthly, low / expected / high, after tax and inflation; plus places to watch for property |
| **Economy** | GDP paths to 2036, IMF and ADB forecasts, what the economy is made of, hydropower export progress, a growth scorecard |
| **National projects** | Progress, cost and status of 25 national pride and major projects, by sector |

On phones and tablets, where the tab row doesn't fit, a **Menu** button stays on screen and lists every feature. The Start page also lists them all under "Everything on Nepal in 1".

**Made for phones.** Tiles sit two to a row, buttons and "show more" rows are sized for thumbs, long pages have a Back to top button, and the Menu has a Share button (the phone's own share sheet, or a copied link). The site can be kept on the home screen like an app (`site/manifest.webmanifest` and the `icon-*.png` files). The browser check fails if a control is too small to tap or a long page has no way back to the top.

Light and dark mode follow the device setting.

**Visitor counting:** [GoatCounter](https://www.goatcounter.com) counts visits and tab views anonymously, with no cookies and no names. The numbers are at https://nepalin1.goatcounter.com (sign in with the owner's account).

**Where builds are saved:** only in the visitor's own browser, on that device. The site has no accounts and no server, so nobody else can see them, they don't follow the visitor to another device, and clearing the browser's data removes them. The calculator remembers its inputs the same way.

## How it's built

No framework and no build step: just two files.

| Path | What it is |
|---|---|
| `site/index.html` | The whole site: layout, styles and script in one file |
| `site/data.json` | The daily data: news, business, NEPSE, investment rates, places |
| `site/mentor.json` | The Mentor: businesses, growth table and sector guides (updated separately, so weekly suggestions never clash with the daily data) |
| `scripts/check.mjs` | Health check: valid data, every tab wired up, script has no syntax errors |
| `scripts/browser-check.mjs` | Opens the site in a real browser at small-phone, phone, tablet and desktop size and checks every feature can be reached and shows content |
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

The data updates itself once a day, at about 4:47 pm Nepal time, after the NEPSE close. A scheduled Claude task researches the day's news, business, NEPSE, watchlist prices and investment rates from public sources (every item keeps its link), writes them to a file and runs:

```sh
python3 scripts/update_data.py today.json   # writes site/data.json
node scripts/check.mjs                      # should end with "Site check passed."
```

then commits to `main`, which publishes the site. The script keeps only public parts, never touches the Mentor (`site/mentor.json`), refuses to go backwards in time, and stops if a story is written to one person ("you", "your") so it can be reworded first. If anything fails, nothing is published and the site keeps its previous data.

Two weekly tasks keep the slower-moving parts fresh:

| When (Nepal time) | Task | Publishes |
|---|---|---|
| Saturday, 9:13 am | **Invest refresh:** fixed deposit rates, savings bond issues, inflation, NEPSE growth, gold, land and rent figures, tax changes and places to watch | Straight to `main`, like the daily update |
| Sunday, 10:23 am | **Mentor refresh:** newer official figures for every growth row and sector guide, plus a new business or sector guide when a solid source exists | To the branch `mentor-weekly`; it goes live only after it is reviewed and merged |

The tasks are spaced out so no two run close together.

To update by hand, run the same two commands with a fresh file in the same shape, then commit and push.

### How the mentor's numbers work

Each business in `site/mentor.json` under `ideas` has four figures per unit (one hive, one tunnel, one kattha, one bird):

- `setup`: the one-off cost to build or buy it
- `first_cycle`: running costs until the first sale (a batch for chickens, a year for the others)
- `cost_year`: running costs for a year
- `profit`: profit a year in a cautious, expected and good case, each taken from a named study

The page works out how many units the visitor's budget covers, then multiplies. Every business lists its sources and explains its sums under "How these numbers are worked out".

**How solid are they?** The main figures for every business were checked against the full papers in November 2026: beekeeping (Chitwan 2026, 60 farms), bananas (Chitwan 2025, 135 farms), tunnel tomatoes (Kathmandu 2024, 150 farms), broilers (Rupandehi, 2020 survey, 120 farms), carp ponds (Bara, 2019 survey, 90 farms), ginger (Surkhet 2026, 100 growers) and goats (Banke, 2025 survey, 95 households). Some figures come from elsewhere and say so on the page: the price of a hive with bees, the broiler shed cost (Indian project models), the pond digging rate, and the cautious cases for bees and fish. Conversions from per hectare to per tunnel or per kattha, and the assumption of five chicken batches a year, are ours. Ginger and goats rest on one study each, so they show no range and can't be the Mentor's pick. Looked at and left without numbers: dairy, large cardamom, mushrooms and homestays (thin or dated figures), cauliflower and cucumber (studies whose sales don't match their own yield and price) and potato (the only recent study covers remote Mustang).

**Budget:** there is no default budget. Each business is shown at its starting size (from about Rs 22,200 for 2 ropani of ginger), so anyone can see what it takes. A visitor's own budget, if entered, sizes every business to it and is remembered only in their browser.

**Mentor's pick of the week** rotates through all the businesses in order, changing each Sunday (Nepal time). It is worked out in the page from the date, so it needs no job or data update, and any business added to `ideas` in `site/mentor.json` joins the rotation.

**Adding a business:** add an entry to `ideas` in `site/mentor.json` with figures from a Nepal study you have read in full, then run `node scripts/check.mjs`. The weekly rotation picks it up by itself.

### Where the growth is

A compact table on the Mentor ranks sectors as Strong, Moderate or Careful by what the latest official figures show: remittances, IT service exports, electricity exports, the trade gap, school numbers, tourist arrivals, growth, EV imports, cooperative savings and NEPSE's year. Each row has one figure with its source, ideas to explore, and a link to the sector guide. It gives no profit estimates. Data lives in `growth` in `site/mentor.json`; `scripts/check.mjs` checks every row has a level, a figure and a source.

### Sector guides

Below the sized businesses, the Mentor has 14 sector guides covering business across Nepal: farming, import and export, retail and wholesale, IT and online services, tourism, small manufacturing and food processing, construction and real estate, transport, education, health and pharmacy, energy, finance and cooperatives, investing in shares, and media, film and creative work. The weekly Mentor refresh updates their figures and can add a guide. Each gives the key public numbers with sources, the first steps (registrations and licences), and what to watch out for. They give **no profit estimate**, because profit depends on the exact product, place and owner. Data lives in `sectors` in `site/mentor.json`; `scripts/check.mjs` checks every guide has first steps and that every number has a source. Registration details summarised from advisers' guides are labelled as such on the page.

## Hosting

The site is published with GitHub Pages at **https://saduanki9.github.io/Nepal-in-1/**

One-time setup, in the repo's settings on GitHub:

1. **Settings → General → Danger Zone → Change visibility → Public.** Free GitHub accounts can only publish Pages sites from public repos.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**

After that, every change to `site/` on `main` goes live by itself within a minute or two. Before publishing, the deploy runs two checks and stops if either fails, so the previous version stays live:

1. **Health check** (`scripts/check.mjs`): valid data, every tab wired up and listed in the Menu, no script errors.
2. **Browser check** (`scripts/browser-check.mjs`): at four screen sizes, every feature must open from the Menu, from its tab, from a direct link and from the Start page, show content, and not scroll sideways.

**Visitors always get the newest version.** The deploy stamps a version into the page and writes `version.json`. If a phone is holding an older cached copy, the page reloads itself once when opened; if a new version is published while the page is open, it offers a "Refresh" button. To publish again by hand, open the **Actions** tab, pick **Deploy site** and tap **Run workflow**.

## Roadmap

1. **Grow the mentor:** add more businesses with solid Nepal figures, and recheck prices each year.
2. **Back up and move builds.** Export builds to a file and import them on another device.
3. **A custom domain,** such as a `.com.np` address, in place of the `github.io` one.
4. **Nepali language.** A नेपाली / English switch.
5. **More of Nepal:** weather and air quality by city, exchange rates, gold and silver prices, a festival and holiday calendar, a province-by-province view.
6. **Share cards.** A one-tap image of the day's NEPSE close or top story, for Facebook, Viber and X.

## Disclaimer

For general information only. Nothing here is investment, financial or legal advice. Projections are not promises; market investments can lose money.
