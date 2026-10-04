---
title: "Tdarr Node Won't Connect to the Server? Ports, IPs and Version Skew"
slug: tdarr-node-not-connecting
meta_description: "'Server not alive' or a node that registers in a loop. The port 8266 requirement, why localhost fails, Socket.IO through proxies, and matching versions."
updated: October 2026
cluster: round 12 (tech) — Tdarr GitHub issues and docs; the rest of the SERP is IBM and Oracle
competition: LOW
---

# Tdarr Node Won't Connect to the Server? Ports, IPs and Version Skew

The node logs **"Server not alive"**, or it keeps registering over and over and never settles. In Tdarr's own words this is **normally a firewall or networking issue** — so check the network path before touching config.

## 1. Is the server actually up and reachable?

From the **node's** machine, not yours:

```bash
curl -s http://SERVER_IP:8265/api/v2/status     # web UI port
curl -s http://SERVER_IP:8266/api/v2/status     # server port the node uses
```

Both should answer. If the first works and the second doesn't, **8266** is blocked or not published — that's the single most common cause.

Two ports matter and people confuse them:
- **8265** — web UI
- **8266** — server/node communication

## 2. Use a real IP, not localhost

In the node config (`Tdarr_Node_Config.json`, or the `serverIP`/`serverURL` environment variables), set the server's **LAN IP**, not `localhost` or `0.0.0.0`.

`localhost` inside a container means the container itself. This is the classic Docker mistake and it produces exactly this error.

```json
{
  "serverIP": "192.168.1.50",
  "serverPort": "8266",
  "nodeName": "node-01",
  "nodeIP": "192.168.1.60",
  "nodePort": "8267"
}
```

Note **`nodeIP`** as well: the server also talks back to the node, so an unreachable or wrong node address breaks the pair in the other direction.

## 3. Socket.IO must pass through

Tdarr uses **Socket.IO** — a persistent WebSocket (falling back to HTTP long-polling). Anything that doesn't forward that breaks it while ordinary HTTP works:

- **nginx**: `proxy_http_version 1.1` plus `Upgrade`/`Connection` headers
- **Traefik/Caddy**: usually fine; remove compression/buffering middleware
- **Cloudflare**: enable WebSockets; note the idle timeouts
- Don't put the **node↔server** link through a reverse proxy at all if you can avoid it — keep it on the LAN

## 4. Firewall and Docker networking

```bash
sudo ufw status
sudo iptables -L -n | grep 8266
docker inspect tdarr-node --format '{{json .HostConfig.PortBindings}}'
```

- Publish **8267** (node) and allow outbound to 8266
- On the same host, put server and node on the **same Docker network** and use container names
- In **host networking**, make sure the ports aren't already used
- Windows: the Windows Firewall prompt on first run is easy to dismiss by accident

## 5. Version skew

Server and node should be on the **same version**. A node that connects, registers, and drops in a loop is very often one side updated and the other not.

- Update both, or pin both to the same tag
- Don't run `latest` on one and a fixed tag on the other
- Check both logs for a version-mismatch line on connect

## 6. The node connects but does no work

Different problem, same frustration:

- The node has no **worker slots** enabled (transcode/health check, CPU/GPU counts)
- Its **library paths don't match** the server's. The node must see the same files at the same paths — map volumes identically on both
- A **GPU worker** on a node with no working GPU passthrough fails every job
- Library has nothing matching the flow/plugin filters

## Diagnosing in five commands

```bash
docker logs tdarr-node --tail 100
docker logs tdarr-server --tail 100
curl -s http://SERVER_IP:8266/api/v2/status
docker exec tdarr-node ls -la /media       # same path as the server?
docker exec tdarr-node ping -c2 SERVER_IP
```

## Prevention

1. **Static IPs / DHCP reservations** for server and nodes
2. **Identical volume mappings** across server and all nodes
3. **Pin the same version** on both
4. Keep node↔server traffic **off the reverse proxy**
5. Document which host is which node — a "node-01" that's actually on the NAS is a future hour lost

## FAQ

**Which port does the node use?**
8266 to the server; the node itself listens on 8267.

**Can the node be on a different network?**
It can, but it needs bidirectional reachability and persistent WebSocket support. A VPN (Tailscale/WireGuard) is the tidy way.

**Why does it register repeatedly?**
Usually version mismatch or a connection that drops right after registering — check both logs.

**Do paths have to match?**
Yes. The node must see the same files at the same paths as the server.
