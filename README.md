# Sustainability News Hub

A daily-updated news aggregator for sustainability, ESG, circular economy and responsible supply chain professionals.

**Live:** https://sustainthread.github.io/sustain-news/

Free, installable as an app on phone or desktop, no sign-up and no ads.

## What it does

A GitHub Actions job runs every morning at 06:00 UTC, pulls a tiered list of RSS feeds from established sustainability and ESG publishers, filters and de-duplicates articles against a keyword taxonomy (environmental action, ESG reporting, fashion sustainability, general sustainability), and writes the result to `news.json`. The front end reads that file and renders a searchable, filterable card view. A service worker caches the app shell so it keeps working offline, while news itself is fetched network-first so an installed copy never shows yesterday's headlines when the device is online.

## Stack

Static site on GitHub Pages: vanilla JavaScript with Bootstrap 5 for the interface, a Python fetcher (`fetch_news.py`) built on feedparser, and two scheduled GitHub Actions workflows, one for the daily news refresh and one to bump the service worker cache version weekly.

## Repository layout

| File | Purpose |
| --- | --- |
| `index.html` | Single-page front end: layout, styling, rendering and filtering |
| `fetch_news.py` | Feed collection, keyword classification and de-duplication |
| `news.json` | Generated article feed consumed by the front end |
| `sw.js` | Service worker: cache-first assets, network-first news |
| `manifest.json` | PWA install metadata |
| `.github/workflows/daily.yml` | Daily news refresh |
| `.github/workflows/deploy-pwa.yml` | Weekly cache version bump |

## Running locally

```bash
pip install -r requirements.txt
python fetch_news.py          # regenerates news.json
python -m http.server 8000    # then open http://localhost:8000
```

Service workers need a real origin, so use the local server rather than opening `index.html` from disk.

## Feedback

Topic suggestions and improvement ideas are welcome: open an issue on this repository.

---

Built and maintained by [Vishal Londhe](https://sustainthread.github.io/Vishal-londhe).
