---
title: "Navidrome Scrobbling Not Working: Last.fm, ListenBrainz and the Client Problem"
slug: navidrome-scrobbling-not-working
meta_description: "Plays don't reach Last.fm or ListenBrainz. Whether it's the server, the token, or your client not sending the scrobble at all."
updated: October 2026
cluster: round 13 (tech) — Navidrome GitHub and docs
competition: LOW
---

# Navidrome Scrobbling Not Working: Last.fm, ListenBrainz and the Client Problem

Navidrome can scrobble on your behalf, but only when the **client** tells it a track was played. A lot of "scrobbling is broken" turns out to be a client that never sends the Subsonic `scrobble` call. Settle that question first.

## 1. Does Navidrome know you played the track?

Open the Navidrome web UI and look at the track's **play count** and **last played**. If those don't increase after a full play from your app, Navidrome never received the scrobble, and nothing on the Last.fm side matters yet.

The web player always scrobbles. So:

- **Play count rises in the web UI, not from your app** → client problem (section 4).
- **Play count rises from the app too, but Last.fm shows nothing** → server-side credentials (sections 2–3).

That one check splits the problem in half.

## 2. Last.fm setup

Navidrome needs an API key and secret of its own, plus a per-user authorisation.

```yaml
environment:
  ND_LASTFM_ENABLED: "true"
  ND_LASTFM_APIKEY: your_api_key
  ND_LASTFM_SECRET: your_shared_secret
```

Then, **per user**, in the Navidrome UI: **Personal → Last.fm → Link**. This opens Last.fm, you approve, and you come back. Missing this step is the most common cause: the server is configured, no user is linked, and nothing scrobbles.

Things that break the link step:

- **`ND_BASEURL` wrong or unset behind a reverse proxy.** The callback returns to a URL Navidrome builds from this; if it's wrong, the approval round-trip fails or lands on a 404. Set it to the external path:

```yaml
  ND_BASEURL: /music      # if served at https://example.com/music
```

- **API key created as the wrong application type.** Create a standard API account at last.fm/api/account/create; the key and *shared secret* are both needed.
- **The link appears to work, then shows unlinked.** Usually a clock skew problem — Last.fm signs requests with a timestamp. Check `date` on the host; a container hours out of sync fails signature validation.

## 3. ListenBrainz setup

Simpler, because it's token-based:

```yaml
environment:
  ND_LISTENBRAINZ_ENABLED: "true"
```

Then per user: **Personal → ListenBrainz → paste your user token** from listenbrainz.org/profile. 

Failure modes:

- **Wrong token.** Use the *user token*, not an API key from another service.
- **Custom instance.** `ND_LISTENBRAINZ_BASEURL` must end in the API path; a bare hostname gives 404s.
- **Egress blocked.** Test from inside the container:

```bash
docker exec -it navidrome \
  wget -qO- https://api.listenbrainz.org/1/validate-token \
  --header="Authorization: Token YOUR_TOKEN"
```

A `valid: true` response means the token and the network are both fine, which points back at the client.

## 4. The client side

This is where most of these end up. The Subsonic API has a `scrobble` endpoint, and clients vary in whether and when they call it:

| Client behaviour | Effect |
|---|---|
| Scrobbles on play start | Counts tracks you skipped |
| Scrobbles at 50%/4 min | Correct, matches Last.fm's rules |
| Has its own Last.fm integration enabled too | **Double scrobbles** |
| Offline/cached playback | Often never scrobbles at all |

Two specific things to check in your app's settings:

- **Turn off the client's own Last.fm scrobbling** if you're using Navidrome's. Both on means duplicate entries, and people then disable the wrong one.
- **Offline mode.** Tracks played from the app's cache with no connection generally don't queue a scrobble for later. If most of your listening is offline, server-side scrobbling will always look broken, and a client with its own queueing scrobbler is the better architecture for you.

Check the Navidrome log while playing to see the call arrive:

```bash
docker logs -f navidrome | grep -i scrobble
```

## What not to do

- **Don't re-link repeatedly.** If the callback is broken, re-linking fails identically. Fix `ND_BASEURL` first.
- **Don't enable scrobbling in both the client and Navidrome.** Pick one.
- **Don't delete `navidrome.db` to reset play counts.** It holds playlists, ratings and play history; there's no reason to lose that over a scrobble problem.
- **Don't assume missing scrobbles are lost plays.** Navidrome's own play counts are intact; only the external service missed them.

## Prevention

| Habit | Why |
|---|---|
| Set `ND_BASEURL` correctly before linking anything | The OAuth callback depends on it |
| One scrobbler, documented in your notes | Prevents the duplicate-entry confusion later |
| Keep host time synced (NTP) | Signed API requests fail on skew |
| Check Navidrome's own play count first | Splits client from server in ten seconds |

## FAQ

**Can Navidrome backfill missed scrobbles?**
No. It scrobbles in real time; there's no replay of history to Last.fm.

**Does it scrobble "now playing" too?**
Yes, when the client sends the appropriate call, and some clients send one but not the other.

**Multiple users, one Last.fm account?**
Each Navidrome user links separately. Sharing one Last.fm account across users will merge everyone's listening.

**Scrobbles stop after a Navidrome update.**
Check whether `ND_LASTFM_ENABLED` is still being read — env var names have changed across major versions, and an unrecognised one is ignored silently.
