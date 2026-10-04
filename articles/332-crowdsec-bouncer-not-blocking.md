---
title: "CrowdSec Decisions Exist But Nothing Is Blocked"
slug: crowdsec-bouncer-not-blocking
meta_description: "cscli decisions list shows bans and traffic still gets through. The bouncer registration, the Docker network problem, and where the real client IP goes."
updated: October 2026
cluster: round 13 (tech) — CrowdSec GitHub and Discourse
competition: LOW
---

# CrowdSec Decisions Exist But Nothing Is Blocked

CrowdSec has two halves. The **engine** reads logs and makes decisions. A **bouncer** enforces them. A working engine with a broken bouncer looks like total protection and provides none.

```bash
docker exec crowdsec cscli decisions list
docker exec crowdsec cscli bouncers list
```

Decisions present + no bouncers, or a bouncer with an old "last pull" timestamp, is the whole diagnosis.

## 1. Is the bouncer registered and pulling?

```
─────────────────────────────────────────────────
 Name            IP          Valid  Last API pull
─────────────────────────────────────────────────
 traefik-bouncer 172.18.0.5  ✔️      2026-10-04T09:41
```

**No bouncer listed** → it was never registered. Generate a key and give it to the bouncer:

```bash
docker exec crowdsec cscli bouncers add traefik-bouncer
```

**Listed but "last API pull" is hours old** → the bouncer can't reach the LAPI, or its key is wrong. Check its own log; a 403 means the key, a timeout means networking.

**Listed, pulling, still not blocking** → section 3.

## 2. The bouncer must reach the LAPI

```bash
docker exec traefik-bouncer wget -qO- --header="X-Api-Key: YOURKEY" \
  http://crowdsec:8080/v1/decisions
```

- `crowdsec:8080` only resolves if both containers share a Docker network. A bouncer on a different network can't see it.
- The LAPI must listen on an address the bouncer can reach. `127.0.0.1:8080` inside the CrowdSec container is unreachable from another container:

```yaml
# config.yaml
api:
  server:
    listen_uri: 0.0.0.0:8080
```

- If LAPI is on another host, it needs to be reachable and ideally TLS-protected. An unauthenticated LAPI on a LAN is a decision-injection surface.

## 3. The real client IP

This is where a correctly-registered bouncer still fails to protect anything, and it's the most consequential mistake.

If your reverse proxy is behind Cloudflare, another proxy, or a load balancer, **every request arrives with the proxy's IP**. CrowdSec then:

- Parses logs full of the proxy's IP
- Decides to ban the proxy
- Bans everyone, or (if the proxy IP is whitelisted) bans nobody

Fix it at the proxy, so logs and the bouncer both see the true client:

**Traefik** — trust the forwarder:

```yaml
entryPoints:
  websecure:
    address: ":443"
    forwardedHeaders:
      trustedIPs:
        - "173.245.48.0/20"
        - "103.21.244.0/22"
        # ... Cloudflare's published ranges
```

**nginx** — real_ip module:

```nginx
set_real_ip_from 173.245.48.0/20;
real_ip_header CF-Connecting-IP;
real_ip_recursive on;
```

Then confirm your access log contains client IPs, not proxy IPs:

```bash
tail -5 /var/log/nginx/access.log
```

Until that line shows real client addresses, CrowdSec cannot work correctly no matter how it's configured.

Also check the whitelist: CrowdSec ships whitelists for private ranges. If your proxy's IP falls in one (very common in Docker, where everything is `172.x`), decisions against it are discarded — which is why "it detects nothing" and "it's banning my proxy" are two faces of the same problem.

```bash
docker exec crowdsec cscli alerts list
```

Alerts with the proxy's IP as the source confirm it.

## 4. Is the engine seeing the logs at all?

```bash
docker exec crowdsec cscli metrics
```

The **Acquisition Metrics** table shows lines read per source. A source with 0 lines read means the log isn't being parsed:

- The log file isn't mounted into the CrowdSec container
- `acquis.yaml` points at the wrong path or the wrong `type`
- Log rotation replaced the file and CrowdSec is holding the old inode (restart, or use a glob)

```yaml
# acquis.yaml
filenames:
  - /var/log/nginx/*.log
labels:
  type: nginx
```

And the **Parser Metrics** table: lines read but 0 parsed means the wrong `type` label or a log format the parser doesn't recognise (a custom `log_format` in nginx will not parse with the stock parser).

## 5. Verify end to end

```bash
# add a test ban on your own IP from another network
docker exec crowdsec cscli decisions add --ip 203.0.113.45 --duration 5m --type ban
```

Then try to reach the service from that address. If it's not blocked, the bouncer is the problem, not detection. This test takes thirty seconds and settles the engine-versus-bouncer question definitively.

```bash
docker exec crowdsec cscli decisions delete --ip 203.0.113.45
```

## What not to do

- **Don't assume a running CrowdSec container means you're protected.** Without a verified bouncer it's a log analyser.
- **Don't whitelist broadly to stop false positives.** Fix the real-IP problem instead; a whitelist covering your proxy disables protection for all traffic through it.
- **Don't rely on the console/CTI dashboard as proof of blocking.** It shows decisions, not enforcement.
- **Don't run only the firewall bouncer behind Cloudflare.** Blocking Cloudflare's IPs at the firewall blocks all your traffic; the application-level bouncer is the right one there.

## Prevention

| Habit | Why |
|---|---|
| Test with a deliberate ban after every change | The only way to know enforcement works |
| Real client IP configured before CrowdSec | Everything downstream depends on it |
| `cscli metrics` after any log or rotation change | Catches silent acquisition failures |
| One bouncer per enforcement point, each verified | A registered bouncer that never pulls is worse than none |

## FAQ

**Do I need the firewall bouncer and the proxy bouncer?**
They cover different layers. Behind Cloudflare, the proxy/application bouncer is what works; the firewall bouncer is for traffic that reaches the host directly.

**Does it replace fail2ban?**
It does the same job with shared threat intel and a cleaner multi-service model. Running both on the same logs means duplicate bans, which is harmless but confusing.

**Decisions expire too quickly.**
`--duration` on manual bans, and the scenario's own duration for automatic ones. Profiles in `profiles.yaml` control escalation for repeat offenders.

**Can I see what would have been blocked?**
Set the profile to a non-blocking remediation (e.g. captcha or log-only) while tuning. That's the safe way to assess false positives.
