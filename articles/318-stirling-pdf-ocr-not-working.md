---
title: "Stirling PDF OCR Not Working: Language Packs and the tessdata Path"
slug: stirling-pdf-ocr-not-working
meta_description: "OCR fails, the language list is empty, or output has no text layer. Which image you're running, where tessdata must go, and the ghostscript dependency."
updated: October 2026
cluster: round 13 (tech) — Stirling PDF GitHub issues
competition: LOW
---

# Stirling PDF OCR Not Working: Language Packs and the `tessdata` Path

Most Stirling PDF OCR problems come from one thing: **the image you pulled doesn't include OCR**, or it does and can't find its language data. Establish which image you're running before anything else.

## 1. Check your image tag

Stirling PDF publishes variants, and the difference is the installed toolchain:

| Tag | Includes OCR? | Notes |
|---|---|---|
| `latest` / `:latest-ultra-lite` | **No** | Minimal; OCR endpoints error |
| `:latest-fat` | Yes | Everything bundled, largest |
| `:latest` (recent versions) | Varies | Check the release notes for your version |

```bash
docker inspect stirling-pdf --format '{{.Config.Image}}'
docker exec stirling-pdf which tesseract
```

If `tesseract` isn't found, the image doesn't have it and no configuration will add it. Switch to the fat image:

```yaml
services:
  stirling-pdf:
    image: stirlingtools/stirling-pdf:latest-fat
```

This single change resolves a large share of OCR reports.

## 2. Language data

Tesseract needs a `.traineddata` file per language. Stirling expects them in a known path, mounted from the host:

```yaml
    volumes:
      - ./tessdata:/usr/share/tessdata
```

Then populate it:

```bash
mkdir -p tessdata
cd tessdata
curl -LO https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
curl -LO https://github.com/tesseract-ocr/tessdata/raw/main/deu.traineddata
curl -LO https://github.com/tesseract-ocr/tessdata/raw/main/tur.traineddata
```

Points that matter:

- **The mount path differs by version.** Older versions used `/usr/share/tesseract-ocr/5/tessdata` or `/usr/share/tesseract-ocr/4.00/tessdata`. Check where the binary looks:

```bash
docker exec stirling-pdf tesseract --list-langs
```

That command prints the directory it's searching. Mount to exactly that path — copying a path from a guide for a different version is the usual failure.

- **Mounting an empty directory over a populated one** removes the bundled languages. If the fat image already ships `eng` and you mount an empty `./tessdata` over it, the language list goes empty. Either don't mount, or copy the existing files out first:

```bash
docker cp stirling-pdf:/usr/share/tessdata/. ./tessdata/
```

- **Use `tessdata` (standard), not `tessdata_best` or `tessdata_fast`** unless you have a reason. Standard is the balanced build; `_best` is much slower and `_fast` noticeably less accurate on scans.

- Filenames are case-sensitive and must keep the `.traineddata` extension. `eng.traineddata.txt` from a browser download is a common silent failure.

## 3. OCR runs but there's no text layer

The output PDF looks identical and selecting text does nothing.

- **OCR mode.** Stirling offers "force OCR" vs. "skip pages with text". If the pages already contain *some* text (e.g. a header added by a scanner), skip-mode skips them entirely. Use **Force OCR** to re-OCR everything.
- **Ghostscript / qpdf missing.** The OCR pipeline rasterises and reassembles. A missing dependency produces a successful-looking job with no change. Check:

```bash
docker exec stirling-pdf sh -c 'which gs qpdf unpaper'
```

- **The input is a vector PDF with no images.** There's nothing to OCR; the text is already there in a form your viewer isn't selecting. Different problem.

## 4. OCR fails or times out

- **Memory.** OCR at 300 DPI on a 200-page document is memory-hungry. A 512 MB container will be killed. Give it 2 GB and check `dmesg | grep -i oom` if a large job dies and a small one works.
- **Timeout behind a proxy.** A long OCR job exceeds nginx's 60 s default and the browser gets a 504 while the job continues. Raise `proxy_read_timeout` to 600s.
- **Upload size.** `client_max_body_size 200M;` — the default 1 MB rejects most scanned documents before OCR is even reached.
- **Temp space.** The pipeline writes intermediate images. A small `/tmp` fills and the job fails with an I/O error. Mount a real volume for temp files if you process large documents.

## What not to do

- **Don't mount an empty tessdata directory.** It's a reliable way to turn a working install into a broken one.
- **Don't download `tessdata_best` for everything.** Multi-hundred-megabyte files for marginal accuracy on clean scans, and much slower.
- **Don't OCR at 600 DPI by default.** 300 is the accuracy plateau for text; above that you spend memory and time for nothing.
- **Don't run OCR on an already-searchable PDF in force mode** unless you need to — it rasterises your crisp vector text into images.

## Prevention

| Habit | Why |
|---|---|
| Use the fat image if you use OCR at all | Removes the whole "tool not installed" class |
| Confirm the tessdata path with `--list-langs` after every upgrade | The path has moved between versions |
| Raise proxy body size and timeouts once, generously | These limits bite every document tool |
| Keep 2 GB and real temp space available | OCR is the memory-heaviest thing Stirling does |

## FAQ

**Can I OCR in multiple languages at once?**
Yes, select several — Tesseract takes a `+`-joined list. It's slower and slightly less accurate per language than a single correct choice.

**Does it handle handwriting?**
No. Tesseract is for printed text.

**Output file is much larger than the input.**
Expected with force OCR: pages become images plus a text layer. Use the compress tool afterwards.

**Is there a batch/API route?**
Yes, Stirling exposes an API; the same dependency and tessdata requirements apply, so fix the UI path first and the API follows.
