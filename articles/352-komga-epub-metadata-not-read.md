---
title: "Komga Not Reading EPUB Series Metadata"
slug: komga-epub-metadata-not-read
meta_description: "EPUBs import with no title, author or series. The OPF namespace prefix problem, Calibre's series field, and what Komga actually reads."
updated: October 2026
cluster: round 14 (tech) — Komga GitHub issues
competition: LOW
---

# Komga Not Reading EPUB Series Metadata

Komga reads metadata from the EPUB's **OPF package document**. EPUB is a loosely-implemented format and a large share of files in the wild are built in ways Komga's parser doesn't expect. The failure is usually the file, not Komga — which matters, because it tells you to fix the file.

## 1. Find out what's actually in the file

An EPUB is a zip. Look inside:

```bash
unzip -p book.epub META-INF/container.xml
# → points at the OPF, e.g. OEBPS/content.opf
unzip -p book.epub OEBPS/content.opf | head -40
```

What you want to see:

```xml
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Book One</dc:title>
  <dc:creator>Author Name</dc:creator>
  <meta name="calibre:series" content="My Series"/>
  <meta name="calibre:series_index" content="1"/>
</metadata>
```

Two specific problems show up here.

**The OPF namespace prefix.** Some valid EPUBs prefix *every* OPF element:

```xml
<opf:metadata>
  <opf:meta name="calibre:series" content="My Series"/>
</opf:metadata>
```

Komga's parser has not handled the prefixed form in all versions, and the result is that title, creator and series are not detected at all — the book appears named after its filename. This is a known gap; the practical fix is to re-write the OPF without the prefix (Calibre does this on a convert or on "Polish books"), or to rely on file naming and Komga's own metadata editor.

**Calibre's series field.** Series is not a core EPUB field. Calibre stores it as `calibre:series` in `<meta>`, and Komga reads that — but only when the tag is present. Exporting from Calibre with "Save to disk" templates that don't include series metadata produces files with no series at all. In Calibre, the series must be set on the book *and* the EPUB regenerated (convert, or Polish) for it to land in the file.

## 2. Make Komga re-read it

Komga caches metadata. Editing the file on disk does not retrigger a read:

```
Library → ⋮ → Scan library files
Library → ⋮ → Analyze
```

**Analyze** is the one that re-reads embedded metadata. If you've locked a field in Komga's metadata editor, Analyze will not overwrite it — that lock is per field and is the reason "it still shows the old value" after you fixed the file.

Series-level metadata is separate from book-level. A book can have the right series name in the file while the Komga *series* entity keeps an older title; edit the series directly, or delete the (empty) series and re-scan.

## 3. Directory structure is the reliable fallback

Komga derives series from the **directory**, and that is far more predictable than EPUB metadata:

```
/books/
  My Series/
    My Series 01 - Book One.epub
    My Series 02 - Book Two.epub
```

One directory per series, one file per book. With this layout you get correct series grouping even from files with no usable internal metadata, and you can then let a metadata provider or manual editing fill in the rest.

Mixing formats in one series directory is supported — comics and ebooks can live together — so there's no reason to split a series by format.

## 4. "Books not showing properly"

Related failures worth separating:

- **The book appears but won't open.** The EPUB's spine or manifest references files that aren't in the zip. `epubcheck` will say so.
- **Pages out of order.** Spine order in the OPF. Nothing Komga can infer around it.
- **Cover missing.** Komga looks for the cover declared in the OPF `<meta name="cover">` or a `properties="cover-image"` item. Files with neither get the first page as a cover, or nothing.

```bash
# if you have epubcheck installed
epubcheck book.epub
```

A file that fails epubcheck will have problems in every reader, not just Komga.

## What not to do

- **Don't rebuild the Komga database to fix one book.** You lose read progress and collections, which exist nowhere else.
- **Don't edit metadata in Komga and then expect a file fix to show.** Locked fields win.
- **Don't rely on EPUB series metadata for a large library.** Directory structure is deterministic; OPF contents are not.
- **Don't bulk-convert your library in Calibre without a backup.** Conversion is lossy for some formatting.

## Prevention

| Habit | Why |
|---|---|
| One directory per series, numbered filenames | Correct grouping regardless of file metadata |
| Set series in Calibre and re-polish before export | Puts `calibre:series` into the file |
| Run `epubcheck` on problem files | Separates "bad file" from "Komga bug" in one command |
| Back up the Komga database | Read progress and collections are not in the files |

## FAQ

**Does Komga write metadata back into files?**
No. Its edits live in its own database. That's safer, and it means a library move needs the database too.

**Can it fetch metadata from an online source?**
Not in core; there are community tools that write to Komga's API. For ebooks, Calibre plus good filenames is the usual pipeline.

**KOReader progress sync?**
Komga exposes a sync endpoint; compatibility with specific KOReader plugin versions varies, and that's a separate issue from metadata.

**CBZ works, EPUB doesn't.**
Expected — CBZ has almost no metadata to misparse. It's evidence that your setup is fine and the EPUB files are the variable.
