---
title: "Traefik Returning 404 After an Update? No Router Rule Matched"
slug: traefik-404-after-update
meta_description: "Traefik's 404 means no router matched the request. The v2 to v3 label changes, missing service ports, provider networks and how to read the dashboard to find it."
updated: October 2026
cluster: round 11 (tech) — Traefik community forum threads only
competition: LOW
---

# Traefik Returning 404 After an Update? No Router Rule Matched

Everything worked, you updated Traefik, and now every host returns a bare **`404 page not found`** — including the dashboard.

**That 404 comes from Traefik itself and means exactly one thing: no router rule matched the request.** The backend was never contacted. So stop looking at the application and start looking at whether Traefik can see a router for that hostname at all.

## Step 1: look at the dashboard (or the API)

```
http://traefik-host:8080/dashboard/
# or
curl -s http://traefik-host:8080/api/http/routers | jq '.[].name'
curl -s http://traefik-host:8080/api/overview | jq
```

- **Router missing entirely** → the provider isn't seeing your container/config (steps 2–4)
- **Router present but shows an error** → the rule or service is malformed (step 5)
- **Router present and healthy, still 404** → the request isn't arriving the way you think (step 6)

If the dashboard itself 404s, that's the same problem applied to the dashboard's own router — the API/dashboard config changed between versions, and `--api.insecure=true` (or a proper router for it) must be present.

## Step 2: the v2 → v3 migration catches almost everyone

Traefik v3 changed rule syntax and several option names. If you jumped major version, your labels may be silently invalid:

- **Backtick quoting** is required in rules: `Host(\`app.example.com\`)` — in docker-compose, mind the YAML escaping
- **`PathPrefix`** semantics and the removal of some matchers
- Matchers are now **case-sensitive** in places v2 tolerated
- Old `Query`, `Headers` and regex forms changed shape
- Static config keys moved (`--providers.docker` options, entrypoint definitions)

Traefik logs invalid rules at startup. Run with `--log.level=DEBUG` once and read the first fifty lines — it names the label it rejected.

Check the official v2→v3 migration notes for your exact labels rather than guessing; this is the single most common cause of a post-update total 404.

## Step 3: is the provider watching the right thing?

**Docker provider:**
- `--providers.docker.exposedByDefault=false` plus a container missing `traefik.enable=true` = invisible
- Traefik must share a **Docker network** with the container. A container on a different compose project's default network cannot be reached, and Traefik then skips or fails it
- Set `--providers.docker.network=proxy` explicitly when containers sit on several networks, or Traefik picks the wrong IP
- Docker **socket access**: after an update to a socket-proxy or a permissions change, Traefik can start with no containers at all. The log says so

**File provider:**
- `--providers.file.directory` still mounted? A changed volume path means an empty configuration and a 404 for everything
- `--providers.file.watch=true` if you edit files live

## Step 4: inspect the labels as Docker sees them

Not as you wrote them — as they ended up:

```bash
docker inspect <container> --format '{{json .Config.Labels}}' | jq
```

Look for:
- Labels that didn't get **variable substitution** (a literal `${DOMAIN}` in the rule)
- A **typo in the router/service name** so the router points at a service that doesn't exist
- Missing `traefik.http.services.<name>.loadbalancer.server.port` — Traefik can't guess the port when the image exposes several, and the router then has no working service
- `traefik.enable` spelled as something else

A minimal, correct set:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.app.rule=Host(`app.example.com`)"
  - "traefik.http.routers.app.entrypoints=websecure"
  - "traefik.http.routers.app.tls.certresolver=le"
  - "traefik.http.services.app.loadbalancer.server.port=8080"
```

## Step 5: entrypoints

A router bound to an entrypoint that no longer exists never matches:

- Did your **entrypoint names** change (`web`/`websecure` vs `http`/`https`)? Router labels must use the current names
- Are the **ports published** on the Traefik container for those entrypoints?
- Is there a **redirect** from web to websecure that's looping or dropping the host?

## Step 6: the request itself

- Are you hitting the **hostname** in the rule, or the IP? `Host()` rules don't match an IP request — that's a legitimate 404
- Is **DNS** pointing where you think? `curl -H "Host: app.example.com" http://traefik-ip/` bypasses DNS and tells you instantly whether routing works
- Behind Cloudflare: is it reaching Traefik at all, and with the right `Host` header?
- **Trailing path** differences if you use PathPrefix with `stripPrefix`

## The five-minute version

```bash
docker logs traefik 2>&1 | head -50                      # rejected config at startup
curl -s localhost:8080/api/http/routers | jq '.[]|{name,rule,status,service}'
docker inspect <app> --format '{{json .Config.Labels}}' | jq
curl -H "Host: app.example.com" http://127.0.0.1/ -v     # routing without DNS
```

Those four commands locate it nearly every time.

## FAQ

**Why does Traefik 404 instead of showing an error?**
Because from Traefik's point of view there's nothing wrong — no rule matched, so it has nothing to serve.

**I upgraded v2 → v3 and everything 404s.**
Rule syntax and option names changed. Run at DEBUG level and fix the labels it rejects.

**The dashboard 404s too.**
Same cause, applied to the dashboard router. Check the api/dashboard configuration for your version.

**Router shows in the dashboard but still 404.**
Check the entrypoint, the service port, and whether the request's Host header is what you think it is.
