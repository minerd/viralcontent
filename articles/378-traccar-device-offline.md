---
title: "Traccar: Device Shows Offline But Is Reporting"
slug: traccar-device-offline
meta_description: "Status offline while positions appear in reports, or the map doesn't move. The latestPosition link, the status timeout and the websocket."
updated: October 2026
cluster: round 14 (tech) — traccar.org forums
competition: LOW
---

# Traccar: Device Shows Offline But Is Reporting

Traccar's device status and its position data are **separate**, and they fail independently. Work out which you have:

| Reports/Replay has data | Map/status | Problem |
|---|---|---|
| Yes | Offline | Status timeout or `latestPosition` — sections 1–2 |
| Yes | Online, not moving | Websocket / UI — section 3 |
| No | Offline | The device isn't reaching the server — section 4 |

## 1. What "offline" actually means

Traccar derives status from the time of the last communication, not from position quality:

- **online** — last update less than `status.timeout` ago (default 300 s)
- **offline** — exceeded that
- **unknown** — never communicated, or the server restarted and hasn't heard from it

For a device that reports every 10 minutes to save battery, the default timeout marks it offline between reports. That's working as designed:

```properties
# conf/traccar.xml
<entry key='status.timeout'>900</entry>
```

Set it above your device's reporting interval, with headroom. A tracker on a 15-minute schedule needs at least 1200.

For **UDP and HTTP protocols** there is no persistent connection at all, so status is purely a function of this timeout. Devices on TCP protocols hold a socket and go offline the moment it drops.

## 2. The `latestPosition_id` problem

A documented and specific cause: in the `tc_devices` table, the `positionid` / `latestPosition_id` column stops referencing the actual newest position. The device then shows stale or no position on the map and in "More details", while **Reports and Replay are correct** — because those query the positions table directly.

That asymmetry is the signature.

```sql
-- inspect
SELECT id, name, positionid, lastupdate FROM tc_devices WHERE name = 'My Tracker';
SELECT id, devicetime, latitude, longitude FROM tc_positions
  WHERE deviceid = 1 ORDER BY devicetime DESC LIMIT 3;
```

If the newest position's `id` isn't the device's `positionid`, that's it. A server restart re-reads it in most versions; if not, the field can be corrected directly (back up first). The usual trigger is a database write failure or a crash mid-insert, so also check disk space and the database log — the symptom will return otherwise.

## 3. Map doesn't update, old UI works

Reported with the modern web UI: positions are received and decoded (visible in the log) but the map doesn't move, while the legacy interface shows them. This is the **websocket**.

```nginx
location / {
    proxy_pass http://127.0.0.1:8082;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400s;
}
```

Without the upgrade headers the UI loads over HTTP, fetches once, and never receives live updates. The long `proxy_read_timeout` matters too — a 60-second default drops the socket every minute and the UI stops updating until you reload.

Confirm in the browser's devtools → Network → WS: a connection in state 101 is good.

## 4. The device genuinely isn't reporting

```bash
tail -f /opt/traccar/logs/tracker-server.log
```

Traccar logs every received packet. Nothing in the log means nothing arrived.

- **Wrong port.** Each protocol has its own port; the device must be configured for the port matching its protocol. Sending a GT06 packet to the Teltonika port yields nothing (or a decode error).
- **Firewall.** Both TCP and UDP where the protocol uses both.
- **APN / data plan** on the tracker's SIM.
- **Server address.** Many trackers accept only an IP, not a hostname.
- **Decode errors** appear in the log as `Unknown message` with a hex dump — that means packets arrive and the protocol is wrong. The hex is often enough to identify the real protocol.

```bash
grep -iE 'unknown|error|disconnect' /opt/traccar/logs/tracker-server.log | tail -30
```

## 5. "Appears online with continuous tracking off"

A reported inconsistency: a device shows **online** having sent no valid location, because it connected and sent a heartbeat. Status reflects communication, not fixes. If you need "has a recent fix" rather than "is connected", build it from the position timestamp with a computed attribute or a report, not from the status field.

## What not to do

- **Don't lower `status.timeout` to make devices look responsive.** You'll generate false offline alerts.
- **Don't edit the database while the server is running.** Stop it, back up, edit, start.
- **Don't open every protocol port.** Open the one your devices use; the rest are attack surface.
- **Don't delete and re-add a device to fix the map.** You lose its history, and the cause is usually sections 2–3.

## Prevention

| Habit | Why |
|---|---|
| `status.timeout` above the reporting interval | Removes false offline status |
| Websocket upgrade configured and verified | Live map updates depend on it |
| Monitor the server's disk and database | The `latestPosition` corruption follows write failures |
| One protocol port per device type, documented | Makes decode errors immediately attributable |

## FAQ

**How do I alert on a device going quiet?**
A notification on *device offline* with a sensible timeout, or a computed attribute comparing `fixTime` to now.

**Does Traccar store every position forever?**
Until you prune. `database.ignoreUnknown` and the data-manager settings control retention; a busy fleet grows fast.

**Can two devices share an identifier?**
No — the unique identifier maps to one device. Duplicates make positions land on whichever matched.

**Battery drains fast.**
Reporting interval on the device, not a server setting. Longer intervals mean a longer `status.timeout`.
