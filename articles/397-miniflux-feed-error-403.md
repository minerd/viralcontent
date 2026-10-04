---
title: "Miniflux: Feed Error 403 or Unable to Fetch"
slug: miniflux-feed-error-403
meta_description: "One feed fails while the rest work. User agents, Cloudflare, timeouts, and the database authentication error people mistake for a feed problem."
updated: October 2026
cluster: round 14 (tech) — miniflux/v2 GitHub issues
competition: LOW
---

# Miniflux: Feed Error 403 or Unable to Fetch

Two completely different things produce "unable to fetch" in Miniflux. Separate them first:

- **One or a few feeds failing** → the remote site is refusing Miniflux (sections 1–3)
- **Everything failing, or errors mentioning `pq:` / `store:`** → your database (section 4)

```bash
docker logs miniflux --tail 60
```

## 1. 403 Forbidden

The site is blocking the request, not failing. Reddit, Indeed, several news sites and anything behind Cloudflare's bot protection do this to default HTTP clients.

Miniflux lets you set a user agent **per feed**:

```
Feed → Edit → User Agent
```

A browser-like string is usually enough:

```
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36
```

Test from the container, which is where the request actually comes from:

```bash
docker exec miniflux sh -c "wget -S -O /dev/null --user-agent='Mozilla/5.0' 'https://example.com/feed.xml'" 2>&1 | head -20
```

Other per-feed options for the same problem:

- **Cookies** field, for feeds that need a session
- **Basic auth** username/password, for protected feeds
- **"Fetch original content"** off — enabling it makes a second request to each article's URL, doubling the chances of being blocked

If a 403 persists with a browser user agent, the site is fingerprinting more than the UA (TLS fingerprint, header order) and no Miniflux setting will get past it. A third-party RSS proxy or RSS-Bridge is the practical route for those.

## 2. Timeouts

```
context deadline exceeded (Client.Timeout exceeded while awaiting headers)
```

The site is slow or the first byte never arrives.

```yaml
environment:
  HTTP_CLIENT_TIMEOUT: 60
  POLLING_FREQUENCY: 60
  BATCH_SIZE: 20
```

`HTTP_CLIENT_TIMEOUT` defaults to 20 seconds. Raising it to 60 fixes genuinely slow feeds and costs nothing except a slower refresh cycle when a feed is down.

Also check the container's own egress:

```bash
docker exec miniflux sh -c 'wget -qO- https://example.com/feed.xml | head -c 200'
docker exec miniflux sh -c 'nslookup example.com'
```

DNS failing inside the container while working on the host is a Docker DNS problem, not a feed one — and it affects everything, so it belongs in section 4's category.

## 3. 503 and rate limiting

A 503 usually means the origin is overloaded or deliberately throttling. Miniflux retries on its own schedule; the useful lever is to poll that feed less often:

```
Feed → Edit → "Ignore HTTP cache" off
```

Leaving HTTP caching **on** is important: Miniflux sends `If-Modified-Since` and `ETag`, and a well-behaved site returns 304 with no body. Turning that off multiplies your request volume and invites rate limiting. Only disable it for a feed whose server mishandles conditional requests.

For a site that's permanently rate-limiting you, increase `POLLING_FREQUENCY` globally or accept the errors — a feed updating hourly doesn't need a 15-minute poll.

## 4. The errors that aren't about feeds

```
store: unable to fetch feed counts: pq: password authentication failed for user "miniflux"
```

This is **PostgreSQL**, not a feed. It appears in the UI as a feed error and sends people hunting the wrong thing.

```yaml
services:
  miniflux:
    environment:
      DATABASE_URL: postgres://miniflux:secret@db/miniflux?sslmode=disable
      RUN_MIGRATIONS: 1
      CREATE_ADMIN: 1
      ADMIN_USERNAME: admin
      ADMIN_PASSWORD: changeme
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: miniflux
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: miniflux
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "miniflux"]
      interval: 10s
    volumes:
      - ./pgdata:/var/lib/postgresql/data
```

Causes of that specific error:

- **Password mismatch** between `DATABASE_URL` and `POSTGRES_PASSWORD`. Changing `POSTGRES_PASSWORD` after the volume exists does **not** change the database's password — Postgres only applies it on first initialisation. Either change it with `ALTER USER` or start from a fresh volume.
- **`sslmode`** — Postgres configured to require SSL with `sslmode=disable` in the URL, or vice versa.
- **No healthcheck ordering**, so Miniflux starts before Postgres is accepting connections. The `depends_on` with `condition: service_healthy` above fixes the intermittent-at-boot version of this.

## 5. Feed works in a browser, fails in Miniflux

Almost always one of:

- The feed URL requires a referer or a cookie your browser has
- Geo-blocking, and your server is in a different country
- The browser follows a redirect chain Miniflux doesn't (a `meta refresh`, which is HTML, not HTTP)

Find the real feed URL rather than the page URL — Miniflux's discovery finds it when you add the site, but a hand-entered URL may point at a redirect.

## What not to do

- **Don't disable HTTP caching globally.** You'll get rate-limited everywhere.
- **Don't change `POSTGRES_PASSWORD` on an existing volume** and expect it to take effect.
- **Don't set a 5-minute polling frequency** on a hundred feeds. You're the load.
- **Don't treat `pq:` errors as feed problems.** They're the database.

## Prevention

| Habit | Why |
|---|---|
| `HTTP_CLIENT_TIMEOUT: 60` | Covers slow origins with no downside |
| Per-feed user agent for known-blocking sites | Targeted, doesn't affect the rest |
| Postgres healthcheck with `depends_on` | Removes startup-race errors |
| HTTP caching left on | Fewer requests, fewer blocks |

## FAQ

**Can Miniflux scrape full articles?**
Yes, "fetch original content" per feed, with optional CSS rules for the content area. It increases request volume.

**Does it support Fever or Google Reader APIs?**
Both, for third-party reader apps. Enable in settings and use an API password.

**A feed shows duplicate entries.**
The site changes item GUIDs on edit. There's a per-feed option to use the URL as the identifier instead.

**How do I bulk-fix failing feeds?**
The feeds list can be filtered by error state; from there you can edit or remove them individually. There's no bulk user-agent setting, so for a site-wide block it's one at a time.
