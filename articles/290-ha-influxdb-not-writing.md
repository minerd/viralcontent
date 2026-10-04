---
title: "Home Assistant Not Writing to InfluxDB? Token Permissions and the Include/Exclude Trap"
slug: ha-influxdb-not-writing
meta_description: "The InfluxDB integration loads but no data arrives. Default-empty API tokens, v1 vs v2 config, include/exclude filters, max_retries and read-only filesystem errors."
updated: October 2026
cluster: round 12 (tech) — HA community threads and core GitHub issues
competition: LOW
---

# Home Assistant Not Writing to InfluxDB? Token Permissions and the Include/Exclude Trap

The integration starts without complaint and your buckets stay empty. Four causes, in order of likelihood.

## 1. The token has no permissions

In InfluxDB 2.x, a newly created **API token has no access by default**. You must grant it **write** (and ideally read) on the target bucket.

- InfluxDB UI → **API Tokens** → create a token with explicit **write** access to your bucket, or use an all-access token while testing
- Check the **organisation** matches exactly (it's case-sensitive)
- Check the **bucket** name matches exactly

For InfluxDB 1.x, the user needs write privileges on the database, and the database must already exist — HA won't create it for you unless configured to.

## 2. v1 vs v2 configuration shapes

Mixing them produces a silent no-op. The v2 form:

```yaml
influxdb:
  api_version: 2
  ssl: false
  host: 192.168.1.50
  port: 8086
  token: !secret influxdb_token
  organization: home
  bucket: homeassistant
  max_retries: 10
  include:
    domains:
      - sensor
      - binary_sensor
```

`api_version: 2` is the line people forget; without it HA speaks the 1.x API to a 2.x server and writes go nowhere.

## 3. Include/exclude filters excluding everything

The InfluxDB integration has its own `include:`/`exclude:` filters, separate from the recorder's. If you wrote an `include:` block, **only** those entities are written — and a typo means nothing is.

- Start with **no filters at all**, confirm data arrives, then add filters
- Entity ids are exact; `sensor.*` style globs go under `entity_globs`
- Also check the **recorder**: entities excluded from the recorder may not produce the state changes you expect to see forwarded

## 4. Debug logging will tell you immediately

```yaml
logger:
  default: warning
  logs:
    homeassistant.components.influxdb: debug
```

Restart, then watch. You'll see either successful writes, or the exact rejection — 401 (token), 404 (bucket/org), 400 (field type conflict), or a connection error.

**Field type conflicts** are worth knowing: once a measurement's field is a float, a later string value for the same field is rejected. A sensor that changes from numeric to `unavailable`/`unknown` is the usual cause, and it shows as 400s for one entity while everything else works.

## 5. Connection and environment problems

- `[Errno 30] Read-only file system` on the InfluxDB side means the **container's filesystem or volume** is read-only — reported after filesystem corruption or Docker upgrades. Check the host's mount and the volume
- From HA, confirm reachability: `curl -sI http://192.168.1.50:8086/ping` (expect 204)
- **SSL**: `ssl: true` with a self-signed certificate HA doesn't trust fails; add the CA or use plain HTTP on the LAN
- `max_retries: 10` is a documented help for intermittent timeouts — HA drops writes it can't deliver rather than queueing indefinitely

## 6. It wrote before and stopped

- **Token rotated or expired**
- **Bucket retention** deleted the data you're looking for; you're querying a window that's been trimmed
- InfluxDB **disk full** — it stops accepting writes
- An InfluxDB **major upgrade** (1.x → 2.x → 3.x) changed the API; the HA integration config must change with it
- Someone recreated the bucket, so the name matches but the ID doesn't

## Prevention

1. Create a **dedicated token** with write access to one bucket, and note where it's used
2. Set **`api_version: 2`** explicitly
3. Start with **no include/exclude**, add filters once data flows
4. Keep **debug logging** handy as the first diagnostic
5. Monitor InfluxDB **disk usage** and retention policies

## FAQ

**Why does the integration load if the token is wrong?**
It doesn't validate on startup in a way that fails loudly; writes fail later. Debug logging shows the 401.

**Nothing at all is written.**
Token permissions, `api_version`, or an include filter that matches nothing.

**One entity is missing from InfluxDB.**
Likely a field type conflict — check debug logs for 400 errors naming it.

**Should I use InfluxDB or the recorder?**
Both do different jobs: recorder for HA's own history, InfluxDB for long-term graphing in Grafana.
