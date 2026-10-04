---
title: "Wallabag: Pocket Import Fails or Stops Partway"
slug: wallabag-pocket-import-failed
meta_description: "504 timeouts, only 300 of 3000 articles, or everything landing in Unread. Use the CLI importer and the Redis/RabbitMQ queue instead of the browser."
updated: October 2026
cluster: round 14 (tech) — wallabag/wallabag GitHub issues
competition: LOW
---

# Wallabag: Pocket Import Fails or Stops Partway

The browser-based import runs **synchronously inside a web request**, which is why it fails on any library of size. Every symptom below has the same underlying answer: move the import out of the web request.

Reported symptoms, all the same cause:

- 504 Gateway Timeout during `/import/pocket/callback`
- Cloudflare 524
- Only 100–300 items imported from thousands
- PHP segfault
- Different partial results on each retry, with duplicates accumulating

## 1. Use the CLI importer

```bash
# Docker
docker exec -it wallabag php bin/console wallabag:import \
  1 /path/to/pocket_export.json --importer=pocket --env=prod

# bare metal
php bin/console wallabag:import 1 ril_export.html --importer=pocket --env=prod
```

The `1` is the **user id**, not the username. Find it:

```bash
docker exec -it wallabag php bin/console doctrine:query:sql \
  "SELECT id, username FROM wallabag_user" --env=prod
```

The CLI has no web timeout and is the documented route for large imports. This is the fix — the rest of this article is about making it go through cleanly.

## 2. Enable asynchronous imports for large libraries

Wallabag can queue each article as a job, which is what you want for thousands of items:

```yaml
# app/config/parameters.yml
rabbitmq: false
redis: true
redis_scheme: tcp
redis_host: redis
redis_port: 6379
```

Then enable the Redis import in Wallabag's **internal settings** (Config → Internal settings → Import), and run a consumer per importer:

```bash
docker exec -d wallabag php bin/console rabbitmq:consumer -r 0 import_pocket --env=prod
# Redis variant:
docker exec -d wallabag php bin/console wallabag:import:redis-worker pocket -m 0 --env=prod
```

With a worker running, the import call returns immediately and articles are fetched in the background. Watch progress:

```bash
docker exec wallabag php bin/console doctrine:query:sql \
  "SELECT COUNT(*) FROM wallabag_entry WHERE user_id = 1" --env=prod
```

Without a worker, queued imports sit there forever and nothing appears — the most common mistake when switching to async.

## 3. Character encoding and date failures

```
Invalid datetime format
Incorrect string value: '\xF0\x9F...' for column 'title'
```

Both are database charset problems, not Pocket's fault. Wallabag needs **utf8mb4** throughout to store emoji and four-byte characters:

```sql
ALTER DATABASE wallabag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE wallabag_entry CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

and in the connection:

```yaml
database_charset: utf8mb4
```

A fresh Wallabag install sets this correctly; an instance upgraded from an old version may still be on `utf8`, and the import is where it finally bites. The `Invalid datetime format` variant comes from Pocket exporting a zero or missing timestamp — rare, and those items fail individually rather than stopping the run.

Use PostgreSQL if you have the choice; none of this applies there.

## 4. Everything lands in Unread

Documented behaviour: **archived Pocket items import as unread**, so a decade of read articles floods your unread list.

The import honours the archive flag in some versions and not others. Practical handling:

- Import, then bulk-archive everything older than your cutover date:

```bash
docker exec wallabag php bin/console doctrine:query:sql \
  "UPDATE wallabag_entry SET is_archived = 1 WHERE user_id = 1 AND created_at < '2026-01-01'" --env=prod
```

Back up first. Doing it in SQL is far faster than the UI for thousands of entries.

- Or import from the **JSON** export rather than the HTML one where your version supports it; the JSON carries the status field more reliably.

## 5. Duplicates from retries

Each retry re-imports what it managed last time, because the partial import left entries that the next run doesn't recognise as its own.

- Prefer the CLI, which completes, so you never retry.
- If you already have duplicates, find them before deleting:

```bash
docker exec wallabag php bin/console doctrine:query:sql \
  "SELECT url, COUNT(*) c FROM wallabag_entry WHERE user_id=1 GROUP BY url HAVING c > 1 LIMIT 20" --env=prod
```

## 6. Content not fetched

Articles imported with a title and no body means the fetch failed, separately from the import. Wallabag fetches each URL; sites that block it return nothing. That's expected for a proportion of a large archive, and it's why keeping the Pocket export file matters — it's your only record of what you had.

## What not to do

- **Don't import through the browser** for more than a few hundred items.
- **Don't retry a failed browser import.** You compound duplicates.
- **Don't enable async imports without starting a worker.** Nothing will ever appear.
- **Don't delete the Pocket export** until you've verified a sample of titles, dates and archive states.

## Prevention

| Habit | Why |
|---|---|
| CLI importer for anything large | No web timeout, completes |
| utf8mb4 (or PostgreSQL) before importing | Removes the encoding failures |
| Keep the export file | The only record if the fetch fails |
| Verify ten items across years and states | Catches date and archive problems early |

## FAQ

**Can I import from Instapaper or Readwise?**
Yes, with the matching `--importer=` value. Same timeout logic applies.

**Does it preserve tags?**
Pocket tags import as Wallabag tags in current versions.

**Will it fetch full text for everything?**
It tries. Expect a tail of failures from paywalled and bot-blocking sites.

**How do I move to another Wallabag instance later?**
Wallabag's own export (Config → Export) round-trips better than re-importing a Pocket file.
