---
title: "Zabbix Agent \"Not available\": Passive, Active and the Port That Isn't Open"
slug: zabbix-agent-not-available
meta_description: "ZBX turns red, items go unsupported, or active checks never arrive. Which direction each mode connects in, and the one hostname that must match."
updated: October 2026
cluster: round 13 (tech) — Zabbix forums and docs
competition: LOW
---

# Zabbix Agent "Not available": Passive, Active and the Port That Isn't Open

Zabbix agents work in two modes that connect in **opposite directions**, and nearly every "not available" is a firewall or configuration mismatch between them.

| Mode | Who connects | Port | Config |
|---|---|---|---|
| **Passive** | Server → Agent | 10050 on the agent | `Server=` |
| **Active** | Agent → Server | 10051 on the server | `ServerActive=` + `Hostname=` |

The red ZBX icon specifically reflects **passive** availability. Active checks can work perfectly while the icon stays red, and vice versa.

## 1. Test the passive path

From the Zabbix server:

```bash
zabbix_get -s 192.168.1.50 -k agent.ping
```

- **`1`** — passive works. The icon should be green; if it isn't, the host's interface IP in Zabbix is wrong.
- **Connection refused** — agent not running, or listening on the wrong address.
- **Timeout** — firewall between them.
- **"Check access restrictions in Zabbix agent configuration"** — the agent is running and reachable but refuses *your* server. This is the `Server=` setting.

```ini
# /etc/zabbix/zabbix_agent2.conf
Server=192.168.1.10
ListenPort=10050
```

`Server=` is an allowlist of addresses permitted to query the agent. It must contain the Zabbix server's (or proxy's) IP. The default `127.0.0.1` is why a fresh agent install is unreachable — and the error message about access restrictions is the giveaway.

In Docker, the agent must also publish 10050 and know its own reachable address:

```yaml
  zabbix-agent:
    image: zabbix/zabbix-agent2:latest
    ports:
      - "10050:10050"
    environment:
      ZBX_SERVER_HOST: 192.168.1.10
      ZBX_HOSTNAME: docker-host-1
```

## 2. Test the active path

Active checks need the agent to reach the server on **10051**, outbound:

```bash
# from the agent host
nc -zv 192.168.1.10 10051
```

```ini
ServerActive=192.168.1.10
Hostname=web-01
```

The critical rule: **`Hostname` must exactly match the "Host name" field of the host in Zabbix** — not the visible name, not the DNS name, the Host name. A mismatch means the server receives active check data for an unknown host and discards it. The agent log says so:

```bash
tail -50 /var/log/zabbix/zabbix_agent2.log
```

```
active check configuration update from [192.168.1.10:10051] started to fail
(host [web-01] not found)
```

That line is the single clearest diagnostic in Zabbix. It names the hostname it sent and tells you the server didn't recognise it.

If you prefer not to maintain the name manually, `HostnameItem=system.hostname` makes the agent report the OS hostname — then the Zabbix host must be named identically.

## 3. Items "unsupported" rather than the host unavailable

A green host with red items is a different problem:

- **The item's type doesn't match the agent's mode.** An item of type "Zabbix agent" is passive; "Zabbix agent (active)" is active. A template of active items on a host where only the passive path works gives exactly this.
- **Permissions.** Items reading `/proc`, `vfs.file.contents[...]`, or running `system.run[]` need the agent's user to have access. The agent runs as `zabbix`, not root. `AllowKey`/`DenyKey` also matters:

```ini
AllowKey=system.run[/usr/local/bin/mycheck.sh]
DenyKey=system.run[*]
```

`system.run` is **denied by default** in modern agents. Enabling it broadly is a remote-code-execution surface; allow specific keys only.

- **Plugin not present (Agent 2).** Items for Docker, PostgreSQL, Redis etc. come from agent 2 plugins. A missing or unconfigured plugin makes those items unsupported while the agent itself is fine.

## 4. Flapping availability

A host that goes red intermittently:

- **Timeout too low.** `Timeout=3` (the default) is tight for items that enumerate filesystems or query a database. Raise it to 10–30 on both agent and server, and note the server's `Timeout` must be ≥ the agent's.
- **`StartAgents=3`** — too few pollers for the number of passive items means queueing and timeouts under load.
- **NAT or a stateful firewall dropping idle connections.** Active checks hold a connection pattern that some firewalls age out; the agent reconnects, which shows as gaps.
- **DNS.** If the host interface uses DNS rather than IP, every poll depends on resolution. Use IP for monitoring interfaces.

## What not to do

- **Don't set `Server=0.0.0.0/0`.** Any host on the network can then query every metric your agent exposes, including file contents where configured.
- **Don't enable `system.run[*]`.** It turns the agent into a remote shell for anything listed in `Server=`.
- **Don't fix a red ZBX icon by switching all items to active.** It hides the passive-path problem rather than solving it, and `zabbix_get` then no longer works for debugging.
- **Don't change `Hostname` casually.** Active check history is tied to the host; a rename creates a new unknown host.

## Prevention

| Habit | Why |
|---|---|
| `Hostname` in the agent config = Host name in Zabbix, documented | Removes the dominant active-check failure |
| `Server=` set to the exact server/proxy IP | Secure and correct in one setting |
| `zabbix_get` as the first test, every time | Splits passive from active immediately |
| Timeout 10+ on both sides for anything non-trivial | Stops flapping on heavier items |

## FAQ

**Which mode should I prefer?**
Active, for anything behind NAT or a firewall you don't control — the agent initiates, so no inbound rule is needed. Passive is easier to debug.

**Can I use both?**
Yes, and it's common: passive for availability, active for the bulk of items.

**Agent 1 or Agent 2?**
Agent 2 for new deployments: plugins, persistent buffering for active checks, better concurrency.

**The host is green but shows no data.**
Availability is a separate check from items. Look at Latest data and the item's own error text.
