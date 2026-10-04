---
title: "immich-go: Uploads Succeed But Albums Are Wrong (or Empty)"
slug: immich-go-upload-albums
meta_description: "Google Takeout imports losing albums and dates, duplicates piling up, or the API key rejected. The flags that matter and the order to use them in."
updated: October 2026
cluster: round 13 (tech) — immich-go GitHub issues
competition: LOW
---

# immich-go: Uploads Succeed But Albums Are Wrong (or Empty)

`immich-go` does two quite different jobs, and most problems come from using the wrong one. Uploading a folder tree and importing a Google Takeout archive have different flags, different album behaviour, and different date handling.

## 1. Use the Takeout mode for Takeout archives

If your source is Google Photos, do **not** unzip it and upload the folders. The album membership and the true capture dates live in the JSON sidecars, and plain folder upload ignores them.

```bash
immich-go upload from-google-photos \
  --server=http://192.168.1.10:2283 \
  --api-key=YOUR_KEY \
  takeout-*.zip
```

Points that matter:

- **Pass the zips directly.** immich-go reads inside them. This is faster and, more importantly, keeps the sidecar JSON associated with the right file. Manual unzipping across multiple archives splits a single photo's data from its JSON, which is the main cause of wrong dates.
- **Pass *all* the zips in one command.** Google splits an export across many archives, and a photo's JSON can land in a different zip from the image. Running them one at a time guarantees mismatches.
- Albums are created automatically from the Takeout structure. You don't need `--album`.

Useful filters:

```bash
  --from-album-name="Holiday 2024"     # just one album
  --date-range=2020-01-01,2020-12-31   # a slice by date
```

## 2. Folder uploads: albums are explicit

```bash
immich-go upload from-folder \
  --server=http://192.168.1.10:2283 \
  --api-key=YOUR_KEY \
  --folder-as-album=FOLDER \
  /mnt/photos/2024
```

`--folder-as-album=FOLDER` uses the immediate directory name; `--folder-as-album=PATH` builds the album name from the whole relative path. Without either flag you get no albums at all — which is the "uploads worked but no albums" report.

Dates in folder mode come from EXIF. For files with no EXIF (screenshots, WhatsApp images, scans), add:

```bash
  --date-from-name
```

which parses common filename date patterns. Without it, those files get the file's modification time, which is usually the day you copied them.

## 3. API key and connection failures

```
error: authentication failed
```

- The key must come from **immich → Account Settings → API Keys**, and in recent Immich versions keys have **scopes**. A key without the upload permissions fails here. Create one with full access for the import, then delete it.
- `--server` takes the base URL **without** `/api`. Adding `/api` yields 404s that read as auth failures.
- Behind a reverse proxy, raise the body size limit (`client_max_body_size 50G;` for nginx) and the timeouts. Large videos otherwise fail partway with a vague network error.

Test the connection on its own:

```bash
curl -s -H "x-api-key: YOUR_KEY" http://192.168.1.10:2283/api/server/about
```

## 4. Duplicates

immich-go checks for existing assets before uploading, but the check isn't magic:

- Re-running the same command is safe; it skips what's there.
- Uploading the *same photo in a different format* (a Takeout JPEG and the original HEIC) creates two assets. That's correct behaviour from the tool's view.
- Google's "edited" copies (`IMG_1234-edited.jpg`) are separate files. Use `--discard-archived` and review Immich's own duplicate finder afterwards rather than trying to filter them during import.

Immich's built-in **Utilities → Duplicates** view is the right tool for cleanup, after the import, not during.

## What not to do

- **Don't unzip Takeout archives manually.** It's the single biggest cause of lost dates and albums.
- **Don't run one zip at a time.** Same reason.
- **Don't delete the Takeout archives until you've verified** a sample: pick ten photos from different albums and years and check their dates and album membership in Immich.
- **Don't import into an Immich instance you haven't backed up.** The database holds all the album structure; the files alone won't reconstruct it.

## Prevention

| Habit | Why |
|---|---|
| Keep the original Takeout zips until verified | The only source of truth for dates and albums |
| One command, all zips | Prevents sidecar/file separation |
| Run a small `--date-range` slice first | Catches flag mistakes before a 500 GB import |
| Create a scoped, temporary API key | Limits damage and makes the import auditable |

## FAQ

**Can I import from another Immich server?**
Export the originals and use folder mode with `--folder-as-album=PATH`. There's no direct server-to-server mode that preserves everything.

**Motion photos / live photos?**
Takeout mode pairs the still and the video where Google kept them together. Folder mode does not pair them.

**It stops partway through a huge import.**
Re-run the identical command. It resumes effectively by skipping existing assets. Check the proxy timeout if it stops at the same place each time.

**Dates are right in the file but wrong in Immich.**
Immich prefers EXIF `DateTimeOriginal`. If that field is absent or wrong in the file, fix it with `exiftool` before importing rather than after.
