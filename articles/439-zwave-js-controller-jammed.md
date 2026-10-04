---
title: "Z-Wave JS: Controller Reporting \"Jammed\""
slug: zwave-js-controller-jammed
meta_description: "Commands are slow or never execute and the controller reports jammed. The 700-series firmware issue, the recovery feature you can disable, and removing dead nodes."
updated: October 2026
cluster: round 14 (tech) — zwave-js GitHub and HA community
competition: LOW
---

# Z-Wave JS: Controller Reporting "Jammed"

"Jammed" means the controller could not transmit — the radio is busy, the mesh is congested, or the controller firmware has wedged. It is most often reported on **700-series** sticks, and there is a known pattern.

## 1. Rule out a dead node flooding the mesh

A single unreachable node that Z-Wave JS keeps retrying generates enormous traffic. Every retry is a transmission the controller must attempt, and a handful of dead nodes can saturate it.

```
Z-Wave JS UI → Control Panel → sort by status
```

Nodes marked **Dead** or stuck interviewing are the first thing to deal with:

```
the node → Actions → Ping
```

A failed ping moves it to the failed-nodes list, after which:

```
the node → ⋮ → Remove failed node
```

The documented catch: **Remove failed node requires the node to be in the controller's failed list, which requires a failed ping first.** If the controller returns an immediate failure without attempting the ping, the node never enters that list and removal fails. Then use **Replace failed node**, or reset the device and let the controller time it out.

Removing two or three genuinely dead nodes frequently resolves chronic jamming on its own.

## 2. The unresponsive-controller recovery feature

Z-Wave JS added automatic recovery for unresponsive controllers — it resets the stick when it detects a jam. On some setups that recovery itself causes churn, and disabling it gives a more stable (if less self-healing) system:

```bash
# environment variable
ZWAVEJS_DISABLE_UNRESPONSIVE_CONTROLLER_RECOVERY=true
```

or in the driver options:

```json
{
  "features": {
    "unresponsiveControllerRecovery": false
  }
}
```

In Z-Wave JS UI this is exposed under the Z-Wave settings. Turning it off is worth trying if your symptom is **"jammed" alternating with "ready" and operations hanging** — the reported shape of recovery fighting the controller.

## 3. Controller firmware

700-series controllers have had firmware bugs affecting exactly this. Check and update:

```
Z-Wave JS UI → Control Panel → Controller → Firmware update (OTW)
```

Z-Wave JS UI can flash the controller over the wire for supported sticks. Note the current version first. An out-of-date 700-series stick is the single most likely cause if everything else in your mesh looks healthy.

## 4. The physical layer

This is where the cheapest wins are:

- **USB 2 port, not USB 3.** USB 3 controllers radiate broadband noise that degrades 900 MHz Z-Wave reception. This is a real, measurable effect.
- **A USB extension cable**, getting the stick away from the host's chassis, SSDs and the Wi-Fi card. A 1 m extension often transforms a marginal mesh.
- **Not next to a Zigbee dongle.** Different bands, but the dongles' own switching noise interferes.

```bash
dmesg -T | grep -iE 'usb|tty' | tail -20
```

USB disconnect/reconnect lines mean a physical problem, and a controller that re-enumerates mid-operation will report jammed.

## 5. Mesh health

```
Control Panel → the node → Health check
```

A documented UI issue: **the node health check UI can hang.** Run it on one node at a time rather than across the mesh, and don't conclude anything from a hang beyond "don't do that".

More useful:

```
Control Panel → ⋮ → Heal network   (only when the mesh is quiet)
```

Healing re-computes routes and generates a lot of traffic. Run it overnight, never while diagnosing a jam — you will make it worse.

Structural fixes that actually help:

- **Add mains-powered nodes** as routers. Battery devices do not route. A mesh of twenty battery sensors and two mains devices will be unreliable regardless of settings.
- **Keep S0 usage to a minimum.** S0 triples the frames per command and is a well-known mesh-congestion cause. Re-include S0 devices as S2 where supported.

## 6. "Controller is unable to transmit"

The related error, same family:

```
Error: Controller is unable to transmit
```

Reported alongside nodes stuck at **NodeInfo** or **ProtocolInfo** during interview. Sequence that usually clears it:

1. Stop Z-Wave JS UI
2. Unplug the stick, wait 10 seconds, replug
3. Start Z-Wave JS UI
4. Deal with dead nodes (section 1) before doing anything else

If it recurs within hours, go to firmware (section 3) and then the physical layer (section 4).

## What not to do

- **Don't run a heal while the controller is jammed.** You add traffic to a congested radio.
- **Don't re-include devices to fix jamming.** The controller is the problem, not the pairings.
- **Don't leave dead nodes in the mesh.** They are an active cost on every transmission.
- **Don't plug the stick directly into a USB 3 port.** It is the most common avoidable cause.

## Prevention

| Habit | Why |
|---|---|
| USB 2 port, extension cable, away from the case | Biggest single reliability improvement |
| Dead nodes removed promptly | Retries are the main congestion source |
| S2 rather than S0 wherever the device supports it | S0 is a documented mesh burden |
| Controller firmware current, version noted | 700-series bugs are firmware-specific |

## FAQ

**Should I move to an 800-series controller?**
They address several 700-series issues and have better range. It's a reasonable upgrade if you've exhausted the above.

**Does a jam lose commands?**
Yes — commands that couldn't transmit fail. Automations depending on them silently don't run.

**How many nodes is too many?**
The protocol allows 232. Practical limits are about mesh quality, not count — twenty well-placed routers beat eighty poorly-placed devices.

**Network key backup?**
Keep the four S2/S0 keys outside the container. Without them a rebuilt controller means re-pairing everything.
