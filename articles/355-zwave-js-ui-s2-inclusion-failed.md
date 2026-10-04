---
title: "Z-Wave JS UI: S2 Inclusion Failing"
slug: zwave-js-ui-s2-inclusion-failed
meta_description: "Secure inclusion fails, keys are reported missing, or the node ends up with no security class. The keys, the 240-second timeout and the proximity rule."
updated: October 2026
cluster: round 14 (tech) — zwave-js GitHub and HA community
competition: LOW
---

# Z-Wave JS UI: S2 Inclusion Failing

S2 inclusion is a two-stage process: the node joins the network, then **security bootstrapping** negotiates a key. The second stage is where it fails, and the node is left included with a lower security class than you asked for — or useless.

## 1. The network keys must exist

```
Settings → Z-Wave → Security Keys
```

You need four:

- `S2_Unauthenticated`
- `S2_Authenticated`
- `S2_AccessControl`
- `S0_Legacy`

If any are blank, inclusion fails with a message naming exactly which are missing. There is a **generate** button that creates random keys — use it, then:

**Write the keys down somewhere outside the container.** They are the only way to recover your network without re-pairing every device. Losing them means re-including everything.

```yaml
# docker-compose, if you set them by environment
environment:
  KEY_S2_Unauthenticated: "aabbccdd..."
  KEY_S2_Authenticated: "11223344..."
  KEY_S2_AccessControl: "55667788..."
  KEY_S0_Legacy: "99aabbcc..."
```

32 hex characters each, no `0x`, no spaces.

## 2. Proximity and the timeout

Two hard constraints that no setting changes:

- **The device must be very close to the controller during S2 inclusion** — within about 30 cm. S2 bootstrapping exchanges several frames and is intolerant of a marginal link. Pair it next to the controller, then install it.
- **The security class grant has a 240-second timeout.** If you don't enter the DSK PIN within that window, inclusion aborts. Have the device's label or box to hand before starting.

For S2 Authenticated and Access Control you must enter the **5-digit DSK PIN** printed on the device. S2 Unauthenticated skips the PIN and gives a weaker class; some devices only offer one class.

## 3. The UI behaviour that looks like failure

A specific and confusing pattern: inclusion appears to fail in the UI while it **continues behind the dialog**. Closing the inclusion panel and reopening it, or refreshing the page, can show the node present and interviewing.

So: before retrying, check the node list. Repeated inclusion attempts create ghost nodes that then have to be removed, which is more work than waiting.

```
Control Panel → the node → Interview stage
```

An interview stuck at *ProtocolInfo* or *NodeInfo* for more than a few minutes means the node isn't responding — different problem from a security failure, and usually distance or a sleeping battery device.

## 4. When bootstrapping fails anyway

The node is included but with a lower class. You cannot upgrade in place; you must exclude and re-include:

```
Control Panel → the node → ⋮ → Remove failed node
# or, if it responds:
Actions → Exclusion → press the device's button
```

If **Remove failed node** refuses, it's because the controller doesn't have that node in its failed list — which requires a failed ping first:

```
Control Panel → the node → Actions → Ping
```

Ping it, let it fail, then remove. If the controller returns an immediate failure without attempting the ping, the node never enters the failed list and the remove command fails. In that case use **Replace failed node** with a new device, or reset the device itself and let the controller time it out.

## 5. Things that look like S2 problems and aren't

- **No `.env`/keys persisted.** A container without a persistent `/usr/src/app/store` volume loses the keys on recreate, and then *every* secure node stops working at once. That's a volume problem.
- **Controller firmware.** 700-series sticks have had firmware bugs affecting inclusion; check for an update via the controller's own tooling.
- **USB extension.** A controller plugged directly into a USB 3 port has markedly worse range. Use a USB 2 port and a short extension cable away from the case — this is the single cheapest improvement to Z-Wave reliability.
- **Device needs factory reset.** A device previously included elsewhere will not join. Reset it per its manual first.

## What not to do

- **Don't retry inclusion repeatedly without checking the node list.** You'll accumulate ghost nodes.
- **Don't use S0 by choice.** It's chatty, slow and floods the network. S2 Unauthenticated is better than S0 for devices that can't do Authenticated.
- **Don't lose the keys.** Store them with your password manager.
- **Don't include devices in place across the house.** Next to the controller, then install.

## Prevention

| Habit | Why |
|---|---|
| Keys generated once and backed up externally | Avoids a full re-pair after any container mishap |
| Persistent volume for the store directory | Same |
| Pair at 30 cm, install afterwards | Removes most bootstrapping failures |
| DSK PIN to hand before starting | Beats the 240-second timeout |

## FAQ

**Does S2 matter for a light switch?**
For locks and garage doors, yes, absolutely. For a lamp, the practical benefit is small and the network cost is real.

**Can I mix S2 and unsecured nodes?**
Yes, and that's normal.

**Node included but no entities in Home Assistant.**
The interview must complete first. A battery device may need waking several times.

**Inclusion works, device drops out days later.**
Mesh problem, not security. Add mains-powered routers and check the network map.
