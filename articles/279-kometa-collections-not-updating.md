---
title: "Kometa Collections Not Updating in Plex? Manual vs Smart, and the Run That Didn't"
slug: kometa-collections-not-updating
meta_description: "Collections that stay stale, keep removed items, or never appear. Why manual collections only change when Kometa runs, TMDB matching failures and cache problems."
updated: October 2026
cluster: round 12 (tech) — Kometa GitHub discussions and wiki
competition: LOW
---

# Kometa Collections Not Updating in Plex? Manual vs Smart, and the Run That Didn't

Start with the distinction that explains half the reports:

- **Manual collections** (built by Kometa from a list/builder) change **only when Kometa runs**
- **Smart collections** (Plex-side filters) update **in real time** as your library changes

If you expected a manual collection to pick up a new film the moment it was added, it won't. That's design, not breakage.

## 1. Did the run actually succeed?

```bash
docker compose logs --tail=200 kometa
# or read the log file
less config/logs/meta.log
```

Look for:
- The collection's name and what it did (added/removed/left alone)
- `Finished` with a summary at the end, versus a traceback
- The **run time** — if your container exits immediately and you expect a schedule, check `KOMETA_RUN`/`KOMETA_SCHEDULE` and the timezone

A Kometa that errors on an earlier collection file can skip everything after it. Read from the top, not the bottom.

## 2. Items that should be removed but stick

Documented behaviour: when a **manual collection built from a `plex_search`** returns **no items** during a run, Kometa doesn't delete the collection or remove items that no longer qualify. The collection quietly keeps yesterday's contents.

Also reported: items removed from a **label/tag** stay in the collection, and once the label is gone Kometa may ignore the collection entirely.

Options:
- Set **`delete_not_scheduled`** / `sync_mode: sync` appropriately so the collection is reconciled rather than appended to
- Use `sync_mode: sync` for collections where removal matters (append-only is the other mode, and it's the default in some templates)
- For label-driven collections, keep the label even when empty, or build from a different source

## 3. TMDB/TVDB matching failures

Reported: during library cache builds, many entries show **no TMDB match**, appearing as `plex://` or `local://` ids. Builders that rely on TMDB/IMDb lists then match nothing, and the collection comes out empty.

Check:
- Items in Plex with **no agent match** or locked metadata — fix them in Plex first
- Your **TMDB API key** present and valid in `config.yml`
- Rate limiting: large libraries hammering TMDB get throttled; Kometa logs it
- A library using the **legacy Plex agent** rather than the Plex Movie/Series agent — match quality is much worse

Fixing the Plex-side match is the real solution; Kometa can only work with the ids it's given.

## 4. Cache and overlays

- Kometa's **cache database** can hold stale ids after a library rebuild. Clear it (`config/cache.db` — stop Kometa first) and re-run
- **Overlays** are a separate operation with their own reset behaviour; a collection updating while posters don't is normal if overlays aren't scheduled
- A reported fix for stubborn state: **restart the Plex container** (Plex caches its own collection state aggressively)

## 5. The collection file isn't being read

- Check `config.yml`'s **`collection_files`** paths actually point at your YAML
- A **YAML syntax error** in one file means that file is skipped — Kometa says so in the log
- Files on a **different mount** inside the container than you think
- The library name in `config.yml` must match Plex's library name **exactly**

## 6. Schedules

Kometa's own `schedule:` keys (weekly, monthly, range) mean a collection may be **deliberately** not scheduled today. The log says `not scheduled for today`. That's not a failure — and it's the explanation for "it worked last week".

## Prevention

1. Read the **log** after every run for a while; it's verbose and honest
2. Use **`sync_mode: sync`** where removal matters
3. Keep **TMDB matching clean** in Plex; Kometa inherits your metadata quality
4. Keep collection files in **git** so a bad edit is a diff away
5. **Pin the image tag**

## FAQ

**Why don't my collections update when I add a film?**
Manual collections only update when Kometa runs. Smart collections update live.

**Why do removed items stay?**
Append-only sync mode, or an empty builder result that Kometa won't act on destructively.

**Everything is empty after a library rebuild.**
Matching/ids changed — clear the cache and fix Plex-side metadata matches.

**Does restarting Plex help?**
Sometimes, for stale collection state. It's a reported fix, not a first step.
