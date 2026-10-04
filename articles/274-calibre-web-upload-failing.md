---
title: "Calibre-Web Upload Failing? Permissions, Cross-Device Links and MIME Checks"
slug: calibre-web-upload-failing
meta_description: "Uploads that error, land in an 'Unknown' folder, or appear on disk but not in the library. The NFS cross-device problem, temp dir, python-magic and Calibre lock conflicts."
updated: October 2026
cluster: round 12 (tech) — Calibre-Web GitHub issues and LinuxServer discourse
competition: LOW
---

# Calibre-Web Upload Failing? Permissions, Cross-Device Links and MIME Checks

Several distinct failures all show as "upload doesn't work". Match yours.

## 1. "Operation not permitted" / file lands in an Unknown folder

Calibre-Web uploads to a temp location, then **moves** the file into the library and renames it. A half-completed move leaves the book in an `Unknown` author folder and an error on screen.

Causes:
- **Ownership/permissions** on the library directory. Match **PUID/PGID** to the owner of the Calibre library, and make sure directories are writable and traversable
- A **read-only** mount (or a NAS share mounted read-only after a reboot)
- SELinux: add `:z` to the bind mount

```bash
docker exec -it calibre-web ls -la /books
docker exec -it calibre-web touch /books/.writetest && echo ok
```

## 2. "[Errno 18] Invalid cross-device link"

A rename across filesystems isn't allowed, so the move fails. This happens when the **temp directory and the library are on different mounts** — classic with the library on NFS/SMB and temp on the container's filesystem.

Fix by putting the temp directory on the **same filesystem as the library**:

```yaml
environment:
  - TMPDIR=/books/.tmp        # same volume as the library
```
and create that directory with the right ownership. (Some setups use `CALIBRE_TEMP_DIR`/`SQLALCHEMY_*` style variables; the principle is the same — temp and destination on one filesystem.)

## 3. "Could not be saved to temp dir"

The temp directory doesn't exist, isn't writable, or is full:

```bash
docker exec -it calibre-web sh -c 'df -h /tmp; ls -ld /tmp'
```

Large PDFs plus a small `/tmp` (or a `tmpfs` with a tight size limit) is the common version of this.

## 4. Some file types stopped uploading after 0.6.22

Documented: **python-magic** was added to validate MIME types, and uploads of some formats began failing where they previously worked — `.mobi` reports are typical.

- Make sure the **`libmagic`** library is present in the image (official and LinuxServer images include it; a custom build may not)
- Check the **allowed upload extensions** setting hasn't been narrowed
- Confirm the file really is what its extension claims: `file book.mobi`
- If a format is genuinely rejected and you need it, convert it (Calibre's `ebook-convert`) rather than fighting the validator

## 5. The file appears on disk but not in the library

Upload moved the file, but the **Calibre database wasn't updated**:

- Another process holds **metadata.db** — a running Calibre desktop app, a Calibre content server, or Calibre-Web Automated's own ingest process. One writer at a time
- The database is on a **network share**, where SQLite locking is unreliable. Keep `metadata.db` on local storage
- Permissions on `metadata.db` itself (not just the folder)
- After fixing: use Calibre-Web's **"Reconnect to Calibre Database"**, or import the stray files with `calibredb add`

## 6. "Failed to queue upload for processing" (Calibre-Web Automated)

That's the CWA ingest pipeline, not plain Calibre-Web. Check its ingest container/service log, the ingest folder's permissions, and that the conversion tools it depends on are present. Report it against the CWA project, not upstream Calibre-Web.

## Prevention

1. **Library and temp on the same filesystem**, both writable by the app's UID
2. **`metadata.db` on local storage**, never on NFS/SMB
3. **One writer** to the Calibre library at a time
4. Keep **`libmagic`** available and the allowed-extensions list sane
5. **Back up `metadata.db`** before bulk imports — it's the library

## FAQ

**Why does the book appear in the folder but not the library?**
The move succeeded and the database update didn't — usually a lock or permissions on `metadata.db`.

**Can my Calibre library live on a NAS share?**
The book files can. Keep `metadata.db` local; SQLite over SMB/NFS corrupts.

**Why did .mobi stop working?**
MIME validation added in 0.6.22, plus a missing or mismatched libmagic.

**Do I need the Calibre desktop app installed?**
Not for Calibre-Web itself, but conversion features rely on Calibre's tools being present.
