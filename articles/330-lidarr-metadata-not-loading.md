---
title: "Lidarr Can't Find Artists: Metadata Server and Indexer Failures"
slug: lidarr-metadata-not-loading
meta_description: "Artist search returns nothing, imports fail on unknown albums, or everything times out. Separating the metadata proxy from your indexers."
updated: October 2026
cluster: round 13 (tech) — Lidarr GitHub issues and *arr forums
competition: LOW
---

# Lidarr Can't Find Artists: Metadata Server and Indexer Failures

Lidarr has two external dependencies that fail independently, and the error messages don't distinguish them well:

- **The metadata proxy** (`api.lidarr.audio`, backed by MusicBrainz) — needed to *add* and *refresh* artists
- **Your indexers** — needed to *find releases*

Searching for an artist and getting nothing is the first. Finding the artist but never grabbing anything is the second.

## 1. Metadata: confirm the proxy

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://api.lidarr.audio/api/v0.4/search?type=artist\&query=radiohead
```

In the log:

```
Lidarr.Core.MetadataSource.SkyHook.SkyHookProxy|
Http request failed: [503:ServiceUnavailable]
```

A 503, 429 or timeout here is upstream. It happens, and it affects everyone at once. Things that *aren't* the cause and aren't worth trying: reinstalling, recreating the container, clearing the database.

What you can do:

- **Wait and retry.** These outages are usually hours, not days.
- **Turn off scheduled refreshes while it's down.** Settings → general tasks: a failing "Refresh Artist" run can mark albums as missing or strip metadata. This is the one real risk during an outage, and it's worth acting on:

```
Settings → Media Management → uncheck automatic metadata refresh
```

- **Check it's not your DNS.** A container that can't resolve anything looks identical:

```bash
docker exec lidarr curl -s -o /dev/null -w '%{http_code}\n' https://api.github.com
```

If GitHub answers and the metadata host doesn't, it's upstream. If neither answers, fix your container's DNS.

One durable note: `api.lidarr.audio` is a single hosted proxy, the same architecture that ended Readarr. Keeping your library well-organised on disk — proper `Artist/Album/Track` naming with embedded tags — means any future tool can rebuild from the files.

## 2. Artist exists in MusicBrainz but Lidarr can't find it

The proxy caches MusicBrainz. A newly created MusicBrainz artist can take time to appear, and some entity types never do.

- Search by **MusicBrainz ID** rather than name: paste `mbid:` followed by the ID into Lidarr's search.
- Artists with unusual types (a "various artists" compilation credit, a DJ alias) may not be modelled the way you expect.
- If the artist genuinely doesn't exist in MusicBrainz, add it there. That's the actual data source; Lidarr is downstream.

## 3. Indexers: releases never found

Separate problem, separate test. **Settings → Indexers → Test** on each one.

Specific Lidarr issues:

- **Categories.** A Usenet or torrent indexer needs the *audio* categories selected (3000-series for Newznab). An indexer configured with video categories returns nothing for music and tests fine.
- **Quality profile too narrow.** A profile allowing only FLAC with a minimum bitrate excludes most of what's available. Check **Settings → Profiles**: the profile must allow something that exists.
- **Release profiles / "must not contain" terms** copied from a Sonarr config will reject music releases wholesale.
- **Prowlarr sync.** If indexers come from Prowlarr, confirm the sync pushed them with the right categories; a synced indexer with no music categories is the most common silent failure in this chain.

Then use the interactive search on one album: it shows every release found and, crucially, *why* each was rejected. That rejection list is the fastest diagnostic in the whole *arr suite and most people never open it.

## 4. Imports failing

- **"Unknown album" / "not a valid release"** — the downloaded files' tags don't match what Lidarr expects for that album. Lidarr matches on track count, duration and tags. A release with a bonus track or a different edition won't match the chosen album.
  - Fix: use **Manual Import** and map it explicitly, or change the album's monitored release to the edition you actually downloaded (album page → the release selector).
- **Permissions.** The classic *arr problem: the download client writes as one user, Lidarr reads as another.

```bash
docker exec lidarr ls -ln /downloads | head
docker exec lidarr id
```

Standardise on one PUID/PGID across the download client and every *arr.

- **Path mismatch.** The download client reports `/data/complete/...` and Lidarr looks at `/downloads/complete/...`. The paths must be identical *inside* both containers. This single convention — mount the same host path at the same container path everywhere — removes most import failures.

## What not to do

- **Don't run a mass "Refresh All Artists" during a metadata outage.** It's the action most likely to damage your library's metadata.
- **Don't delete `lidarr.db`.** It holds your library, history and quality decisions. Nothing about a metadata outage is fixed by losing it.
- **Don't set a profile that allows only one format** and then conclude indexers are broken. Open the interactive search and read the rejections.
- **Don't change PUID/PGID on one container only.** It moves the permission problem rather than fixing it.

## Prevention

| Habit | Why |
|---|---|
| Identical container paths across download client and *arr apps | Eliminates the biggest import failure class |
| Well-tagged files in `Artist/Album/Track` layout | Any tool, now or later, can rebuild from them |
| Automatic metadata refresh off, manual when needed | Protects against upstream outages corrupting metadata |
| Back up the *arr config directories weekly | Rebuilding profiles and history by hand is hours of work |

## FAQ

**Can I point Lidarr at MusicBrainz directly?**
No — the proxy URL is compiled in, and MusicBrainz's own rate limits are why the proxy exists.

**Is there an alternative?**
For library management, Beets plus a media server covers much of it with no hosted dependency, at the cost of the automation.

**Artist added but all albums show as missing.**
Lidarr monitors releases; it hasn't searched yet or your profile rejects everything available. Interactive search on one album tells you which.

**Metadata refresh removed albums from my library.**
That's the outage risk in section 1. Restore from a database backup if you have one; otherwise re-add and re-monitor.
