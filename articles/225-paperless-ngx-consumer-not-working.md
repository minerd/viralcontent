---
title: "Paperless-ngx Not Consuming Documents? Polling, Paths and Ignore Patterns"
slug: paperless-ngx-consumer-not-working
meta_description: "Files sit in the consume folder and nothing happens. The inotify-on-network-share problem, the Docker path mistake, regex ignore patterns and a dead task worker."
updated: October 2026
cluster: round 10 (tech) — GitHub discussions and the official docs
competition: LOW
---

# Paperless-ngx Not Consuming Documents? Polling, Paths and Ignore Patterns

Documents land in the consume folder and just sit there. No error, no document, nothing in the UI. Four causes cover nearly every report.

## 1. The consume folder is on a network share (the big one)

Paperless-ngx watches the folder with **inotify** — a Linux kernel feature that only fires for local filesystems. **NFS and SMB shares do not generate inotify events**, so a folder you write to from another machine never triggers anything.

This is the single most common cause, and the fix is one variable:

```
PAPERLESS_CONSUMER_POLLING=30
```

Set it to a positive number of seconds and Paperless switches from filesystem notifications to **polling**. Also useful:

```
PAPERLESS_CONSUMER_POLLING_RETRY_COUNT=5
PAPERLESS_CONSUMER_POLLING_DELAY=5
```

Tell-tale sign that this is your problem: files dropped **inside the container** (or on the host's local disk) get consumed, but files written **over the network** don't.

## 2. Pointing `PAPERLESS_CONSUMPTION_DIR` somewhere that isn't mounted

In Docker, the container already has a consume directory at **`/usr/src/paperless/consume`**, and your compose file bind-mounts a host folder onto it. If you then set `PAPERLESS_CONSUMPTION_DIR` to some other path, Paperless watches a directory that your files never reach.

**For a standard Docker install: don't set `PAPERLESS_CONSUMPTION_DIR` at all.** Mount your folder onto `/usr/src/paperless/consume` and leave the default alone:

```yaml
volumes:
  - /srv/scans:/usr/src/paperless/consume
```

Verify from inside the container:
```
docker compose exec webserver ls -la /usr/src/paperless/consume
```
If your file isn't listed there, it's a mount problem, not a Paperless problem.

## 3. Ignore patterns are eating your files

`PAPERLESS_CONSUMER_IGNORE_PATTERNS` filters filenames. In Paperless-ngx **3.x these are regular expressions, not shell globs** — so a pattern copied from an older config or a blog post can silently match everything.

Check the variable, and if it contains anything you didn't write deliberately, empty it and test with one file. Default behaviour also skips dotfiles and some OS metadata files (`.DS_Store`, `Thumbs.db`, `@eaDir` on Synology).

## 4. The broker or the task worker is dead

Paperless processes documents **asynchronously**. The consumer can see the file and still produce nothing if the queue isn't being worked.

```
docker compose ps                     # are broker/redis and webserver both up?
docker compose logs -f webserver      # is the consumer scanning? does it mention the file?
docker compose logs -f broker
```

Look for:
- Redis/broker **not running** or unreachable
- The worker **crashing in a loop** (often OOM on a low-memory box during OCR)
- Tasks visible in the UI's **Tasks** page sitting in *pending* forever
- `redis` connection errors in the log at startup

A Raspberry Pi doing OCR on a 60-page scan can simply run out of memory; in that case the worker dies and nothing else explains itself.

## 5. Permissions

The container runs as a specific UID/GID. If the consume folder's files aren't readable (or the folder isn't writable, since Paperless deletes files after consuming), everything stalls.

- Match **`USERMAP_UID` / `USERMAP_GID`** in your environment to the owner of the host folder
- The folder must be **writable**, not just readable
- On SELinux systems, add `:z` to the bind mount
- Nextcloud/Syncthing-created files sometimes arrive owned by another user — check `ls -la` on the host

## Diagnostic order

1. `ls` the consume directory **inside the container**
2. `docker compose logs -f webserver` while you drop a file in
3. If the log says nothing at all → inotify/polling or mount path
4. If the log says it saw the file but nothing appears → broker/worker, or the Tasks page has the error
5. If some files work and others don't → ignore patterns, permissions, or a file type without OCR support
6. Check the **Tasks** page in the UI — failures are recorded there with messages

## Things to avoid

- Don't write files **directly into** the consume folder over a long network copy — partial files get picked up. Copy to a temp name and rename, or use the folder-import pattern Paperless documents
- Don't set both a custom `PAPERLESS_CONSUMPTION_DIR` and a bind mount at the default path
- Don't chase OCR settings when the consumer never saw the file

## FAQ

**Does Paperless-ngx work with an NFS or SMB consume folder?**
Yes, but only with polling enabled — inotify doesn't work there.

**Where should my consume folder be mounted in Docker?**
On `/usr/src/paperless/consume`, with no custom `PAPERLESS_CONSUMPTION_DIR`.

**Why do some files get consumed and others ignored?**
Ignore patterns (regex in 3.x), unsupported file types, or permissions on specific files.

**Files disappear but no document appears.**
They were consumed and the task failed. Check the Tasks page and the worker log.
