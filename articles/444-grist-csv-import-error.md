---
title: "Grist: CSV Import Errors on a Self-Hosted Instance"
slug: grist-csv-import-error
meta_description: "\"Row ID too high\" on large files, choice lists importing as red text, and formula columns arriving as data. What Grist does with an import and how to steer it."
updated: October 2026
cluster: round 14 (tech) — gristlabs/grist-core GitHub and the Grist community
competition: LOW
---

# Grist: CSV Import Errors on a Self-Hosted Instance

Three distinct problems, each with a specific handling.

## 1. "ValueError: Row ID too high" on large files

Reported with a ~70 MB CSV of about 1.7 million rows. Grist's data engine assigns row ids, and a single import of that size exceeds what the engine will allocate in one operation.

The practical answer is to **split the file**:

```bash
# header-preserving split into 200k-row chunks
head -1 big.csv > header.csv
tail -n +2 big.csv | split -l 200000 - chunk_
for f in chunk_*; do cat header.csv "$f" > "import_$f.csv"; rm "$f"; done
rm header.csv
```

Import the first chunk to create the table, then import the rest **into the existing table** with "update existing records" off so they append.

Also worth asking whether Grist is the right tool at that scale. It is a relational spreadsheet with an in-memory Python data engine — hundreds of thousands of rows work, millions are outside its comfortable range. For a 1.7-million-row dataset, loading it into Postgres and connecting a reporting tool is less painful than fighting the import.

## 2. Choice-list columns importing as red text

A documented community issue: **choice list data doesn't split on import — the list isn't parsed and the cell is marked red** (Grist's indication of an invalid value for the column type).

The cause: a Choice List column expects a list, and the CSV gives it a string like `"red, green, blue"`. Grist doesn't guess the delimiter.

The documented workaround is a **trigger formula** to convert the imported string:

1. Import into a plain **Text** column, say `tags_raw`.
2. Add a **Choice List** column `tags`.
3. Give `tags` a trigger formula applied on record change:

```python
[s.strip() for s in ($tags_raw or "").split(",") if s.strip()]
```

4. Let it run across the table, then remove `tags_raw` if you want.

That ordering matters: importing straight into a Choice List and trying to fix it afterwards leaves invalid values that the formula can't read. Import as text first.

Make sure the choices themselves exist in the column's configuration, or Grist shows valid-looking values as invalid.

## 3. Formula columns arrive as data

The documented behaviour:

> **When importing data from another document, formula columns arrive as data.**

So a column computed by a formula in the source becomes a static column of values in the destination. The formula is not carried over.

Consequences and handling:

- Expect to **re-create formulas** after any import. Note them down before migrating.
- If you're moving a whole document, **copy the document** (Grist's own duplicate/export-as-`.grist`) rather than exporting CSV and importing. The `.grist` file carries formulas, column types, views and access rules; CSV carries none of that.

```
Document menu → Download → Download document (.grist)
```

Then upload that file to the destination instance. This is the correct migration path between self-hosted Grist instances and it sidesteps this entire article.

## 4. Reference columns not resolving

Reported: **existing values in a Reference column are not resolved** on import. A CSV containing the *display* value of a referenced record doesn't automatically link to that record.

The pattern that works:

1. Import into a text column holding the lookup key.
2. Add the Reference column and set its **"SHOW COLUMN"** to the field your text matches.
3. Use a formula or Grist's reference-repair UI to populate it:

```python
Table_Lookup.lookupOne(Name=$name_raw)
```

Grist will also offer to convert a text column to a Reference and match values, which works when the values are exact. Mismatched whitespace or case defeats it — normalise first.

## 5. Import mechanics worth knowing

```
Add New → Import from file / Import from URL
```

- **Incremental imports are supported**: importing into an existing table with a key column set to "update existing records" merges rather than appends. Getting this wrong is how you end up with duplicates.
- **Import from URL** needs the instance to be able to reach it — on a self-hosted install behind a firewall, outbound access is required, and the error is a generic failure.
- Grist parses the CSV's types on preview. A column of numbers with a few text values becomes text, which then breaks downstream formulas. Clean the source.

## 6. Self-hosted specifics

```yaml
services:
  grist:
    image: gristlabs/grist:latest
    environment:
      - GRIST_SESSION_SECRET=a-long-random-string
      - GRIST_SINGLE_ORG=docs
      - GRIST_DEFAULT_EMAIL=you@example.com
      - PYTHON_VERSION_ON_CREATION=3
    volumes:
      - ./persist:/persist
    ports:
      - "8484:8484"
```

- **`/persist` must be writable.** Imports write a temporary document; a read-only volume fails with an unhelpful error.
- **Memory.** The data engine holds the document in memory. A large import on a 512 MB container is killed mid-operation:

```bash
docker stats --no-stream grist
dmesg -T | grep -i 'killed process' | tail
```

- A recent fix addressed **formula error details being unreadable in dark mode** on self-hosted instances. If you can't read an error message, switch to light mode — the information is there.

## What not to do

- **Don't migrate documents via CSV.** Use the `.grist` download.
- **Don't import directly into Choice List or Reference columns.** Text first, then convert.
- **Don't import a million rows in one file.** Split, or reconsider the tool.
- **Don't run Grist with a read-only `/persist`.** Imports need to write.

## Prevention

| Habit | Why |
|---|---|
| `.grist` export/import for document moves | Carries formulas, types, views and rules |
| Text columns on import, converted afterwards | The only reliable path for lists and references |
| Chunked imports above ~200k rows | Stays within the engine's limits |
| Note formulas before any CSV round-trip | They do not survive |

## FAQ

**Can it connect to an external database?**
Not as a live backend; Grist stores documents in SQLite internally. Import or sync via the API.

**Is there an API for bulk loading?**
Yes, and for repeated loads it's better than the UI importer — you control batching.

**Snapshots and history?**
Self-hosted Grist keeps document history in `/persist`. Back that up; it's your undo.

**Python formulas sandboxed?**
Yes, via gVisor where available. Check the sandbox configuration on self-hosted instances — without it, formulas run with fewer restrictions.
