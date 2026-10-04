---
title: "Audiobookshelf: Metadata Won't Update or Embed"
slug: audiobookshelf-metadata-not-updating
meta_description: "Match applies but the files keep old tags, books merge into each other, or 'Failed to update item details'. Inodes on network shares, and the embed path."
updated: October 2026
cluster: round 13 (tech) — Audiobookshelf GitHub issues and discussions
competition: LOW
---

# Audiobookshelf: Metadata Won't Update or Embed

Three different problems get reported as "metadata not updating", and one of them can quietly merge two books together. Identify yours first.

- **Match works in the UI, files still have old tags** → embedding, section 2
- **A new book takes over an existing one's details** → the inode problem, section 3
- **"Failed to update item details" on submit** → section 4

## 1. Understand the two layers

Audiobookshelf keeps metadata in **its own database** and, optionally, writes it into the **files** (embedded tags) or a **sidecar** `metadata.json`/`metadata.abs` next to the book.

Matching a book updates the database. It does **not** touch the files unless you ask it to. So mp3tag showing old data after a successful match is expected behaviour, not a bug.

Enable the sidecar — this is the single most valuable setting here:

**Settings → Library → Edit → "Store metadata with item"**

With it on, each book directory gets a metadata file. That gives you two things: a human-readable record of what ABS believes, and a recovery path if the database is lost or an item gets confused.

## 2. Embedding into the files

**Item → ⋮ → Embed Metadata** (or Tools → Embed Metadata in bulk).

What goes wrong:

- **The job reports success and tags are unchanged.** Check the file format. Embedding works for M4B/MP4 and MP3; it can't write tags into formats that don't support them. A book of many MP3s embeds per-file, and some players read only the first file's tags.
- **Read-only filesystem or wrong ownership.** ABS needs write access to the book files:

```bash
docker exec -it audiobookshelf ls -ln /audiobooks | head
docker exec -it audiobookshelf id
```

Standardise on the same UID/GID as whatever else writes there.

- **ffmpeg failure.** Embedding uses ffmpeg to rewrite the container. Check the log:

```bash
docker logs audiobookshelf --tail 100 | grep -iE 'embed|ffmpeg|error'
```

- **Disk space.** Embedding writes a new file and replaces the original; it needs room for a full copy of the largest book. A nearly-full volume fails here first.

ABS keeps a backup of the original file alongside by default when embedding — useful, but it doubles space during the operation.

## 3. The inode problem on network shares

This one matters because it can corrupt your library.

Audiobookshelf identifies library items partly by **filesystem inode**. On SMB/CIFS and NFS mounts, inode numbers can be reused or synthesised, so a newly added book can present the same inode as a book ABS already knows. ABS then treats the new book as the existing one: the details of the old book appear on the new, or the two merge.

Symptoms: a book you just added shows another book's cover and description; two books share one entry; a scan "loses" books.

Mitigations, all worth applying on a network share:

- **Turn off the folder watcher** (Settings → Library → disable watcher) and scan manually. The watcher reacts to filesystem events, which are the least reliable part on a network mount.
- **Enable "Store metadata with item"** so each book carries its own identity on disk.
- **Mount with options that give stable inodes.** For CIFS, `noserverino` makes the client generate inode numbers, which can help or hurt depending on the server — test it:

```
//nas/audiobooks /audiobooks cifs credentials=/etc/smbcreds,uid=1000,gid=1000,noserverino 0 0
```

- **Prefer NFS over CIFS** where you have the choice, or better, keep the library on local storage and back it up elsewhere.

If two items have already merged, the recovery is to remove both from the library (without deleting files), then re-scan with the watcher off.

## 4. "Failed to update item details"

- **A provider returning malformed data.** The match preview shows fields, submit fails. Try a different metadata provider for that book; Audible region providers and Google Books behave differently on edge cases (very long descriptions, unusual series data).
- **Database locked.** SQLite under a concurrent scan. Wait for the scan to finish, then retry.
- **Author with a very large number of items.** Submitting a change that touches an author with hundreds of books has timed out in some versions. Retry once; if it's consistent, update via the author page instead.
- **Reverse proxy body limit.** A long description plus a cover image can exceed a 1 MB `client_max_body_size`. Raise it:

```nginx
client_max_body_size 50M;
```

## 5. Library-level provider selection doesn't stick

A known irritation: changing a library's metadata provider, then finding it reverted after a page refresh. The provider chosen at library creation persists in some versions. The workaround is to select the provider **in the match dialog itself** each time, which does take effect, rather than relying on the library default.

## What not to do

- **Don't run the watcher on a network share.** It's the main amplifier of the inode problem.
- **Don't embed metadata on a nearly-full volume.** It needs space for a full copy.
- **Don't delete and re-add the whole library to fix one book.** You lose progress, bookmarks and collections, which live in the database.
- **Don't edit tags with an external tool while ABS is scanning.** The two will fight and the result is unpredictable.

## Prevention

| Habit | Why |
|---|---|
| "Store metadata with item" on from day one | Gives every book an identity independent of the database |
| Watcher off on network shares, manual scans | Removes the main source of item confusion |
| Back up the ABS database and config | Progress, bookmarks and collections exist nowhere else |
| One book per directory, `Author/Series/Title` layout | Makes scans deterministic and recovery trivial |

## FAQ

**Does embedding change my files?**
Yes — it rewrites the container with new tags. ABS can keep a backup of the original; enable that if the files are irreplaceable.

**Can I use a custom metadata provider?**
Yes, ABS supports custom providers via a small API. Some have had bugs around partial data; check the provider's own issues if fields go missing.

**Progress lost after a re-scan.**
Progress is tied to the library item. If an item was removed and recreated (new inode, moved directory), progress doesn't follow. The sidecar doesn't store progress.

**Should I convert everything to M4B?**
It makes chapters and tags far more reliable, and single-file books avoid the per-file tag problem entirely. It's the format ABS handles best.
