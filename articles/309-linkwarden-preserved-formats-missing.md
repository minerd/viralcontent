---
title: "Linkwarden: Preserved Formats Missing (No Screenshot, No PDF, No Archive)"
slug: linkwarden-preserved-formats-missing
meta_description: "Links save but the screenshot, PDF and single-file archive never appear. The worker, Playwright's memory need, and the settings that gate each format."
updated: October 2026
cluster: round 13 (tech) — Linkwarden GitHub issues
competition: LOW
---

# Linkwarden: Preserved Formats Missing (No Screenshot, No PDF, No Archive)

Saving a link writes a database row immediately. The preserved formats — screenshot, PDF, single-file HTML, readable text — are produced afterwards by a **background worker running Playwright/Chromium**. When they never appear, that worker is failing, and there are four usual reasons.

## 1. Read the worker log

```bash
docker logs linkwarden --tail 100 | grep -iE 'archive|worker|playwright|chromium|error'
```

You're looking for lines about an archival run starting and either finishing or erroring. If there are none at all, the worker isn't running; if there are errors, the error names the cause.

## 2. Memory — the most common cause

Chromium needs real memory to render a page. On a 1–2 GB VPS or a small LXC container, the browser gets killed partway and the archive silently never completes.

```bash
dmesg -T | grep -iE 'oom|killed process' | tail
free -m
```

A `Killed process ... chrome` line is conclusive. Options:

- Give the host or container at least **2 GB**, preferably 4 with several links in flight.
- Add swap. 1–2 GB of swap turns an OOM kill into a slow archive, which is strictly better.
- Reduce concurrency so one page renders at a time.

In an LXC container (Proxmox), also check that the container isn't memory-limited well below the host's free RAM — the limit, not the host, is what Chromium sees.

## 3. `/dev/shm` too small

Chromium uses shared memory heavily. Docker's default `/dev/shm` is **64 MB**, which is not enough, and the failure mode is a crash mid-render rather than an obvious error.

```yaml
services:
  linkwarden:
    shm_size: '1gb'
```

Or, if you can't change compose:

```yaml
    volumes:
      - /dev/shm:/dev/shm
```

This one line fixes a surprising proportion of "archives sometimes work" reports.

## 4. The formats are disabled, per collection or globally

Linkwarden gates each format with a setting, and they're not all on by default in every version.

- **Settings → Preferences → Archive**: toggles for screenshot, PDF, single-file, readable, and the Wayback Machine link. If a format is off here, no amount of worker debugging will produce it.
- **Per-collection** settings can override. A link saved into a collection with archiving off produces nothing even though another collection works — which looks random until you notice the pattern.
- **`NEXT_PUBLIC_DISABLE_REGISTRATION`-style env vars** don't affect this, but `ARCHIVE_TAKE_COUNT` and the worker interval do. The worker runs on an interval; immediately after saving, "missing" is just "not yet".

Force a retry on one link from its detail view (**Refresh preserved formats**) rather than re-saving it.

## 5. Pages that will never archive

Some failures are correct:

- **Login-walled pages.** The worker has no session. You get the login page as your screenshot.
- **Sites blocking headless browsers.** Cloudflare's interstitial, in particular, archives as the challenge page.
- **Very large pages.** The render times out. The timeout is configurable, but a 200 MB single-page app is not going to produce a useful PDF.

For these, the browser extension's capture is the practical alternative, because it uses your real session.

## What not to do

- **Don't re-save the link to retry.** You get a duplicate with the same failing job. Use the refresh action on the existing link.
- **Don't delete the Postgres volume.** Links, collections and tags live there; archives are files. A database wipe loses everything and fixes nothing.
- **Don't run Linkwarden with no swap on a 1 GB box** and conclude archiving is broken. It's a hardware shortfall.
- **Don't expose the instance publicly without configuring the worker's egress** if you care — the worker fetches arbitrary URLs from your network, which is worth thinking about on a server that can reach internal services.

## Prevention

| Habit | Why |
|---|---|
| `shm_size: 1gb` in compose from day one | Removes the hardest-to-diagnose failure |
| 2 GB RAM minimum, plus swap | Chromium is the floor, not Linkwarden |
| Enable only the formats you use | Each one is a separate render; three formats is three times the work |
| Back up the database *and* the archive directory | They're useless separately |

## FAQ

**Which format is actually worth keeping?**
Single-file HTML, for readability years later. PDFs are big and screenshots lose text selection. Many people enable single-file plus readable and skip the rest.

**Can I archive to the Wayback Machine instead?**
There's a setting for submitting links to it, which is complementary, not a replacement — you don't control retention there.

**Archives work for some links and not others, with no pattern.**
Check `/dev/shm` first; intermittent-by-page-weight is its signature.

**Does it respect robots.txt?**
It fetches as a browser would. Sites that block headless agents will block it regardless.
