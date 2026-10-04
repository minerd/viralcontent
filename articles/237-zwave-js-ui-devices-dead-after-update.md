---
title: "Z-Wave Devices Dead After a Z-Wave JS UI Update? Recover Before You Re-Pair"
slug: zwave-js-ui-devices-dead-after-update
meta_description: "Nodes marked dead or unavailable after updating Z-Wave JS UI. Why re-interviewing and rolling back beat re-pairing, and how to protect the network key and NVM backup."
updated: October 2026
cluster: round 11 (tech) — HA core GitHub issues and HA community threads
competition: LOW
---

# Z-Wave Devices Dead After a Z-Wave JS UI Update? Recover Before You Re-Pair

You update Z-Wave JS UI and a pile of devices go **unavailable** in Home Assistant, or the log says *"The node did not respond after 1 attempts, it is presumed dead"*. Sometimes they're still listed as Ready in the Z-Wave JS UI web interface, which is the tell that this is a **software state problem, not a radio problem**.

**Do not start excluding and re-pairing devices.** That's hours of work, it loses entity IDs and automations, and it's almost never necessary.

## Step 0: don't make it worse

- **Don't exclude** devices
- **Don't reset the controller**
- **Don't re-flash controller firmware**
- **Don't heal/rebuild the whole network** as a first move — it floods a network that's already struggling

## Step 1: make sure only one Z-Wave stack is running

The most common self-inflicted cause: **both** the `zwave_js` add-on and **Z-Wave JS UI** running, both trying to hold the USB stick. Only one process can own the serial device.

- Disable the plain **Z-Wave JS** add-on if you use **Z-Wave JS UI**
- In Home Assistant, the Z-Wave integration should point at Z-Wave JS UI's **websocket** (usually port 3000), not at its own driver
- Check the add-on log for *"Failed to open the serial port"* or *"port is already in use"*

## Step 2: check the controller is actually present

```
ls -l /dev/serial/by-id/
```

Use the **by-id** path in your configuration, never `/dev/ttyUSB0` — USB enumeration order changes on reboot, and after a host update your stick can land on a different device node. This alone explains a lot of "everything died after an update".

In Z-Wave JS UI: does the **Controller** show as ready, with a home ID? If not, nothing else matters yet.

## Step 3: restart in the right order

1. Restart **Z-Wave JS UI**
2. Wait for the controller to come ready and the node list to populate
3. **Reload** the Z-Wave integration in Home Assistant (Settings → Devices & Services → Z-Wave → ⋮ → Reload)
4. Give it time — mains devices answer in minutes, **battery devices only check in on their own schedule**, which can be hours

A lot of "dead" nodes are battery devices that simply haven't woken yet. Wake one manually (press its button) and watch whether it comes back.

## Step 4: re-interview individual nodes

For nodes still dead after the restart:

- In Z-Wave JS UI → node → **Re-interview**. This re-reads the device's capabilities without touching the pairing
- Do them **one at a time**, not all at once
- Battery nodes need to be **woken** before an interview can complete — press the button, then interview

Reported in several of these threads: re-interviewing recovers devices that looked permanently dead.

## Step 5: roll back the version

If a specific release broke your network — and this has happened across several Z-Wave JS UI versions — **go back**:

- In the Home Assistant add-on store, install the **previous version**
- In Docker, pin the previous **image tag** (pin tags generally; don't run `latest` on your home's light switches)
- Then wait for the issue to be fixed upstream rather than rebuilding your network around it

Rolling back is a legitimate, fast fix. Check the project's GitHub issues for your exact version first — if others report it, you'll also find which version to go back to.

## Step 6: restore from backup if the node list itself is wrong

Z-Wave JS UI keeps:
- A **store directory** with its database and config
- An **NVM backup** of the controller (Settings → Backup, and it can run automatically)

If the node list is empty or truncated after an update, the fix is **restoring the store/NVM**, not re-pairing. Check where the add-on's store lives now versus before — a changed data path produces an empty-looking network, exactly as it does with Zigbee2MQTT.

**Take an NVM backup now, while things work**, and keep automatic backups on. It is the difference between a ten-minute restore and an evening with a ladder.

## Step 7: only then, the network

If multiple nodes are genuinely unreachable and the controller is fine:
- Check for a **new source of interference** (a new 2.4 GHz/900 MHz device, a USB 3 port next to the stick — use an extension cable)
- **Rebuild routes** for specific nodes, not the whole network at once
- Confirm mains-powered repeaters are still powered — losing one can orphan a branch

## FAQ

**Why do devices show Ready in Z-Wave JS UI but unavailable in Home Assistant?**
That's the integration's connection to the driver, not the radio. Reload the Z-Wave integration.

**Should I re-pair dead nodes?**
Last resort only. Try restart → re-interview → version rollback → backup restore first.

**Can I run Z-Wave JS and Z-Wave JS UI together?**
No. One process owns the serial device.

**How do I avoid this next time?**
Pin versions, keep automatic NVM backups, use the `by-id` serial path, and read the release notes before updating.
