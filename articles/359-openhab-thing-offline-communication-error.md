---
title: "openHAB: Thing OFFLINE - COMMUNICATION_ERROR"
slug: openhab-thing-offline-communication-error
meta_description: "A Thing goes offline with a communication error. What separates it from CONFIGURATION_ERROR, the cache wipe that fixes stuck Things, and the IPv6 trap."
updated: October 2026
cluster: round 14 (tech) — openHAB community forum and openhab-addons
competition: LOW
---

# openHAB: Thing OFFLINE - COMMUNICATION_ERROR

openHAB distinguishes two offline states, and the difference tells you where to look:

| Status detail | Meaning |
|---|---|
| **COMMUNICATION_ERROR** | The binding tried and failed to reach the device. Recoverable; it will retry. |
| **CONFIGURATION_ERROR** | Something in the Thing's config is wrong or unsupported. It will not retry usefully. |

A Thing that flips between COMMUNICATION_ERROR and ONLINE is a network or device problem. One that sits in COMMUNICATION_ERROR permanently, especially after an edit, is often the stuck-Thing case in section 3.

## 1. Read the status description

The UI shows a description next to the status. It is the binding's own message and it is specific:

```
OFFLINE - COMMUNICATION_ERROR
java.util.concurrent.TimeoutException: Total timeout 2000 ms elapsed
```

```
OFFLINE - COMMUNICATION_ERROR
Connection refused: localhost/127.0.0.1:8080
```

Then raise the binding's log level:

```
# in the openHAB console (ssh -p 8101 openhab@localhost)
log:set DEBUG org.openhab.binding.mqtt
log:tail
```

## 2. The IPv4/IPv6 localhost trap

A recurring cause with bindings that talk to a service on the same host: the service binds to **IPv6 localhost** while the binding resolves `localhost` to IPv4, or vice versa. The symptom is `Connection refused` to `127.0.0.1` for a service you can see running.

```bash
sudo ss -tlnp | grep 8080
# tcp LISTEN 0 128 [::1]:8080   → IPv6 only
```

Use an explicit address in the Thing config — `127.0.0.1` or `::1` to match — rather than `localhost`. Or add a JVM option to prefer IPv4:

```
# /etc/default/openhab → EXTRA_JAVA_OPTS
-Djava.net.preferIPv4Stack=true
```

## 3. The stuck Thing: cache wipe

A Thing defined in a `.things` file and then edited in the UI (or the reverse) can end up in an inconsistent state that no restart clears. The documented remedy is deliberate and works:

```bash
sudo systemctl stop openhab
sudo openhab-cli clean-cache
sudo systemctl start openhab
```

`clean-cache` clears the OSGi bundle cache and forces openHAB to rebuild it. The first start afterwards is slow — several minutes — and that is expected, not a hang.

Before that, try the lighter version: **disable and re-enable the Thing** (the clock icon in the UI). That re-runs `initialize()` on the handler and fixes a good share of stuck Things in seconds.

If the Thing was created in a file, it cannot be edited in the UI; the UI copy and the file copy fight. Pick one management method per Thing and stick to it.

## 4. TLS and cipher failures

For bindings talking HTTPS to local devices:

```
OFFLINE - COMMUNICATION_ERROR
javax.net.ssl.SSLHandshakeException: No appropriate protocol
(protocol is disabled or cipher suites are inappropriate)
```

This is the JVM refusing an obsolete protocol, which is correct and increasingly common with older IoT devices that only speak TLS 1.0. The options, worst to best: re-enable TLS 1.0 in the JVM's `java.security` (not recommended), put a modern TLS-terminating proxy in front of the device, or use the device's plain-HTTP endpoint on a trusted VLAN.

## 5. Bindings that never retry

A real behavioural gap in some bindings: after a **failed initialization**, the Thing stays OFFLINE permanently with no retry, so a device that was merely booting at openHAB startup never comes back. The workaround is a rule that re-enables Things on a communication error:

```javascript
// Rule: trigger on Thing status change
things.getThing('mqtt:topic:mything').setEnabled(false);
things.getThing('mqtt:topic:mything').setEnabled(true);
```

Trigger it on the Thing's status changing to OFFLINE, with a delay so you don't loop during a genuine outage.

## What not to do

- **Don't delete and recreate Things as a first step.** You lose Item links, and the cause is usually recoverable.
- **Don't mix file-based and UI-based definitions for the same Thing.** It's the main source of stuck states.
- **Don't run `clean-cache` casually.** It's safe but costs a slow restart; try disable/enable first.
- **Don't re-enable TLS 1.0 globally** to fix one device.

## Prevention

| Habit | Why |
|---|---|
| Explicit IP addresses, not `localhost`, in Thing configs | Removes the IPv4/IPv6 class |
| One management method per Thing (files or UI) | Avoids inconsistent state |
| A re-enable rule for critical Things | Covers bindings that don't retry |
| Static DHCP reservations for every device | Most COMMUNICATION_ERRORs are address changes |

## FAQ

**Thing is ONLINE but Items don't update.**
Different problem: channel linking, or the device not reporting. Check the channel's state in the UI directly.

**All Things offline after an upgrade.**
Run `clean-cache`. Bundle cache mismatches after a major upgrade are the usual cause.

**UNINITIALIZED - HANDLER_MISSING_ERROR?**
The binding isn't installed, or failed to load. Check `bundle:list | grep <binding>` in the console.

**How do I see history of a Thing's status?**
Enable persistence on the Thing's status, or watch `events.log`, which records every status change.
