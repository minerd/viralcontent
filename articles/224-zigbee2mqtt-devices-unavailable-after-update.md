---
title: "Zigbee2MQTT Devices Unavailable After an Update? Availability, Data Path and Downgrades"
slug: zigbee2mqtt-devices-unavailable-after-update
meta_description: "All your Zigbee devices show offline after a Z2M update but still work. Why availability reporting breaks, the add-on data_path trap, and how to recover lost pairings."
updated: October 2026
cluster: round 10 (tech) — Z2M GitHub issues and HA community threads only
competition: LOW
---

# Zigbee2MQTT Devices Unavailable After an Update? Availability, Data Path and Downgrades

Two very different problems get described the same way after a Zigbee2MQTT update. Separate them first, because the fixes have nothing in common.

**Problem A — they say offline but they work.** Lights still respond, automations still fire, but Home Assistant shows everything *unavailable*. This is **availability reporting**, a display problem.

**Problem B — they're actually gone.** Devices missing from the Z2M device list, nothing responds, pairings lost. This is **data/state**, and it's serious.

## Problem A: everything reads offline but works

### Check the availability feature

Availability is an opt-in Z2M feature. After an update, its config can end up inconsistent, or newly enabled with default timeouts that mark your battery devices dead.

In `configuration.yaml`:

```yaml
availability:
  enabled: true
  active:
    timeout: 10     # minutes, mains-powered devices
  passive:
    timeout: 1500   # minutes, battery devices — must be generous
```

Battery devices only speak when they have something to say. A passive timeout that's too short marks every sensor unavailable until it next reports. **Raise the passive timeout** before anything else.

### Then the dull-but-effective steps

- **Restart Zigbee2MQTT**, then **restart Home Assistant** — in that order
- **Hard-refresh the browser** (and clear its cache) — the frontend caches availability state and shows a stale picture after an update
- Check **MQTT** itself: is the broker up, did credentials survive the update, is Z2M connected? Z2M logs say so on startup. The HA MQTT integration shows the last message time
- Confirm the **base topic** didn't change in the update's config migration

### Give it time

After a restart, availability repopulates as devices check in. Mains devices come back in minutes; battery sensors can take hours. Don't conclude anything in the first ten minutes.

## Problem B: devices actually lost after an update

### The Home Assistant add-on data_path trap

A specific, reported failure: after updating the **Home Assistant add-on**, all paired devices appeared to vanish, because the add-on's **`data_path`** changed and Z2M started with an empty database.

Fix:
- Set **`data_path: /addon_config/zigbee2mqtt`** in the add-on configuration (the current location)
- Update to the **patched add-on version** rather than the one that introduced it
- Your old `coordinator_backup.json`, `database.db` and `configuration.yaml` are still in the **previous** data directory — find them before you re-pair anything

Re-pairing 60 devices because a path moved is avoidable. Look for the old `database.db` first.

### Restore, don't re-pair

- Stop Z2M
- Put `database.db`, `configuration.yaml` and `coordinator_backup.json` back in the directory Z2M is now reading
- Start Z2M and check the device list before touching anything else

### Coordinator firmware and adapter changes

Z2M 2.x changed adapter handling. If the coordinator isn't detected or the network won't form:
- Check the **`adapter`** and **`port`** settings against the current docs for your stick
- Use a **stable by-id device path** (`/dev/serial/by-id/...`), not `/dev/ttyUSB0` — USB enumeration order changes on reboot and this is a classic post-update "everything is gone"
- Don't reflash coordinator firmware as a first move; it risks the network key

### Downgrade if you must

Pinning the previous Z2M version is a legitimate recovery step while you read the release notes and the issue tracker. In the add-on, that means installing the older version; in Docker, pinning the image tag — which you should be doing anyway instead of `latest`.

## Before your next update

1. **Back up** `data/` (database.db, configuration.yaml, coordinator_backup.json) — and check the backup is not empty
2. **Read the release notes**, especially for major versions (1.x → 2.x had breaking changes)
3. **Pin image tags**; never let an unattended pull take your Zigbee network down
4. **Watch the logs** on first start after an update instead of assuming it worked

## FAQ

**Why do devices work while showing unavailable?**
Commands go out over Zigbee regardless; availability is a separate heartbeat that Z2M publishes and HA reads.

**My battery sensors are always unavailable.**
Your passive availability timeout is too short for how often they report.

**Did the update delete my devices?**
Almost never. Far more often Z2M is reading a different data directory or serial path than before.

**Should I re-pair everything?**
Only after you've confirmed the old `database.db` is genuinely unrecoverable.
