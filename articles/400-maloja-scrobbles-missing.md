---
title: "Maloja: Scrobbles Visible in multi-scrobbler But Not Arriving"
slug: maloja-scrobbles-missing
meta_description: "multi-scrobbler shows the play and Maloja doesn't record it. Client initialisation, the time-cutoff that drops backlogs, and the retry queue."
updated: October 2026
cluster: round 14 (tech) — FoxxMD/multi-scrobbler GitHub issues
competition: LOW
---

# Maloja: Scrobbles Visible in multi-scrobbler But Not Arriving

multi-scrobbler detecting a play and Maloja not recording it is a **client-side** problem in multi-scrobbler, not a source problem. The logs separate the two halves cleanly:

```bash
docker logs multi-scrobbler --tail 100 | grep -iE 'maloja|scrobble|queue|client'
```

- `Discovered => ...` — the source saw the play
- `Scrobbled (Source) => ...` — it was sent to a client
- `Maloja client not yet initialized` — the client never came up

## 1. "Maloja client is not yet initialized"

A documented and common state: scrobbles are discovered, the Maloja client isn't ready, and plays are dropped or queued.

```yaml
services:
  multi-scrobbler:
    image: foxxmd/multi-scrobbler
    environment:
      - MALOJA_URL=http://maloja:42010
      - MALOJA_API_KEY=your-api-key
      - TZ=Europe/Istanbul
    volumes:
      - ./config:/config
```

Checks:

- **`MALOJA_URL` reachable from the container.** Not `localhost`:

```bash
docker exec multi-scrobbler wget -qO- http://maloja:42010/apis/mlj_1/serverinfo
```

- **The API key** comes from Maloja's admin page. An invalid key gives a 403 that surfaces as an initialisation failure.
- **Maloja started after multi-scrobbler.** The reported remedy is simply to restart multi-scrobbler once Maloja is up:

```bash
docker restart multi-scrobbler
```

This is the fix in most cases, and it's worth adding ordering so it doesn't recur:

```yaml
    depends_on:
      maloja:
        condition: service_started
    restart: unless-stopped
```

A related note: the initialisation failure has been traced to multi-scrobbler's **reconnect mechanism** rather than to Maloja. So if Maloja is demonstrably healthy and Last.fm works from the same instance, restarting the scrobbler rather than debugging Maloja is the right move.

## 2. The time cutoff that silently drops backlogs

This one explains the most confusing reports. multi-scrobbler will not submit a scrobble **older than the oldest scrobble already present in the client**. The intent is to avoid duplicating history; the effect is that a backlog of offline plays is discarded.

Consequences:

- **Offline playback** on a phone (Symfonium against Navidrome, for example) that syncs later may never reach Maloja, because by the time it's reported, newer scrobbles already exist.
- **Backlogged Subsonic scrobbles** are dropped for the same reason — a documented bug.

What helps:

- Keep the scrobbler running continuously so the window never opens.
- For a known backlog, import it into Maloja directly rather than through multi-scrobbler. Maloja accepts imports:

```bash
docker exec maloja maloja import /path/to/scrobbles.csv
```

- Check whether your version has a setting to allow older scrobbles; where it exists, enabling it is the clean fix.

## 3. The retry queue

When a submission fails, multi-scrobbler queues it and retries **every 5 minutes for a limited number of attempts**, then gives up. So:

- A Maloja outage of under half an hour usually loses nothing
- A longer outage loses the plays in between
- The log records each retry, so a queue that's draining looks like repeated attempts rather than failures

```bash
docker logs multi-scrobbler --tail 200 | grep -iE 'retry|deadletter|gave up'
```

Dead-lettered scrobbles are visible in the web UI in recent versions, where you can retry them manually.

## 4. Data-format errors

```
Cannot read property 'album' of undefined
```

Reported for Spotify → Maloja: a track with no album (a single, a local file, a podcast) breaks the payload construction. Nothing to configure; it's a source-data shape the client didn't expect. Updating multi-scrobbler is the fix, and reporting the specific track type helps.

Similar: tracks with very long titles, or non-Latin characters in a field Maloja validates strictly, have each produced submission failures. The log names the field.

## 5. Source-specific gaps

- **Plex** not scrobbling while Jellyfin works: Plex's webhook needs Plex Pass, and the webhook URL must point at multi-scrobbler's endpoint. Check that the webhook is firing at all.
- **Subsonic/Navidrome sources** poll the server's now-playing, which misses plays that happened while the scrobbler was down (section 2).
- **Jellyfin** needs its webhook plugin configured, and the "ignore" filters in multi-scrobbler must not exclude your user or library.

## 6. Arriving but shown wrong in Maloja

Different problem. Maloja normalises artist and title aggressively, and a track can land under a merged artist. Maloja's rules files control this:

```
/config/rules/
```

Fix the artist with Maloja's own merge/rename tooling rather than the scrobbler.

## What not to do

- **Don't debug Maloja when Last.fm works from the same scrobbler.** The client is the variable.
- **Don't expect offline plays to backfill.** The time cutoff is deliberate.
- **Don't run two scrobblers against the same source and client.** You'll double-count.
- **Don't delete Maloja's database to fix duplicates.** It has merge tooling for that.

## Prevention

| Habit | Why |
|---|---|
| `restart: unless-stopped` and start ordering | Covers the initialisation race |
| Scrobbler running continuously | The time cutoff never bites |
| `TZ` set on both containers | Timestamps that line up |
| Back up Maloja's data directory | Your listening history exists nowhere else |

## FAQ

**Can I scrobble to Maloja and Last.fm at once?**
Yes — multiple clients, one source. That's the point of the tool.

**Does Maloja have its own scrobble endpoint?**
Yes, Last.fm-compatible, so some players can submit directly without multi-scrobbler.

**Import from Last.fm?**
Maloja's importer handles Last.fm and Spotify exports.

**Plays counted twice.**
Two sources reporting the same playback (a Jellyfin webhook plus a Subsonic poll). Disable one.
