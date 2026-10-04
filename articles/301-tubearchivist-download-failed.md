---
title: "TubeArchivist Downloads Failing? Cookies, Throttling and the ES Index"
slug: tubearchivist-download-failed
meta_description: "Downloads stuck in the queue, 'Sign in to confirm you're not a bot', or Elasticsearch refusing to start. The three distinct failures and their fixes."
updated: October 2026
cluster: round 13 (tech) — TubeArchivist GitHub issues
competition: LOW
---

# TubeArchivist Downloads Failing? Cookies, Throttling and the ES Index

Three unrelated problems present as "downloads don't work". Identify yours from the log line, because the fixes share nothing.

```bash
docker logs tubearchivist --tail 100
```

## Failure 1: "Sign in to confirm you're not a bot"

This is the dominant cause now and it comes from YouTube, not TubeArchivist. Datacentre IPs and unauthenticated requests get challenged.

The fix is a cookie file. In TubeArchivist: **Settings → Application → Cookie**, paste your exported `cookies.txt`, and enable **Use Cookie**. Then use the **Validate Cookie** button — it tells you immediately whether the cookie is accepted, which saves guessing.

Getting a cookie that actually works:

1. Export cookies in **Netscape format** from a browser logged into YouTube (a `cookies.txt` extension, or `yt-dlp --cookies-from-browser` on a desktop machine).
2. Export from a **private/incognito window**, then close that window **without logging out**. Cookies rotate; closing a normal session invalidates the cookie you just exported, which is why people's first attempt works for ten minutes and then dies.
3. Expect to refresh it periodically. A cookie that worked for weeks suddenly failing is normal, not a regression.

If you'd rather not attach your account, the alternative is routing through a residential IP. Note that a commercial VPN exit is usually *worse* than a bare datacentre IP for this check.

## Failure 2: downloads queue but never start

Check whether the queue item is actually `pending` and whether a download is in flight:

```bash
docker logs tubearchivist --tail 50 | grep -iE 'download|yt_dlp|throttl'
```

Common causes, in order:

- **`downloads` throttle set very low.** Settings → Downloads → *Download Speed Limit*. A limit of a few hundred KB/s with large 4K files looks like a stall.
- **The subscription's "Download Pending" was never triggered.** Adding a channel indexes it; it doesn't queue it. Use **Rescan Subscriptions** then **Start Download**.
- **Format string matches nothing.** A custom `format` like `bestvideo[height<=1080][vcodec^=av01]+bestaudio` silently matches zero formats on many videos. Test it outside the container:

```bash
yt-dlp -F 'https://www.youtube.com/watch?v=VIDEOID'
```

If your format selector returns "Requested format is not available", that's your answer. Add a fallback: `.../best`.

- **Disk full.** `df -h` on the volume behind `/youtube`. yt-dlp's partial-file errors are not obvious about this.

## Failure 3: Elasticsearch won't start, so nothing works

TubeArchivist depends on Elasticsearch; when ES is down, the UI is broken or empty rather than "downloads failing", but people report it the same way.

```bash
docker logs archivist-es --tail 50
```

Two near-universal causes:

**`max virtual memory areas vm.max_map_count [65530] is too low`**

```bash
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee /etc/sysctl.d/99-tubearchivist.conf
```

Without the second line it reverts on reboot — which is why ES "randomly" dies weeks later.

**`AccessDeniedException` / permission errors on `/usr/share/elasticsearch/data`**

The ES container runs as UID 1000. The bind-mounted data directory must be owned by it:

```bash
sudo chown -R 1000:0 /path/to/es/data
```

If you're on a NAS that can't set that ownership, use a Docker named volume for ES instead of a bind mount. This single point is responsible for a large share of failed first installs on Synology and Unraid.

## What not to do

- **Don't delete the ES volume to fix a download problem.** You lose your entire index — metadata, watch states, subscriptions — and downloads still fail.
- **Don't paste a cookie exported from a session you then logged out of.** It's already dead.
- **Don't run many parallel downloads to go faster.** Concurrency is what triggers the bot check; it's the fastest route to being blocked entirely.
- **Don't edit files directly in `/youtube`.** The index won't know, and TubeArchivist will show entries for files that no longer exist.

## Prevention

| Habit | Why |
|---|---|
| Set `vm.max_map_count` persistently on day one | Removes the most common "it broke after a reboot" failure |
| Re-validate the cookie monthly | Turns a hard failure into a two-minute chore |
| Keep a conservative rate limit and one worker | Steady and unblocked beats fast and challenged |
| Back up the ES index, not just the videos | Files are re-downloadable; watch state and subscriptions aren't |

## FAQ

**Will a VPN help with the bot check?**
Usually not — shared VPN exits are heavily flagged. A cookie is the reliable path.

**Do I need cookies for members-only or age-restricted videos?**
Yes, and the cookie must come from an account with the relevant access.

**Downloads work but videos don't appear in the UI.**
That's an indexing problem: check the ES connection and look for `refresh` errors in the TubeArchivist log.

**Can I migrate the index to a new host?**
Yes — stop everything, copy the ES data directory with ownership intact (`rsync -aAX`), and keep the same ES major version.
