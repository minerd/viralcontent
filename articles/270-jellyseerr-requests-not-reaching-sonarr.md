---
title: "Jellyseerr Requests Not Reaching Sonarr or Radarr? Default Server and Root Folder"
slug: jellyseerr-requests-not-reaching-sonarr
meta_description: "Approved requests that never appear in Sonarr. The default-server setting, missing root folders, Docker hostnames instead of localhost, and the stuck-request behaviour."
updated: October 2026
cluster: round 12 (tech) — Jellyseerr/Seerr GitHub issues and discussions
competition: LOW
---

# Jellyseerr Requests Not Reaching Sonarr or Radarr? Default Server and Root Folder

A request is approved in Jellyseerr, shows as *Processing*, and nothing ever appears in Sonarr or Radarr.

## 1. Is a default server set?

The most-reported cause, and the least obvious: **Settings → Services → Radarr/Sonarr → edit each server → enable "Default Server"**.

Without it, requests made through some paths (notably the integrated search, or automatic approvals) have nowhere to go, while requests made directly in the web UI appear to work. That split behaviour — "works in Jellyseerr but not from the integration" — is the signature.

Also set, per server:
- **Default quality profile**
- **Default root folder** — a missing root folder means the request has nowhere to be written and silently fails
- **Language profile** (Sonarr)
- **Season folders / series type** defaults

Then use **Test** on the service. A green test only proves connectivity, not that defaults exist, so check both.

## 2. Use container names, not localhost

In Docker, `localhost` means the Jellyseerr container itself:

```
http://sonarr:8989        ✅ same docker network
http://192.168.1.50:8989  ✅ host IP
http://localhost:8989     ❌
```

Confirm from inside the container:

```bash
docker exec -it jellyseerr wget -qO- http://sonarr:8989/api/v3/system/status?apikey=KEY
```

If that fails, fix networking before anything else — put them on the same Docker network, or use host IPs.

## 3. API key and base URL

- Copy the key again from **Sonarr → Settings → General → Security**. A truncated paste is common
- If Sonarr runs on a **base URL** (`/sonarr`), Jellyseerr's URL must include it
- Behind a reverse proxy with HTTPS: verify the certificate is trusted by the Jellyseerr container, or use the internal HTTP address instead — there's no reason to proxy a container-to-container call

## 4. The stuck-request behaviour

Documented: if Jellyseerr can't reach Sonarr at the moment a request is approved — Sonarr down, network blip — the request is **stuck forever**. There's no automatic retry, and feature requests exist for exactly this.

So after fixing the connection:
- Find the affected requests in **Requests**
- **Delete and re-request**, or decline and re-approve
- Don't expect them to drain on their own

That also means: check Sonarr's uptime around the time requests stopped working. A nightly container restart that overlaps auto-approvals will quietly lose them.

## 5. It reached Sonarr but nothing downloaded

Different problem, and the handover worked. Look in **Sonarr**:

- Series added but **unmonitored**, or the season not monitored
- **Quality profile** has no cutoff that matches anything available
- **Indexers** failing (Prowlarr sync, or indexer errors)
- Interactive search shows **rejection reasons** — read them; they're explicit
- A **root folder** that Sonarr can't write to

The dividing line: if the series/movie exists in Sonarr, Jellyseerr did its job and you're debugging Sonarr.

## 6. Watch the logs during a request

```bash
docker compose logs -f jellyseerr
# and in another shell
docker compose logs -f sonarr
```

Make a request and watch both. You'll see either the outgoing call and its error, or nothing at all from Jellyseerr — which tells you whether it even tried.

## Prevention

1. **Default Server, quality profile and root folder** set on every service entry
2. **Container names or host IPs**, never localhost
3. Keep **Sonarr/Radarr up** when auto-approval is enabled; avoid restart windows that overlap
4. **Pin image tags** for all of them
5. After any change to Sonarr's URL, key or root folders, **re-test and re-save** the Jellyseerr service entry

## FAQ

**Why does requesting in the web UI work but not from search integrations?**
No default server is set. That's the single most common cause.

**Do stuck requests retry automatically?**
No. Re-request them after fixing the connection.

**Should Jellyseerr reach Sonarr through my reverse proxy?**
No need — use the internal address. Fewer moving parts.

**The request reached Sonarr but nothing downloads.**
That's a Sonarr problem: monitoring, quality profile, indexers. Use interactive search to see rejection reasons.
