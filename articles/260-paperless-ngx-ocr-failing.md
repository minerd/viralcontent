---
title: "Paperless-ngx OCR Failing on Some PDFs? The Three Flags That Fix It"
slug: paperless-ngx-ocr-failing
meta_description: "Signed PDFs, malformed content streams and huge scans each break OCR differently. The OCR user args that force them through, plus memory limits and pikepdf issues."
updated: October 2026
cluster: round 12 (tech) — Paperless-ngx GitHub issues and OCRmyPDF upstream
competition: LOW
---

# Paperless-ngx OCR Failing on Some PDFs? The Three Flags That Fix It

Most documents consume fine and a few always fail. The failure is usually in **OCRmyPDF**, which Paperless uses underneath, and the error text tells you exactly which category you're in. Find it first:

**Documents → the failed task**, or the **Tasks** page, or:
```bash
docker compose logs -f webserver | grep -i -e error -e ocrmypdf
```

## 1. Digitally signed PDFs

Error: OCR would **invalidate the digital signature**, so it refuses.

That's deliberate — OCR rewrites the file. If you accept losing the signature:

```yaml
environment:
  PAPERLESS_OCR_USER_ARGS: '{"invalidate_digital_signatures": true}'
```

Bank statements, invoices and official documents are the common case. Decide consciously: the document stays readable, but the cryptographic signature is gone.

## 2. Malformed PDFs ("content stream is corrupt")

Error: `InputFileError: PDF content stream is corrupt - this PDF is malformed`.

The file opens in your viewer because viewers are forgiving; OCRmyPDF is strict.

```yaml
  PAPERLESS_OCR_USER_ARGS: '{"continue_on_soft_render_error": true}'
```

That pushes most of them through. If a specific file still fails, repair it once outside Paperless:

```bash
qpdf --replace-input broken.pdf                 # rewrite structure
gs -o fixed.pdf -sDEVICE=pdfwrite broken.pdf    # heavier, re-renders
```

Then re-consume the repaired copy.

## 3. Large or high-resolution scans

Error: a task that dies with no clear message, or the container restarting mid-job.

That's **memory**. OCR rasterises pages; a 600 dpi colour A3 scan is enormous in RAM.

```bash
docker inspect <container> --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
dmesg -T | grep -i "killed process" | tail
```

Exit 137 confirms it. Options:
- Raise the host's RAM, or add **swap** so it's slow rather than fatal
- Lower **`PAPERLESS_OCR_MAX_IMAGE_PIXELS`** / scan at a sane resolution (300 dpi is plenty for text)
- Reduce **`PAPERLESS_TASK_WORKERS`** and **`PAPERLESS_THREADS_PER_WORKER`** — four workers each rasterising a big scan will kill a small box
- Scan to **greyscale** rather than colour for text documents

## 4. Version-specific library bugs

Reported: consuming PDFs failing with `AttributeError: get_images` when **`optimize >= 2`** is set in OCR user args, fixed by upgrading **pikepdf** inside the container.

Pattern to recognise: a Python traceback naming a library rather than your document. Then:
- Check the **GitHub issues** for your Paperless version and that traceback
- **Upgrade Paperless** (the pinned library versions come with the image)
- As a stopgap, remove the option that triggers it (`optimize`, `--deskew`, `--clean`) and consume without it

## 5. The pragmatic escape hatch

Some documents simply won't OCR. Paperless can store them anyway:

```yaml
  PAPERLESS_OCR_MODE: skip_noarchive     # or: skip
```

- `skip` — don't OCR files that already have text
- `skip_noarchive` — don't build an archive version when OCR isn't possible
- `redo` — force OCR even over existing text

You keep the document and lose searchable text for that one file. Better than a stuck consume folder.

## 6. Language packs

A document in a language you haven't installed OCRs badly rather than failing:

```yaml
  PAPERLESS_OCR_LANGUAGE: tur+eng
  PAPERLESS_OCR_LANGUAGES: tur eng deu
```

`PAPERLESS_OCR_LANGUAGES` installs the Tesseract data; `PAPERLESS_OCR_LANGUAGE` selects it. Setting only the second gives you a confusing failure on first use.

## Prevention

1. **Scan at 300 dpi greyscale** for text; reserve colour and high dpi for what needs it
2. Set the **user args** above once, before you hit the problem
3. Keep **task workers** proportional to RAM
4. Monitor the **Tasks** page rather than discovering failures months later
5. **Pin the image tag** and read release notes for OCR-related changes

## FAQ

**Can I OCR a signed PDF without destroying the signature?**
No. Either keep the signature and skip OCR, or invalidate it deliberately.

**Why do big scans fail silently?**
The worker is OOM-killed. Check for exit code 137.

**Should I set `optimize`?**
It saves space but has triggered library bugs. Leave it default unless you need it.

**The file sits in the consume folder forever.**
The task failed — look at the Tasks page for the message, then match it to a section above.
