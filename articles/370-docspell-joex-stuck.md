---
title: "Docspell: Documents Stuck in the Processing Queue (joex)"
slug: docspell-joex-stuck
meta_description: "Jobs sit in stuck or running forever. The LibreOffice concurrency deadlock, the OutOfMemory crash, and the stale jobgroupuse rows."
updated: October 2026
cluster: round 14 (tech) — eikek/docspell GitHub issues
competition: LOW
---

# Docspell: Documents Stuck in the Processing Queue (joex)

Docspell's job executor (**joex**) is a separate process from the web server. Uploads always succeed — they're just a row and a file — and everything that matters happens afterwards in joex. Three distinct failure modes.

First, understand the states, because "stuck" is a real state and not an error:

- **waiting** — queued, nothing wrong
- **running** — in progress
- **stuck** — failed, will be retried after a delay
- **failed** — exceeded the retry count
- **cancelled**

A job cycling waiting → running → stuck repeatedly is failing. A job sitting in **running** with no progress is the deadlock case.

## 1. The LibreOffice concurrency deadlock

This is the one that takes the longest to diagnose. Docspell converts office documents (`.docx`, `.xlsx`, `.odt`) via **unoconv**, which talks to a single shared `soffice.bin` listener. LibreOffice's UNO headless interface is **not safe for concurrent conversion**, so when the worker pool calls unoconv from several workers at once against one listener, the pool deadlocks — sometimes for hours — and every subsequent job queues behind it.

The symptom: a couple of office documents in **running** forever, everything else waiting, no error in the log.

Mitigations:

```conf
# docspell-joex.conf
docspell.joex {
  scheduler {
    pool-size = 1
    counting-scheme = "4,1"
    retries = 2
    retry-delay = "1 minute"
  }
}
```

`pool-size = 1` serialises everything. It is slower and it removes the deadlock entirely — the right trade for a personal instance.

Recover a deadlocked executor:

```bash
docker compose restart docspell-joex
```

Jobs in **running** at restart need to be reset; see section 3.

Longer term, the project has moved toward an out-of-band `unoserver` daemon instead of unoconv precisely because of this. If your version offers it, use it and you can raise the pool size again.

## 2. OutOfMemoryError

```bash
docker logs docspell-joex --tail 100 | grep -iE 'OutOfMemory|heap|Killed'
```

```
java.lang.OutOfMemoryError: Java heap space
```

joex runs OCR and image processing on the JVM heap. The default heap is often too small for large scanned PDFs.

```yaml
  docspell-joex:
    environment:
      JAVA_OPTS: "-Xms256m -Xmx2g"
```

And give the container real memory to back it:

```yaml
    deploy:
      resources:
        limits:
          memory: 3g
```

A JVM `-Xmx` larger than the container limit guarantees an OOM kill rather than a graceful Java error — keep `-Xmx` comfortably below the limit.

Also reduce per-job cost for huge files:

```conf
docspell.joex.extraction.ocr {
  max-image-size = 14000000
  page-range { begin = 10 }
}
```

Limiting OCR to the first pages of very long documents is a legitimate trade for a personal archive.

## 3. Stale job state after a crash

If joex is killed while jobs are **running**, rows remain claimed and new joex instances believe work is in progress. Docspell tracks group usage in a `jobgroupuse` table, and stale entries there make the scheduler skip groups.

The clean fix is from the UI: **Admin → Job Queue**, cancel the stuck jobs, then re-trigger processing on the affected items. If the UI won't let you:

```sql
-- back up the database first
UPDATE job SET state = 'cancelled' WHERE state = 'running';
DELETE FROM jobgroupuse;
```

Then restart joex. Only do this with joex stopped, or you'll race it.

## 4. joex can't be reached / wrong hostname

A separate startup failure:

```
Cannot resolve host 'docspell-joex'
```

The web server (restserver) and joex find each other by configured URL. In Compose, use service names and make sure both are on the same network:

```conf
# docspell-restserver.conf
docspell.server.backend.files { ... }

# docspell-joex.conf
docspell.joex {
  app-id = "joex1"
  base-url = "http://docspell-joex:7878"
}
```

`localhost` in `base-url` means the joex container itself, so the restserver can't register it, and the queue never drains even though joex is healthy.

## What not to do

- **Don't raise `pool-size` to clear a backlog.** With office documents in the queue, more workers means more deadlock.
- **Don't set `-Xmx` above the container memory limit.** You trade a Java error for a silent kill.
- **Don't delete the files directory to clear stuck items.** The database still references them and the UI shows broken entries.
- **Don't run two joex instances with the same `app-id`.** They'll fight over job claims.

## Prevention

| Habit | Why |
|---|---|
| `pool-size = 1` unless you've moved to unoserver | Removes the deadlock class |
| `-Xmx` set explicitly, below the container limit | OOMs become readable Java errors |
| Watch the Job Queue after bulk uploads | Catches a stall while it's one document, not two hundred |
| Back up the Postgres database on a schedule | All metadata, tags and job history live there |

## FAQ

**Can I run joex on a different machine?**
Yes — that's the designed scaling model. Each needs a unique `app-id` and access to the database and file store.

**Will a stuck job retry forever?**
No: after `retries` attempts it moves to failed and stops.

**OCR quality is poor.**
Check the OCR language setting and the input DPI. 300 DPI is the practical target; below 200 accuracy drops sharply.

**Does cancelling a job lose the document?**
No. The file and its metadata remain; only the processing result is missing. Re-trigger processing from the item's menu.
