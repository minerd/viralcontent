---
title: "Readarr Metadata Server Errors: The Project Is Retired — What to Do Now"
slug: readarr-metadata-server-down
meta_description: "Readarr can't add books, search returns nothing, logs show metadata server failures. Why it won't be fixed, and the two working paths forward."
updated: October 2026
cluster: round 13 (tech) — Readarr GitHub and the *arr Discord
competition: LOW
---

# Readarr Metadata Server Errors: The Project Is Retired — What to Do Now

If your Readarr suddenly can't add books, shows empty author search results, or fills its log with metadata lookup failures, stop troubleshooting your instance. The cause is almost certainly upstream and permanent.

Readarr was **retired by the *arr team**. The part that broke is its hosted metadata service: Readarr never queried a book database directly, it queried a proxy run by the project, which in turn sat on top of Goodreads data. When that proxy degrades, every instance in the world degrades at the same time, and no reinstall, container recreate, or database rebuild touches it.

## 1. Confirm it's the metadata service, not you

The signature in the log:

```
Readarr.Core.MetadataSource.BookInfo.BookInfoProxy|
Http request failed: [503:ServiceUnavailable]
[GET] at [https://api.bookinfo.club/v1/author/...]
```

Or `[429:TooManyRequests]`, or a timeout against the same host. Three checks that settle it in a minute:

```bash
# does the proxy answer at all?
curl -s -o /dev/null -w '%{http_code}\n' https://api.bookinfo.club/v1/

# is your container resolving DNS fine otherwise?
docker exec readarr curl -s -o /dev/null -w '%{http_code}\n' https://api.github.com
```

If GitHub answers 200 and the metadata host doesn't, your networking is fine. Importantly: **existing library items keep working.** Monitoring, searching your indexers, importing files — all of that is local. Only *adding new authors/books* and *refreshing metadata* go through the proxy.

That distinction matters because it tells you whether you need to act at all.

## 2. Reduce the damage on an existing instance

If your library is already populated and you mostly want it to keep grabbing new releases for authors you already track, you can keep running — but you must stop it hammering a dead service and corrupting its own state.

In **Settings → Profiles / Media Management**, and in the scheduled tasks:

- Turn off **"Refresh monitored authors"** on a schedule. Each run attempts a metadata fetch per author; against a failing proxy this does nothing useful and, worse, some versions mark items as removed when the lookup comes back empty.
- Avoid clicking **Refresh & Scan** on an author. A failed refresh can blank out book lists.
- **Back up the database now**, before any further refresh attempts:

```bash
docker stop readarr
cp -a /path/to/readarr/config /path/to/readarr/config.backup-$(date +%F)
docker start readarr
```

That backup is the only thing standing between you and re-entering a library by hand.

## 3. Pick a path forward

There are two real options, and the right one depends on whether you care about *audiobooks*, *ebooks*, or both.

**Option A — a community fork.** Forks of Readarr exist that replace the hosted proxy with a different metadata source (commonly Open Library or Hardcover). The practical test for any fork: does it run its own metadata endpoint, or point at a new hosted one? A fork pointed at another single hosted service has the same failure mode you're in now, just later.

Before migrating, note your root folders, quality profiles, and indexer settings. The config format is close enough that most forks import an existing database, but take the backup from step 2 first.

**Option B — change tools.** For ebooks, **Calibre-Web (with the automated-import add-on)** plus manual or script-driven acquisition covers most of what people actually used Readarr for: a library, metadata, and format conversion. For audiobooks, **Audiobookshelf** handles the library and metadata side and has its own providers, so you're not dependent on one proxy.

Neither option reproduces Readarr's "monitor an author, auto-grab new releases" loop exactly. That loop is what the metadata proxy enabled, and it's the part that's genuinely gone.

## What not to do

- **Don't rebuild the database to fix it.** `readarr.db` corruption produces different errors. Deleting it loses your library and the metadata service still won't answer.
- **Don't recreate the container, change DNS, or add a VPN exit.** A 503 from the upstream is the same from every IP.
- **Don't run a mass refresh hoping it'll catch a good window.** That's the action most likely to wipe book lists.
- **Don't open a GitHub issue.** The repository is archived; nobody is triaging.

## Prevention

| Habit | Why |
|---|---|
| Prefer tools with pluggable metadata sources | A single hosted proxy is a single point of failure for the whole product |
| Keep config backups on a schedule | Makes a retirement an inconvenience rather than a data loss |
| Keep file naming meaningful on disk | Any replacement tool can rebuild a library from well-named files; none can rebuild it from `book.epub` |
| Check a project's activity before adopting | Last commit date and open-issue response time predict this failure |

## FAQ

**Will the metadata service come back?**
Treat it as gone. Even brief recoveries aren't something to build a library workflow on.

**Can I point Readarr at a different metadata URL?**
Not in the official builds — the endpoint is compiled in. That's precisely what the forks change.

**My existing authors still get new books. Why?**
Because release monitoring uses your indexers, not the metadata proxy. Only lookups and refreshes break.

**Is Lidarr affected?**
Lidarr has its own metadata proxy and a separate status. Same architectural risk, different service.
