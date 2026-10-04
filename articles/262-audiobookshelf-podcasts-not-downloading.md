---
title: "Audiobookshelf Not Downloading New Podcast Episodes? Check the Schedule Tab"
slug: audiobookshelf-podcasts-not-downloading
meta_description: "Auto-download is per-podcast, not global, and it has been reported silently switching off. Where the setting lives, the OPML import gap, and how to verify the cron."
updated: October 2026
cluster: round 12 (tech) — Audiobookshelf GitHub issues only
competition: LOW
---

# Audiobookshelf Not Downloading New Podcast Episodes? Check the Schedule Tab

Auto-download in Audiobookshelf is **per podcast**, configured in that podcast's own **Schedule** tab. It is not a global setting, and nothing downloads automatically when you first add a podcast.

That alone explains most reports. The rest are worth knowing.

## 1. Set it per podcast

For each podcast: open it → **Settings → Schedule tab** → enable automatic episode downloads and choose the check interval (a cron expression).

Things to verify there:
- **Auto-download enabled** (per podcast)
- **Max episodes to keep** — set to 1 and you'll wonder where everything went
- The **cron schedule** actually matches what you intended
- **Max new episodes** per check, if your podcast posts in bursts

## 2. It turns itself off

A documented bug: the **automatic download setting occasionally gets disabled** without the user touching it. If downloads stopped for every podcast at once, re-check the toggles before investigating anything else — and check again after updates.

Keep a note of which podcasts should be on, because once you have thirty you won't remember.

## 3. OPML imports don't get scheduled

Also reported: podcasts created by **OPML import** aren't scheduled for auto-download even when the toggle appeared checked during import.

After any bulk import, go through each new podcast and set the schedule manually. Annoying, but it's a two-minute job versus weeks of silence.

## 4. Verify the server is checking at all

```bash
docker compose logs -f audiobookshelf | grep -i -e podcast -e episode -e cron
```

You want to see the scheduled check fire. If nothing appears at the expected time:
- **Server timezone** — set `TZ` on the container, or your 3am cron runs at a surprising hour
- Container **restarted** before the scheduled time, every time (a nightly `docker compose up -d` from a script resets timers)
- The podcast's **feed URL** is dead or redirecting; check the feed in a browser and update it
- The feed requires a **user agent** or auth it isn't getting (private/premium feeds)

## 5. Episodes found but not downloaded

Different failure. Use the podcast's **manual search**: if episodes are listed but downloading fails:

- **Disk space** on the library volume
- **Permissions** — match PUID/PGID to the library owner, and confirm the container can write into that podcast's folder
- **Episode already exists** by filename — ABS skips duplicates, and a rename upstream can look like a failure
- The CDN returns a **redirect** ABS can't follow, or requires HTTPS with a certificate the container doesn't trust (`ca-certificates` missing in a slim image)

## 6. After an update

- **Pin the image tag**; this feature has had regressions across several versions
- Check the **GitHub issues** for your version plus "auto download"
- After updating, spot-check one podcast's Schedule tab — that's where the silent reset shows up

## Prevention

1. **Set the schedule when you add the podcast**, not later
2. **Audit the toggles** after every update — it takes a minute
3. Set **`TZ`** on the container
4. Keep **max episodes** values deliberate, and write down why
5. Monitor **disk space**; podcasts grow quietly

## FAQ

**Why didn't anything download when I added the podcast?**
By design — no episodes download on creation. Configure the Schedule tab and/or download the backlog manually.

**Everything stopped at once. Why?**
Most likely the auto-download setting was reset, or the container's timezone/restart pattern means the cron never fires.

**Do OPML-imported podcasts auto-download?**
Reportedly not — set each one's schedule after import.

**Episodes appear in search but won't download.**
Disk space, permissions, or the feed's CDN. Check the server log during a manual download.
