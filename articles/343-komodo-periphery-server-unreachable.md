---
title: "Komodo: Periphery Server Unreachable"
slug: komodo-periphery-server-unreachable
meta_description: "Komodo Core shows a server as unreachable, or deploys fail at the agent. Passkeys through env files, the SSL cert, and the reconnect backoff."
updated: October 2026
cluster: round 13 (tech) — Komodo GitHub issues
competition: LOW
---

# Komodo: Periphery Server Unreachable

Komodo has a **Core** (the UI and database) and a **Periphery** agent per managed host. "ServerUnreachable" means Core can't talk to an agent, and there are four causes — one of which is a Docker Compose env-file subtlety that catches almost everyone.

## 1. The passkey problem

Core authenticates to Periphery with a shared passkey. If they don't match, you get ServerUnreachable with no further detail.

The subtlety: **`docker stack deploy` and some Compose configurations do not resolve variable references from a separate env file into the service's environment.** So this looks right and isn't:

```yaml
# compose.yaml
services:
  periphery:
    environment:
      - PERIPHERY_PASSKEYS=${PASSKEY}      # may resolve to empty
env_file: compose.env
```

Put the value where it's definitely read — inline in the compose file, or via `environment:` with a literal:

```yaml
services:
  periphery:
    image: ghcr.io/moghtech/komodo-periphery:latest
    environment:
      PERIPHERY_PASSKEYS: "your-long-random-passkey"
      PERIPHERY_PORT: 8120
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /proc:/proc
    network_mode: host
    restart: unless-stopped
```

Then confirm what the container actually has:

```bash
docker exec periphery env | grep -i passkey
```

An empty value there is the whole answer. The same applies to `KOMODO_PASSKEY` on the Core side — both ends must carry the same string.

Note `PERIPHERY_PASSKEYS` is plural and takes a comma-separated list, which allows rotating keys without downtime.

## 2. The SSL certificate

Periphery generates a self-signed certificate at startup. If it can't, it won't serve:

```bash
docker logs periphery --tail 50 | grep -iE 'cert|ssl|tls|error'
```

Failures here come from a read-only or missing data directory. Give it a writable volume, or disable SSL for a trusted LAN:

```yaml
    environment:
      PERIPHERY_SSL_ENABLED: "false"
```

If SSL stays on, Core must be told to accept the self-signed cert — in the server's settings in Komodo's UI, use `https://` and enable the "allow insecure" option for that server. A `https://` URL with strict verification against a self-signed cert is a silent, total failure.

## 3. Address and reachability

```bash
# from the Core host
curl -k https://192.168.1.50:8120/health
```

- **`network_mode: host` is the usual choice** for Periphery, because it manages the host's Docker and reads host metrics from `/proc`. In bridge mode you must publish 8120 and some metrics are the container's, not the host's.
- **The address registered in Komodo** must be reachable *from Core*. `localhost` works only when Core and Periphery are on the same host.
- **Firewall.** 8120/tcp inbound on the managed host.
- **Core in Docker, Periphery on the host** — Core's container must reach the host's IP. `host.docker.internal` works on some platforms; the LAN IP always does.

## 4. It was working and went unreachable

**After a network outage, Periphery enters exponential backoff and may not reconnect promptly.** The practical fix is to restart it:

```bash
sudo systemctl restart periphery
# or
docker restart periphery
```

This is a known behaviour rather than a misconfiguration. If your network is flaky, a periodic health-check-driven restart is a reasonable mitigation:

```yaml
    healthcheck:
      test: ["CMD", "curl", "-fk", "https://localhost:8120/health"]
      interval: 60s
      retries: 3
    restart: unless-stopped
```

**After a version update**, check for a regression. A specific Periphery release has crashed on container-management API requests from Core — the symptom being that listing or restarting containers kills the agent, while the agent otherwise looks healthy. The diagnostic:

```bash
docker logs periphery --tail 100
```

An agent that exits right when you click something in the UI is this class of problem. Pin the previous known-good version:

```yaml
    image: ghcr.io/moghtech/komodo-periphery:1.18.4
```

**Keep Core and Periphery on matching versions.** A large version gap between them is a supported-but-untested combination and produces odd partial failures.

## 5. Deploys failing rather than the server being unreachable

Different symptom, worth separating:

- **`Stopped after repo pull failure`** — Periphery clones the repo on the managed host. It needs network access to your Git host and, for private repos, credentials configured in Komodo.
- **500 on "Pull image"** — the host can't reach the registry, or the image requires auth not configured on that host.
- **Stack deploy fails with a missing env var** — the same env-file resolution issue as section 1, now affecting your own stacks.

These mean Core→Periphery works fine; the failure is on the managed host's side.

## What not to do

- **Don't put the passkey only in a separate env file** referenced by variable substitution. Verify it inside the container.
- **Don't use `https://` with strict verification against the self-signed cert.** Either allow insecure for that server or provide a real certificate.
- **Don't run Periphery without the Docker socket** and expect container management. It's the whole point of the agent.
- **Don't expose 8120 to the internet.** The passkey is the only thing between it and root-equivalent control of the host's Docker.

## Prevention

| Habit | Why |
|---|---|
| Verify `docker exec periphery env` after any config change | Catches the env-resolution class immediately |
| Pin Core and Periphery to the same known-good version | Avoids regressions and version-skew behaviour |
| Healthcheck with restart on Periphery | Covers the reconnect backoff |
| Periphery reachable only on the management network | 8120 is an administrative port |

## FAQ

**Can one Core manage hosts across the internet?**
Yes, but put Periphery behind a VPN or a mesh network rather than exposing 8120.

**Does Periphery need root?**
It needs access to the Docker socket, which is root-equivalent. Treat the host accordingly.

**Server shows unreachable but deploys work.**
Then it's the health/metrics path specifically — often `/proc` not mounted, or bridge networking hiding host stats.

**Komodo or Dockge/Portainer?**
Komodo's model is Git-backed stacks across many hosts. If you manage one host from its own UI, the agent architecture is overhead you don't need.
