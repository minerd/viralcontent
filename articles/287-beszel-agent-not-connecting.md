---
title: "Beszel Agent Not Connecting to the Hub? Which Direction Is Broken"
slug: beszel-agent-not-connecting
meta_description: "A Beszel system stuck on 'down'. WebSocket vs SSH connection modes, the /api/beszel/agent-connect endpoint, Docker socket paths and fingerprint mismatches."
updated: October 2026
cluster: round 12 (tech) — Beszel GitHub issues, discussions and docs
competition: LOW
---

# Beszel Agent Not Connecting to the Hub? Which Direction Is Broken

Beszel has **two connection modes**, and the troubleshooting differs completely. Work out which one you're using first — the docs' own framing is that **one of the two directions needs to work**.

- **WebSocket mode**: the **agent** connects out to the hub at `/api/beszel/agent-connect`
- **SSH mode**: the **hub** connects in to the agent's port (default 45876)

## 1. Read the hub's logs

Beszel runs on PocketBase, and the real error is in its log:

**`https://your-hub/_/#/logs`**

That tells you which side failed and why — authentication, timeout, refused. Everything below is confirmation.

## 2. WebSocket mode checks

The agent must reach the hub's connect endpoint:

```bash
# from the agent's machine
curl -sI https://hub.example.com/api/beszel/agent-connect
```

- Behind a reverse proxy, **WebSockets must be proxied** (`proxy_http_version 1.1`, `Upgrade`/`Connection` headers). This is the most common failure
- Reported: Beszel **behind a Cloudflare Tunnel** needs the tunnel to allow WebSockets; check the tunnel's settings
- Reported: agents **don't automatically retry** after a temporary network outage in some versions — restart the agent after your network comes back, and update if you're affected
- Agents on versions **0.9.1 and earlier** don't support outgoing HTTP connections to the hub at all. Upgrade the agent

## 3. SSH mode checks

The hub initiates the connection, so the **agent's port must be reachable**:

```bash
# from the hub
nc -vz AGENT_IP 45876
```

- Open the port in the agent host's firewall **and** your cloud provider's security group — both, as the docs point out
- Reported gotcha: if the **hub host has `iptables -P FORWARD DROP`**, the connection can fail silently. Either allow forwarded packets or switch to WebSocket mode
- The agent must be **listening on an address the hub can reach**, not just loopback

## 4. Docker and localhost

When the hub and the agent are on the same machine but in different containers, **`localhost` will not work** — they're in separate network namespaces. The documented recommendation is a **unix socket** between them:

```yaml
# hub
volumes:
  - ./beszel_socket:/beszel_socket
# agent
volumes:
  - ./beszel_socket:/beszel_socket
environment:
  LISTEN: /beszel_socket/beszel.sock
```

Otherwise use the host IP, or put them on the same Docker network and use container names.

The agent also needs the **Docker socket** (read-only) to report container stats:

```yaml
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

Reported for **Unraid** and non-root setups: a socket-proxy or non-root agent needs its permissions lined up, or container metrics are missing while the system itself reports fine.

## 5. Fingerprint and token mismatches

- A **fingerprint mismatch** between what the hub recorded and what the agent presents blocks the connection. Delete the system in the hub and re-add it to re-establish trust
- Re-created agent containers that regenerate their key look like new machines
- Copy the **exact** token/key from the hub's add-system dialog — a truncated paste is common

## 6. Still nothing

1. Hub logs at `/_/#/logs`
2. Agent logs: `docker compose logs beszel-agent` or `journalctl -u beszel-agent`
3. Test the direction that applies (curl the endpoint, or nc the port)
4. Remove and re-add the system in the hub
5. Match versions: update hub and agents together

## Prevention

1. **Pin versions** and update hub + agents together
2. Prefer **WebSocket mode** for agents behind NAT; SSH mode for a flat trusted LAN
3. **Unix socket** when hub and agent share a host
4. Mount the Docker socket **read-only**
5. Keep the hub behind a proxy that you've verified passes WebSockets

## FAQ

**Which mode should I use?**
WebSocket if the agent can reach the hub (works through NAT). SSH if the hub can reach the agent.

**Why does localhost fail in Docker?**
Separate network namespaces. Use a unix socket, host IP, or shared network.

**System shows up but no container stats.**
The Docker socket isn't mounted or isn't readable by the agent.

**It stopped after a network outage.**
Some versions don't retry. Restart the agent and update it.
