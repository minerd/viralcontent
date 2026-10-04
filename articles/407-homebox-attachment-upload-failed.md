---
title: "Homebox: Attachment Upload Fails or Attachments Disappear"
slug: homebox-attachment-upload-failed
meta_description: "500 \"item not found\" on the API, attachments that don't display, or files gone after an upgrade. The volume path, Windows paths and version regressions."
updated: October 2026
cluster: round 14 (tech) — sysadminsmedia/homebox GitHub issues
competition: LOW
---

# Homebox: Attachment Upload Fails or Attachments Disappear

Attachments are files on disk plus rows in the database. Almost every problem here is one of the two halves being in the wrong place.

## 1. The data volume

```yaml
services:
  homebox:
    image: ghcr.io/sysadminsmedia/homebox:latest
    environment:
      - HBOX_MODE=production
      - HBOX_STORAGE_DATA=/data
      - HBOX_STORAGE_SQLITE_URL=/data/homebox.db?_pragma=busy_timeout=999&_pragma=journal_mode=WAL
    volumes:
      - homebox-data:/data
    ports:
      - "3100:7745"

volumes:
  homebox-data:
```

The documented requirement is that the volume be mounted at the **default `/data`** path. Attachments not loading has been traced directly to a non-default volume location — the database stores paths relative to the configured data directory, and moving it without migrating leaves every attachment pointing nowhere.

Check both halves:

```bash
docker exec homebox ls -la /data
docker exec homebox find /data -type d -name 'documents' -o -name 'attachments' | head
```

An empty data directory with attachments listed in the UI means the files are gone (or elsewhere) while the rows survive.

## 2. "Attachments added successfully" but never shown

Reported from 0.20.x onward: the UI confirms the upload and the file never appears on the item.

What to check:

- **Disk space and write permission** on the volume. A failed write can still return success to the browser if the error isn't propagated:

```bash
docker exec homebox sh -c 'df -h /data; touch /data/_writetest && echo writable && rm /data/_writetest'
```

- **The reverse proxy's body limit.** A photo from a modern phone is 3–8 MB; nginx's 1 MB default rejects it, and the browser's error can be swallowed by the SPA:

```nginx
client_max_body_size 100M;
proxy_request_buffering off;
proxy_read_timeout 300s;
```

- **Version.** This has been a moving target; upgrade before deep-diving, and check the changelog for your jump.

## 3. API uploads returning 500 "item not found"

A specific regression: `POST` to the attachments endpoint returning **500 with `ent: item not found`** after upgrading, breaking programmatic uploads while the web UI works.

The cause is multipart form handling: the field names and ordering the API expects changed, and the documentation lagged. Practical handling:

- Check the **current** API docs for your exact version (`/api/docs` or `/swagger` on your instance) rather than a blog post or an older README.
- The item ID must be sent in the form data in the shape that version expects — a mismatch produces exactly "item not found" even though the item exists.
- If you're scripting bulk imports, test against one item and read the response body, not just the status.

```bash
curl -s -X POST "https://homebox.example.com/api/v1/items/$ITEM_ID/attachments" \
  -H "Authorization: $TOKEN" \
  -F "file=@photo.jpg" \
  -F "type=photo" \
  -F "name=photo.jpg" -i | head -20
```

## 4. Existing attachments broken on Windows

Reported specifically: attachments added on 0.19 failed to download on 0.21 under Windows, resolved by rolling back. The cause was **attachment path encoding** in blob storage — Windows path separators handled differently between versions.

If you run Homebox on Windows (or on a Windows-hosted Docker volume):

- Check the changelog for the path-encoding fix and upgrade past it rather than rolling back permanently
- Prefer a Linux host, or at least a Linux-native volume, for anything you care about

## 5. "Attachments gone"

The worst case, and it's usually recoverable because the **files and the database are separate**:

```bash
docker exec homebox find /data -type f \! -name '*.db*' | head -20
```

- Files present, UI empty → database rows lost or pointing elsewhere. Restore the database from backup; the files will re-link if the paths match.
- Files absent → the volume wasn't persistent. If `volumes:` was missing or pointed at the container's writable layer, recreating the container destroyed them. There is no recovery.

This is why the volume configuration in section 1 matters more than anything else here.

## 6. Import/export caution

A reported discussion worth heeding: exporting and re-importing is **not** a safe round trip for attachments. The CSV export covers item data; attachments are files that the import does not carry. Migrating by export/import loses them.

To move instances, copy the whole `/data` volume — database and files together, with paths intact:

```bash
docker run --rm -v homebox-data:/from -v $(pwd):/to alpine \
  tar czf /to/homebox-data.tgz -C /from .
```

## What not to do

- **Don't run without a named volume or bind mount for `/data`.** Everything lives there.
- **Don't change the data path without migrating.** Stored paths are relative to it.
- **Don't rely on CSV export as a backup.** It omits attachments.
- **Don't upgrade across several majors blind.** Read the changelog; this area has had breaking fixes.

## Prevention

| Habit | Why |
|---|---|
| Named volume at `/data`, never changed | Removes the path class entirely |
| `client_max_body_size 100M` at the proxy | Phone photos exceed the default |
| Tar the whole volume as your backup | Database and files stay consistent |
| Check the changelog before upgrading | Attachment handling has changed more than once |

## FAQ

**Can I use Postgres instead of SQLite?**
Recent versions support it, which helps with concurrent use. Attachments are still files on disk.

**How large can attachments be?**
Bounded by your proxy and disk, not by Homebox. Keep receipts and manuals as PDFs rather than photo bursts.

**Does it generate thumbnails?**
Yes for images, cached in the data directory. A corrupt cache is safe to delete; it regenerates.

**Labels and QR codes stop resolving after a move.**
Those encode item URLs; if the hostname changed, regenerate them.
