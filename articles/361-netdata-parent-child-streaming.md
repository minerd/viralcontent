---
title: "Netdata Parent/Child Streaming Not Connecting"
slug: netdata-parent-child-streaming
meta_description: "Children won't stream to the parent: API key not enabled, remote server denied access, or an SSL mismatch. The two files and how they pair."
updated: October 2026
cluster: round 14 (tech) — Netdata community forums and GitHub
competition: LOW
---

# Netdata Parent/Child Streaming Not Connecting

Streaming is configured in **`stream.conf` on both machines**, but the two halves look different, and mixing them up is the single biggest cause of failure.

| On the child | On the parent |
|---|---|
| `[stream]` section — where to send | `[API_KEY]` section — who may send |

The literal string `[API_KEY]` in the documentation is a placeholder: the section name must be the **actual UUID**.

## 1. Child side

```ini
# /etc/netdata/stream.conf  (child)
[stream]
    enabled = yes
    destination = 192.168.1.10:19999
    api key = 11111111-2222-3333-4444-555555555555
    timeout seconds = 60
    default port = 19999
    send charts matching = *
    buffer size bytes = 10485760
    reconnect delay seconds = 5
```

Generate the key once:

```bash
uuidgen
```

## 2. Parent side

```ini
# /etc/netdata/stream.conf  (parent)
[11111111-2222-3333-4444-555555555555]
    enabled = yes
    allow from = *
    default history = 3600
    default memory mode = dbengine
    health enabled by default = auto
```

The section header is the UUID in square brackets — **not** the word `API_KEY`. This section exists only on the receiving side. A parent with a `[stream]` section instead, or with `[API_KEY]` literally, produces exactly:

```
STREAM: API key is not enabled
```

on the parent, and on the child:

```
STREAM: remote server denied access, probably we don't have the right API key?
```

Those two messages together are conclusive: the UUID doesn't match, or the parent's section is missing.

```bash
sudo systemctl restart netdata     # on both, after editing
journalctl -u netdata -n 60 | grep -i stream
```

## 3. SSL/TLS mismatch

The second-most-common failure, and it has a distinctive log line: the child connects, but the parent doesn't answer with the streaming protocol.

The destination syntax carries the TLS intent:

```ini
destination = 192.168.1.10:19999          # plain
destination = 192.168.1.10:19999:SSL      # TLS
```

Rules:

- If the parent terminates TLS (its own `[web]` section has certificates, or it sits behind a TLS proxy), the child needs `:SSL`.
- If the parent is plain HTTP, `:SSL` on the child makes the parent see TLS handshake bytes as garbage.
- With TLS enabled, the child **verifies the certificate by default**. A self-signed parent certificate fails. For a lab:

```ini
[stream]
    ssl skip certificate verification = yes
```

Prefer installing the CA properly where you can.

## 4. Network

```
STREAM: Cannot connect to 192.168.1.10:19999 (No route to host)
```

Plainly a firewall or routing problem:

```bash
# from the child
nc -zv 192.168.1.10 19999
```

And on the parent, confirm it listens on a reachable interface, not just localhost:

```ini
# /etc/netdata/netdata.conf (parent)
[web]
    bind to = 0.0.0.0:19999
```

## 5. Connects then falls behind

```
STREAM: buffer full, dropping metrics
```

The child's send buffer fills faster than the link drains. Over a slow or high-latency link:

```ini
[stream]
    buffer size bytes = 20971520
    send charts matching = !netdata.* *
```

Raising the buffer buys time; reducing what you send fixes the cause. Excluding Netdata's own internal charts, and anything you don't query, cuts volume substantially.

On the parent, a child that appears and disappears usually means it's reconnecting — check `reconnect delay seconds` and the parent's `timeout seconds`; the parent's timeout must exceed the child's heartbeat.

## What not to do

- **Don't put a `[stream]` section on the parent** expecting it to receive. That section is for sending.
- **Don't use the literal `[API_KEY]`.** Generate a UUID.
- **Don't share one API key across trust boundaries.** Anything holding it can inject metrics; use one key per group of children and restrict `allow from`.
- **Don't expose 19999 to the internet** to stream across sites. Put it on a VPN.

## Prevention

| Habit | Why |
|---|---|
| One UUID per fleet, recorded in your notes | The key is half of every troubleshooting session |
| Explicit `:SSL` or not, matched to the parent | Removes the silent-protocol-mismatch class |
| `allow from` restricted to your subnets | Security, and it makes misconfiguration visible |
| Prune `send charts matching` early | Buffer problems never start |

## FAQ

**Do children keep local history when streaming?**
They can. `memory mode = ram` with a short history on children and `dbengine` on the parent is the usual split.

**Can a parent also be a child?**
Yes — proxy configurations are supported; the node has both sections.

**Health alarms firing twice?**
Both parent and child have health enabled. Set `health enabled by default = auto` on the parent and disable health on children.

**Child shows in the parent's list but has no data.**
Usually the SSL case: the connection is up at TCP level and the stream never starts.
