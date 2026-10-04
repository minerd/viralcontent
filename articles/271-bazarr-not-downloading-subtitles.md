---
title: "Bazarr Not Downloading Subtitles? Language Profiles and Provider Limits"
slug: bazarr-not-downloading-subtitles
meta_description: "Manual search finds subtitles but automatic download does nothing. Forced-subtitle profile traps, provider throttling, adaptive searching and path mapping."
updated: October 2026
cluster: round 12 (tech) — Bazarr GitHub issues only
competition: LOW
---

# Bazarr Not Downloading Subtitles? Language Profiles and Provider Limits

The tell-tale symptom: **manual search for a single language works, automatic download doesn't.** That points at the language profile, not at the providers.

## 1. The multi-language / forced-subtitle profile trap

Reported behaviour: when a language profile contains **multiple languages including Forced**, Bazarr finds nothing automatically — but searching each language manually works.

What to do:
- Simplify the profile: **one language, not forced**, and confirm automatic download starts working
- Then add complexity back one step at a time
- If you want forced subtitles, give them their **own profile** or their own cutoff rather than mixing them into one list
- Check the **"Must contain"/"Must not contain"** filters on the profile — a stray value there silently excludes everything
- Confirm the profile is actually **assigned** to the series/movies (Series → mass-edit → set profile)

A profile that exists but isn't assigned is a surprisingly common cause of "nothing happens".

## 2. Provider state

Bazarr depends on third-party subtitle providers, and they rate-limit, break and require accounts:

- **Settings → Providers**: are any showing errors or throttled? Bazarr flags throttled providers and stops using them temporarily
- **OpenSubtitles** needs an account; the free tier has daily download limits that you will hit on a big library
- A provider's API change breaks it until Bazarr updates — check the version's issues
- Having **more providers** enabled is better for coverage; having one broken provider is enough to skew results

The **History** and **Logs** pages tell you which provider answered and which refused. Read those before changing settings.

## 3. Adaptive searching is doing its job

Bazarr's **adaptive searching** deliberately backs off repeated searches for items it couldn't find subtitles for, with increasing intervals. That's a feature — it protects providers — but it reads as "Bazarr stopped trying".

- For a specific item, use **manual search** to bypass it
- Reported alongside this: after some Sonarr/Bazarr version combinations, **every sync re-queues all missing subtitles**, which is the opposite problem and burns your provider quota. If you see that, check the issues for your versions

## 4. Path mapping

Bazarr must see the **same files at the same paths** as Sonarr/Radarr. In Docker, this is the usual mistake:

```bash
docker exec -it bazarr ls -la "/tv/Some Show/Season 01"
```

If that path doesn't exist from Bazarr's point of view, it can't write subtitles next to the video — and it reports confusing failures instead of a clear error. Fix the mounts so all three containers share one layout, or set **path mappings** in Bazarr's settings for Sonarr and Radarr separately.

Also check **write permissions**: Bazarr needs to write into the media folder (PUID/PGID matching), and a read-only media mount means it can never save anything.

## 5. The series/episode isn't eligible

- **Episode not monitored** in Sonarr → Bazarr may not consider it
- The **cutoff** is already met by an existing subtitle file Bazarr detected
- **Embedded subtitles** present and "use embedded subtitles" enabled → Bazarr considers the requirement satisfied. That setting surprises people
- **Upgrade** settings off, so an existing poor subtitle is never replaced

## 6. After an update

- **Pin the image tag**
- Check **System → Status** for version and provider state
- Read **System → Logs** at debug level while a search runs — Bazarr is verbose and names the reason
- Roll back if a release broke providers for you; these are frequent and quickly fixed

## Prevention

1. **Simple language profiles**, assigned explicitly
2. **Several providers**, with an OpenSubtitles account configured
3. **Identical paths** across Sonarr/Radarr/Bazarr
4. Leave **adaptive searching on** — and use manual search when you're impatient
5. Watch for provider quota rather than blaming Bazarr

## FAQ

**Why does manual search work and automatic not?**
Almost always the language profile — especially multi-language profiles that include Forced.

**Why did Bazarr stop searching for an old episode?**
Adaptive searching backing off. Manual search still works.

**Does it need write access to my media folder?**
Yes, unless you store subtitles elsewhere. A read-only mount blocks everything.

**My provider says too many requests.**
You hit a daily limit. Add providers, or an account with a higher quota.
