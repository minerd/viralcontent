---
title: "Kavita Library Scan Stuck or Missing Files? Folder Structure and Permissions"
slug: kavita-scan-stuck
meta_description: "Scans that hang on 'File Scan Starting', stop after the first folder, or only show part of your library. Why force-scan works temporarily and what to fix properly."
updated: October 2026
cluster: round 12 (tech) — Kavita GitHub issues only
competition: LOW
---

# Kavita Library Scan Stuck or Missing Files? Folder Structure and Permissions

Three reported symptoms, one set of causes:

- **Stuck on "File Scan Starting"** and never progressing
- **Scan stops after the first folder** that contains files
- **Only part of the library shows**, and a **force scan** fixes it temporarily

## 1. Folder structure is the usual cause

Kavita infers series, volumes and chapters from the **directory layout and filenames**. Libraries laid out in ways it doesn't expect — especially Publisher/Series nesting, or everything in one flat folder — produce partial scans and odd groupings. The scanner's change detection has been a known weak point as libraries got bigger and more varied.

What works reliably:

```
/manga/
  Series Name/
    Series Name Vol. 01.cbz
    Series Name Vol. 02.cbz
/books/
  Author Name/
    Book Title/
      Book Title.epub
```

- One folder **per series**, directly under the library root
- Avoid extra nesting levels Kavita isn't expecting
- Avoid mixing **manga, comics and ebooks** in one library — create separate libraries with the correct type
- Keep filenames consistent; volume/chapter numbers in a predictable position

## 2. Permissions

Kavita needs **read** on everything and **write** where it stores covers/bookmarks:

```bash
docker exec -it kavita ls -la /manga
docker exec -it kavita stat /manga/"Some Series"
```

- Match **PUID/PGID** to the owner of the media
- Directories need the **execute** bit to be traversable (`755`), not just read
- Mixed ownership across a library (half from one tool, half from another) gives exactly the "some files missing" symptom
- A folder the container can't enter is skipped **silently**, which is why it looks like a scanner bug

## 3. Network shares and change detection

Kavita watches for changes. On **NFS/SMB** mounts:

- **Inotify doesn't fire**, so new files aren't noticed until a scheduled or forced scan — that is the entire explanation for "force scan works, then it forgets"
- Timestamps can be unstable, breaking change detection
- Latency makes big scans crawl and look hung

Practical answers: keep the library on **local storage** if you can, or rely on **scheduled scans** rather than live detection, and accept that new files appear at the next scan.

## 4. Stuck at the very start

"File Scan Starting" and nothing else usually means it's working but hasn't reported yet, or it died:

```bash
docker compose logs -f kavita
docker exec -it kavita ls -la /kavita/config/logs/
```

Look for:
- A very large library genuinely taking a long time on the **first** scan (hours is plausible)
- An exception naming a specific file — a corrupt CBZ/EPUB can stall the pass; move it out and rescan
- **Disk full** on the config volume (covers and the database live there)
- **Database locked** errors → another process or a backup touching `kavita.db`

## 5. One problem file

A malformed archive is a common stall. Bisect it: move half the series out, scan, move them back. Tedious, reliable, and it finds the file in a few passes. `unzip -t` on CBZ files and `epubcheck` on EPUBs will often identify it faster.

## 6. After an update

- **Pin the image tag**; the scanner has been rewritten more than once
- Read the release notes for scanner changes — some versions need a **one-off full/force scan** to rebuild metadata
- If a version scans worse than the last, roll back and report it with your folder layout attached (that's what maintainers need)

## Prevention

1. **One folder per series** under the library root; correct library type
2. **Consistent ownership** across the whole library, matching PUID/PGID
3. **Local storage** where possible; scheduled scans where not
4. Back up **`/kavita/config`** — it holds the database, covers and progress
5. Validate new archives before dropping them in

## FAQ

**Why does a force scan fix it temporarily?**
Force scan ignores change detection and reads everything. If that works, your change detection (inotify on a network share, or timestamps) is the problem.

**How long should a first scan take?**
Large libraries can take hours. Watch the log rather than the progress label.

**Can I mix comics and ebooks in one library?**
Don't. Use separate libraries with the right type.

**One series never appears.**
Permissions on that folder, or a corrupt file inside it. Check both.
