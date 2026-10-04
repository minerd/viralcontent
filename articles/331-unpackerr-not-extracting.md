---
title: "unpackerr Not Extracting? Paths, Permissions and the Queue It Reads"
slug: unpackerr-not-extracting
meta_description: "RAR archives sit in the download folder untouched. The path-matching rule that trips everyone, plus permissions and the *arr API check."
updated: October 2026
cluster: round 13 (tech) — unpackerr GitHub issues
competition: LOW
---

# unpackerr Not Extracting? Paths, Permissions and the Queue It Reads

unpackerr doesn't watch a folder. It asks Sonarr/Radarr/Lidarr for their **queue**, finds items the *arr app says it can't import, and extracts those. That design explains almost every failure:

- If it can't reach the *arr API, it has nothing to work on
- If the path the *arr reports doesn't exist at the same path inside unpackerr, it can't find the archive
- If it can't write, extraction fails

## 1. Confirm the API connection

```ini
[[sonarr]]
  url = "http://sonarr:8989"
  api_key = "your-key"
  paths = ['/downloads']
  protocols = "torrent,usenet"
  timeout = "10s"
  delete_delay = "5m"
```

```bash
docker logs unpackerr --tail 50
```

A healthy start logs each configured app and the queue size:

```
Checking: 1 Sonarr, 1 Radarr
Sonarr (http://sonarr:8989): 3 Items Queued, 0 Retrieved
```

`0 Items Queued` when you know there are downloads means either the API key is wrong (you'd see an auth error), or the *arr queue genuinely has nothing in a state unpackerr acts on. It only cares about items the *arr is **waiting to import**; a completed import is none of its business.

## 2. The path rule — the main cause

This is the part that catches everyone. unpackerr takes the path Sonarr reports for a queue item, and only acts if it starts with one of the `paths` you configured **and exists in unpackerr's own filesystem**.

So all three must agree:

| Component | Must see the archive at |
|---|---|
| Download client | `/downloads/complete/tv/Show.S01E01/` |
| Sonarr | `/downloads/complete/tv/Show.S01E01/` |
| unpackerr | `/downloads/complete/tv/Show.S01E01/` |

```yaml
  unpackerr:
    volumes:
      - /mnt/data/downloads:/downloads
```

Verify directly:

```bash
docker exec unpackerr ls -la /downloads/complete/tv | head
```

If that path doesn't exist inside unpackerr, nothing else matters. Remapping in Sonarr (Settings → Download Clients → Remote Path Mappings) fixes Sonarr's view but **not** unpackerr's — unpackerr reads the *post-mapping* path from Sonarr and then needs that same path itself. Mount it identically and avoid remote path mappings entirely where you can.

The `paths` list in unpackerr's config is a filter, not a mount. Listing `/data/downloads` while mounting `/downloads` means every item is skipped, silently, with a debug-level message you won't see at default log level.

Turn up logging while diagnosing:

```ini
  debug = true
  log_file = "/downloads/unpackerr.log"
```

The debug log states, per item, the path it saw and whether it matched.

## 3. Permissions

```ini
  file_mode = "0644"
  dir_mode = "0755"
```

And the container's identity:

```yaml
    environment:
      - UN_UID=1000
      - UN_GID=1000
```

Extraction writes the unpacked files next to the archive. If the download directory is owned by a different user, extraction fails with a permission error in the log. Standardise PUID/PGID across the download client, every *arr and unpackerr — the same advice that fixes most *arr import problems.

A subtler case: files extracted with the wrong ownership extract *successfully* and then Sonarr can't import them. If unpackerr logs success and the item still sits in the queue, check ownership of the extracted files, not the archive.

## 4. Archive types and passwords

- **Password-protected RARs are not extractable.** No configuration helps.
- **Multi-part RARs** (`.part1.rar`, `.r00`) are handled, but only if all parts are present. A missing part gives a CRC error.
- **Nested archives** (a zip inside a rar) are extracted one level by default. There's a setting for recursion depth; the default handles the common case.
- **`.iso`, `.7z`, `.zip`, `.tar.gz`** are supported. An exotic format isn't.

## 5. The delete delay

```ini
  delete_delay = "5m"
```

unpackerr waits after a successful import before removing the extracted files. If set to `-1s`, it never deletes — so your download directory fills with both archives and extracted copies, which people sometimes read as "extraction isn't working" because the archive is still there.

The archive staying put is normal: the download client owns it, and seeding may require it. What matters is whether the extracted media appeared.

## What not to do

- **Don't use remote path mappings as a substitute for consistent mounts.** They solve the *arr's view only.
- **Don't point unpackerr at a folder and expect it to scan.** It is queue-driven; a folder full of RARs with nothing in the *arr queue is correctly ignored.
- **Don't set `delete_delay` to something very short** while torrents are still seeding. You'll break the torrents.
- **Don't run it as root to fix permissions.** The extracted files then belong to root and the *arr can't import them — same problem, further along.

## Prevention

| Habit | Why |
|---|---|
| One host path mounted at one container path, everywhere | Removes the dominant failure class |
| Same PUID/PGID across the whole stack | Removes the second |
| `debug = true` while setting up, off afterwards | The answer is always in the debug log |
| No remote path mappings | They hide the inconsistency instead of fixing it |

## FAQ

**Do I still need it with Usenet?**
SABnzbd and NZBGet unpack themselves, so usually not. It matters for torrents, which arrive as archives.

**Can it handle files not in any *arr queue?**
There's a folder-watch mode in recent versions, configured separately from the *arr blocks. The queue-driven path is the main design.

**It extracts but the *arr still doesn't import.**
Permissions on the extracted files, or the *arr rejecting them on quality/naming. Check the *arr's own log for the import attempt.

**Will it delete my torrents?**
It deletes the files it extracted, not the originals, after `delete_delay`. The download client manages the archive.
