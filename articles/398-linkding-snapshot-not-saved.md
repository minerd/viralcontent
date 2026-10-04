---
title: "linkding: HTML Snapshots Not Being Saved"
slug: linkding-snapshot-not-saved
meta_description: "Bookmarks save and the archive doesn't attach. The image tag that enables snapshots, the SingleFile extension handshake, and bulk archiving."
updated: October 2026
cluster: round 14 (tech) — sissbruecker/linkding GitHub issues
competition: LOW
---

# linkding: HTML Snapshots Not Being Saved

Local HTML snapshots are **not available in every linkding image**, and they are **off by default** where they are. Both facts explain most of these reports.

## 1. You need the right image and the feature flag

```yaml
services:
  linkding:
    image: sissbruecker/linkding:latest-plus
    environment:
      - LD_ENABLE_SNAPSHOTS=True
    volumes:
      - ./data:/etc/linkding/data
```

- **`latest-plus`** is the variant that includes the headless browser needed for snapshots. The plain `latest` image does not, and the setting silently does nothing.
- **`LD_ENABLE_SNAPSHOTS=True`** must be set. On a bare-metal or non-Docker install the equivalent is in `data/env.sh`:

```bash
# /app/data/env.sh
export LD_ENABLE_SNAPSHOTS=True
```

then restart.

Confirm both:

```bash
docker inspect linkding --format '{{.Config.Image}}'
docker exec linkding sh -c 'echo $LD_ENABLE_SNAPSHOTS'
docker exec linkding sh -c 'which chromium chromium-browser 2>/dev/null; ls /root/.cache/ms-playwright 2>/dev/null'
```

No browser present means you're on the wrong image.

## 2. Resources

Snapshots render the page in a headless browser. That needs memory:

```bash
dmesg -T | grep -iE 'oom|killed process' | tail
free -m
```

- **2 GB minimum**, with swap. On a 512 MB VPS, snapshots will be killed mid-render while the rest of linkding works perfectly — which is exactly the "saves the bookmark, no snapshot" pattern.
- **`/dev/shm`** at Docker's 64 MB default is too small for Chromium:

```yaml
    shm_size: '512mb'
```

This one line resolves a lot of intermittent snapshot failures.

## 3. The SingleFile extension path

linkding can also accept snapshots pushed from the **SingleFile browser extension**, which is better for pages requiring a login because it captures what your browser sees.

The reported problem: **with both the SingleFile and linkding extensions configured, adding a bookmark doesn't reliably attach the snapshot.** The bookmark saves with a success message; the HTML file sometimes isn't there, and deleting and re-adding the bookmark a couple of times eventually works.

Practical handling:

- After adding a bookmark this way, **check that the snapshot attached** before closing the tab. The bookmark detail page shows its assets.
- If it didn't, use the bookmark's **"Create HTML snapshot"** action from linkding itself rather than re-adding.
- Keep both extensions current; the handshake between them has been the subject of fixes.

## 4. Bulk archiving existing bookmarks

Snapshots are created when a bookmark is added, not retroactively. A reported gap: **"refresh from website" on a list of bookmarks does not add snapshots.**

So a library imported from elsewhere has no snapshots, and there's no one-click backfill in the UI for every version. Options:

- Select bookmarks and use the bulk action for creating snapshots, where your version offers it
- Trigger per-bookmark from the detail view
- Use the API in a loop:

```bash
for id in $(curl -s -H "Authorization: Token $TOKEN" \
    'https://linkding.example.com/api/bookmarks/?limit=100' \
  | python3 -c 'import sys,json;print(" ".join(str(b["id"]) for b in json.load(sys.stdin)["results"]))'); do
  curl -s -X POST -H "Authorization: Token $TOKEN" \
    "https://linkding.example.com/api/bookmarks/$id/assets/" >/dev/null
  sleep 2
done
```

Rate-limit yourself; each snapshot is a full page render.

## 5. Internet Archive vs. local snapshots

Two separate features, and conflating them causes confusion:

- **`LD_ENABLE_SNAPSHOTS`** — local HTML files stored by you
- **Internet Archive integration** — linkding asks web.archive.org to archive the URL and stores the resulting link

A reported issue: with the Internet Archive option enabled, `web_archive_snapshot_url` stays **empty in the API** for all bookmarks. The Archive's save-page endpoint is rate-limited and frequently slow; a missing URL often means the request didn't complete rather than that linkding is broken. It also means you don't control retention there — local snapshots are the thing to rely on.

## 6. Pages that can't be snapshotted

- **Login-walled pages** — the server has no session. Use the SingleFile route.
- **Cloudflare interstitials** — you archive the challenge page.
- **Very heavy single-page apps** — the render times out before the content paints.

## What not to do

- **Don't expect snapshots from the plain `latest` image.** Check the tag first.
- **Don't run with 64 MB `/dev/shm`.** It produces exactly the intermittent failures you're debugging.
- **Don't rely on the Internet Archive integration as your archive.** You don't control it.
- **Don't bulk-snapshot a thousand bookmarks at once.** Each is a browser render; pace it.

## Prevention

| Habit | Why |
|---|---|
| `latest-plus` + `LD_ENABLE_SNAPSHOTS=True` + `shm_size: 512mb` | The three settings that make snapshots work at all |
| Verify the snapshot attached when adding via the extension | The handshake is the unreliable part |
| Back up `./data` including assets | Snapshots are files, not database rows |
| 2 GB RAM and swap | Chromium is the floor |

## FAQ

**How much disk do snapshots use?**
A single-file HTML archive is typically 1–5 MB. A thousand bookmarks is a few gigabytes.

**Can I search inside snapshots?**
linkding indexes bookmark metadata, not snapshot contents.

**Does it archive PDFs?**
It stores the file where it can fetch it; rendering a PDF page as HTML isn't the same thing.

**linkding or Linkwarden?**
linkding is lighter and simpler; Linkwarden does more formats and AI tagging with correspondingly more moving parts.
