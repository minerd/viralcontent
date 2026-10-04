---
title: "Karakeep (Hoarder) Not Archiving? The Worker, Chrome and the Queue"
slug: karakeep-archiving-stuck
meta_description: "Bookmarks save but stay blank: no screenshot, no AI tags, no full text. Which of the four containers is failing, and how to tell from the logs."
updated: October 2026
cluster: round 13 (tech) — Karakeep GitHub issues
competition: LOW
---

# Karakeep (Hoarder) Not Archiving? The Worker, Chrome and the Queue

Karakeep saves a bookmark instantly — that's just a database row. Everything you actually want (title, screenshot, full text, tags) happens afterwards in a **worker** container talking to a **headless Chrome** container. A bookmark stuck as a bare URL means one of those two is down, not that saving failed.

Four containers, four distinct failures:

| Container | What it does | Symptom when it fails |
|---|---|---|
| `web` | UI and API | Nothing loads |
| `chrome` | Renders the page | No screenshot, no full text, title stays the raw URL |
| `meilisearch` | Search index | Saving works, search returns nothing |
| worker (in `web` or separate) | Runs the jobs | Everything stays pending forever |

## 1. Read the worker log first

```bash
docker compose logs -f web | grep -iE 'crawl|worker|chrome|error'
```

The useful lines look like `[Crawler][job_id] Starting crawling` followed by either a completion or a specific error. If you see *no* crawl lines at all after adding a bookmark, the worker isn't picking up jobs — skip to section 3.

## 2. Chrome connection failures

The most common error:

```
Failed to connect to the browser instance, will retry in 5 secs:
connect ECONNREFUSED 127.0.0.1:9222
```

`127.0.0.1:9222` is the giveaway: the worker is looking for Chrome on *itself*. In Docker Compose the address must be the service name:

```yaml
environment:
  BROWSER_WEB_URL: http://chrome:9222
```

Variations and what they mean:

- **`ECONNREFUSED` with the right hostname** — the Chrome container isn't running, or crashed. Check `docker compose ps` and its own log.
- **`Protocol error` / websocket closes immediately** — Chrome started but is being killed. Almost always memory. Headless Chrome rendering a heavy page wants ~500 MB–1 GB; on a 1 GB VPS it gets OOM-killed mid-render. `dmesg | grep -i oom` confirms it.
- **`net::ERR_NAME_NOT_RESOLVED` in the crawl result** — Chrome is fine, but can't resolve the site. If you run a local DNS blocker, the target may be blocked for the container.
- **Works for most sites, fails for a few** — those sites are blocking headless Chrome. Nothing to fix locally.

A Chrome container that keeps restarting also needs the right security flags; the stock compose sets them, and a hand-written compose that omits `--no-sandbox` will not start under most Docker configurations.

## 3. Jobs never get picked up

If no crawl lines appear:

- **`NEXTAUTH_SECRET` / `MEILI_MASTER_KEY` missing.** Karakeep's worker refuses to start without its required secrets and logs a startup error you'll miss if you only tail recent output. Check from the very beginning: `docker compose logs web | head -40`.
- **The data volume is read-only or full.** `df -h` and confirm the `DATA_DIR` mount is writable.
- **A stuck job at the head of the queue.** Open a bookmark, use **Refetch** / **Recrawl** on it. If one specific URL hangs every worker, deleting that bookmark unblocks the rest.

## 4. AI tagging specifically

Separate from crawling, with its own failure:

```yaml
environment:
  OPENAI_API_KEY: sk-...
  INFERENCE_TEXT_MODEL: gpt-4o-mini
```

Or for a local model:

```yaml
environment:
  OLLAMA_BASE_URL: http://ollama:11434
  INFERENCE_TEXT_MODEL: llama3.1
  INFERENCE_IMAGE_MODEL: llava
```

What goes wrong:

- **`OLLAMA_BASE_URL` pointing at `localhost`** — same mistake as Chrome. Use the service name, or the host's LAN IP if Ollama runs outside Docker.
- **The model isn't pulled.** `docker exec ollama ollama list` must show the exact tag you configured. A missing model gives a 404 that reads like an auth problem.
- **Context length.** A long article sent to a small local model overflows its context and the job fails. `INFERENCE_CONTEXT_LENGTH` exists for this.
- **Tagging is enabled but nothing is tagged** — check that you haven't set tagging to run only on manually triggered jobs, and use **Refetch** to re-run inference on an existing bookmark.

## What not to do

- **Don't re-add the bookmark to retry.** Use Refetch; re-adding creates a duplicate with the same failing job.
- **Don't delete the SQLite database to clear a stuck queue.** You lose every bookmark. Deleting the one offending bookmark is enough.
- **Don't run Chrome on a host with under 2 GB RAM and expect full-page screenshots.** This isn't tunable away.
- **Don't expose the Chrome container's 9222 port publicly.** A reachable DevTools endpoint is a remote code execution surface. Keep it internal to the compose network.

## Prevention

| Habit | Why |
|---|---|
| Use service names everywhere, never localhost | Removes the single largest cause |
| Watch the first 40 log lines after any config change | Startup validation errors scroll away fast |
| Give the host swap, even 1 GB | Turns Chrome OOM kills into slow renders |
| Keep single-file archives enabled for pages you care about | A screenshot is not a readable archive |

## FAQ

**Is Hoarder the same project?**
Yes — Karakeep is the renamed Hoarder. Old `hoarder/` image names and env var prefixes still appear in guides; the new ones are what current releases read.

**Can I archive paywalled pages?**
Only by giving Chrome a session, which the stock setup doesn't do. Browser-extension capture is the practical route.

**Search is empty though bookmarks exist.**
Meilisearch problem, not crawling. Check its container and that `MEILI_MASTER_KEY` matches on both sides, then re-index.

**Screenshots are blank white.**
Chrome rendered before the page painted. Increase the crawl timeout; some single-page apps need several seconds.
