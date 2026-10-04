---
title: "Jellystat Showing No Data"
slug: jellystat-no-data
meta_description: "Jellystat connects to Jellyfin and the dashboard stays empty. The webhook plugin it needs, and why importing Playback Reporting data does nothing."
updated: October 2026
cluster: round 14 (tech) — CyferShepard/Jellystat GitHub issues
competition: LOW
---

# Jellystat Showing No Data

Jellystat records activity **as it happens**. It is not a reader of Jellyfin's own statistics, which means two things:

1. It only knows about playback that occurred while it was running and connected
2. The connection that matters for live data is a **webhook from Jellyfin**, not the API key alone

Those two facts explain nearly every empty dashboard.

## 1. The API key gets you the library; the webhook gets you activity

```yaml
services:
  jellystat:
    image: cyfershepard/jellystat:latest
    environment:
      POSTGRES_USER: jellystat
      POSTGRES_PASSWORD: secret
      POSTGRES_IP: jellystat-db
      POSTGRES_PORT: 5432
      JWT_SECRET: a-long-random-string
    ports:
      - "3000:3000"
    volumes:
      - ./backup:/app/backend/backup-data
```

In Jellystat's settings you give the Jellyfin URL and an API key. That populates libraries and item metadata. But for sessions:

**Jellyfin → Dashboard → Plugins → Catalogue → install *Webhook*.** Then add a webhook:

- **URL:** `http://jellystat:3000/proxy/webhook` (adjust to how Jellystat is reachable from Jellyfin)
- **Notification types:** Playback Start, Playback Progress, Playback Stop
- **Item types:** Movies, Episodes, Audio as needed
- **Template:** the generic/handlebars payload Jellystat documents

Without this plugin configured, Jellystat installs cleanly, connects to Jellyfin, shows your libraries, and reports **zero activity** even while something is playing. That is the single most common cause.

Confirm the webhook is firing:

```bash
docker logs jellystat --tail 50 | grep -iE 'webhook|session|playback'
docker logs jellyfin --tail 50 | grep -i webhook
```

Note the direction: **Jellyfin must be able to reach Jellystat.** If Jellystat is on a different host or network, use an address Jellyfin can resolve — not `localhost`.

## 2. "Import Playback Reporting Plugin Data" does nothing

A well-reported behaviour: clicking **Import Playback Reporting Plugin Data** completes with no error and no data appears, even when the Playback Reporting plugin has months of history.

What's going on, and what to do:

- The import expects a specific schema from the Playback Reporting plugin's database, and version differences between the plugin and Jellystat break the mapping silently.
- TV show activity specifically has failed to import while movies worked, in several reports.

Practical options:

- **Check the import's log output** rather than the UI result:

```bash
docker logs jellystat --tail 200 | grep -iE 'import|playback_reporting|error'
```

- **Export from Playback Reporting manually** (its plugin page offers a CSV/TSV export) and import that, where your Jellystat version supports a file import.
- **Accept the gap.** Jellystat from today forward is the realistic position for most people; historical import is the fragile part of the product.

Don't repeatedly re-run the import — it can create partial duplicates.

## 3. Database connection

```bash
docker logs jellystat --tail 50 | grep -iE 'postgres|database|ECONNREFUSED'
```

- `POSTGRES_IP` must be the **service name or IP**, not `localhost`.
- The Postgres container must be ready before Jellystat starts; without a healthcheck you get an intermittent empty dashboard on boot:

```yaml
    depends_on:
      jellystat-db:
        condition: service_healthy

  jellystat-db:
    image: postgres:16
    environment:
      POSTGRES_DB: jellystat
      POSTGRES_USER: jellystat
      POSTGRES_PASSWORD: secret
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jellystat"]
      interval: 10s
    volumes:
      - ./pgdata:/var/lib/postgresql/data
```

- **`JWT_SECRET` must be set and stable.** Changing it invalidates sessions; leaving it unset fails at login.

## 4. Libraries empty as well as activity

That points at the API key or the Jellyfin URL:

```bash
docker exec jellystat sh -c \
  "wget -qO- 'http://jellyfin:8096/System/Info?api_key=YOUR_KEY' | head -c 200"
```

- The key must come from **Jellyfin → Dashboard → API Keys**.
- The URL needs the scheme and port, no trailing slash.
- Behind a reverse proxy with forward-auth, Jellystat's requests get a login page. Use the internal address.

## 5. Activity appears then disappears

- **Jellystat's data retention / sync tasks.** It runs periodic syncs; a failing sync can prune items it can no longer resolve.
- **Library item IDs changed** — a Jellyfin library removed and re-added gives everything new IDs, and old activity no longer maps to an item. It's still in the database but shows as unknown.

Back up before any Jellyfin library surgery:

```bash
# Jellystat has a backup action in Settings, writing to the mounted backup dir
ls -la ./backup/
```

## What not to do

- **Don't expect data without the Webhook plugin.** The API key alone gives you a library browser.
- **Don't re-run the Playback Reporting import repeatedly.** Partial duplicates are harder to clean than a missing history.
- **Don't point Jellyfin's webhook at a URL only you can reach.** The server makes that request, not your browser.
- **Don't change `JWT_SECRET` casually.** Everyone gets logged out.

## Prevention

| Habit | Why |
|---|---|
| Configure the Webhook plugin as step one | Without it there is no activity data at all |
| Postgres healthcheck and `depends_on` | Removes the boot-race empty dashboard |
| Scheduled Jellystat backups to a mounted volume | Watch history is the irreplaceable part |
| Avoid removing and re-adding Jellyfin libraries | It orphans historical activity |

## FAQ

**Jellystat or Tautulli?**
Tautulli is Plex-only. Jellystat is the Jellyfin equivalent and is younger — expect rougher edges, especially around imports.

**Does it slow Jellyfin down?**
The webhook adds negligible load. The library sync is periodic and light.

**Can several Jellyfin servers feed one Jellystat?**
One server per instance in current versions.

**No data for music playback.**
Audio item types must be selected in the webhook's configuration; they're often left off by default.
