# Nepal Dashboard

A personal dashboard for building in Nepal: key projects for a school and community in Kanchanpur, a daily news brief, business, NEPSE, investment planning, the economy, and national pride projects.

**Live version:** runs as a Claude artifact on claude.ai, where it saves your builds and refreshes its data every day.
**This repo:** the backup and version history of its code.

## What's inside

| Path | What it is |
|---|---|
| `dashboard/index.html` | The whole app: one HTML file with its styles and script inside |
| `dashboard/public.json` | A snapshot of the daily data (news, business, NEPSE, invest, places) |
| `scripts/check.mjs` | A quick health check for the two files above |
| `.github/workflows/check.yml` | Runs that check on GitHub every time the dashboard changes |
| `docs/slsa-generic-generator.yml` | A parked SLSA provenance workflow, not active (see below) |

## The eight tabs

1. **Key builds:** your projects on a board (Idea → Exploring → Planning → Building → Launched), with tasks, notes and a daily news signal
2. **Today in Nepal:** the morning news brief, with Sudurpashchim stories first
3. **Ideas:** opportunities from the day's news; add one to your builds with a tap
4. **Business:** indicators, company news and upcoming business events
5. **NEPSE:** index chart, sector moves, top gainers and losers, a fundamentals watchlist, IPOs
6. **Invest:** a growth calculator, a plan splitter (starts at Rs 5 crore) and places to watch for property
7. **Economy:** GDP paths to 2036, growth forecasts, the hydropower export tracker, a growth scorecard
8. **National projects:** progress on 25 big projects, with Sudurpashchim highlighted

## How it works

- **On claude.ai** the page uses Claude's shared database. Builds sit in the `builds` collection. The daily data sits in `feed/today`, `business/today`, `market/nepse`, `market/watchlist`, `invest/options`, `invest/places` and `invest/plan`. Claude's scheduled tasks refresh the data around 6:34 each morning and at 4 pm on NEPSE trading days.
- **Anywhere else** the page switches to *device mode*. It reads `public.json` for the data and saves builds only in that browser. To preview it locally:

  ```sh
  cd dashboard && python3 -m http.server 8000   # then open http://localhost:8000
  ```

Your builds and plan are **not** in this repo. They live only in the database on claude.ai.

## Making changes

1. Edit `dashboard/index.html`, or ask Claude to.
2. Run `node scripts/check.mjs`. It should end with "Dashboard check passed."
3. Commit and push. GitHub runs the same check.
4. Publish the updated file back to the artifact so the live version gets the change.

Keep the artifact and this repo in step. If you change the dashboard on claude.ai, save the new version here too.

## Growing it

Ideas for next steps, roughly smallest first:

- **Regular backups:** each time the dashboard changes on claude.ai, ask Claude to save it here, so every version is kept.
- **Back up your builds:** export the `builds` collection to a JSON file here now and then, in case it's ever lost.
- **Split the file:** once the app gets bigger, move the CSS and JavaScript into their own files so changes are easier to review.
- **A public site:** GitHub Pages can serve `dashboard/` as a website. It needs a public repo or a paid plan, and the data stays frozen unless a workflow refreshes `public.json`.
- **A downloadable app:** if you ever ship an installable version, turn on `docs/slsa-generic-generator.yml`. It signs your release files so people can check they're genuine. To use it, move it to `.github/workflows/`, put the release files in an `artifacts/` folder and update the generator version.
