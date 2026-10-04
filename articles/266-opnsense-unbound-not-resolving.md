---
title: "OPNsense Unbound Not Resolving After an Update? Restart It, Then Check DNSBL"
slug: opnsense-unbound-not-resolving
meta_description: "DNS dies after an OPNsense upgrade. The DNSBL refresh bug, corrupted root hints, outgoing interface settings and how to restore just the Unbound config."
updated: October 2026
cluster: round 12 (tech) — OPNsense forum threads and core GitHub issues
competition: LOW
---

# OPNsense Unbound Not Resolving After an Update? Restart It, Then Check DNSBL

DNS stops after an upgrade, which means the whole network looks broken. Get service back first, diagnose second.

## Step 0: restore service

Point a client at **1.1.1.1** temporarily so you can research on a working connection. Then:

**Services → Unbound DNS → Restart** (or `configctl unbound restart`). A restart alone fixes a meaningful share of post-upgrade cases, because the service comes up before something it depends on.

## 1. Intermittent SERVFAIL = the DNSBL refresh

A documented OPNsense behaviour: when the **Unbound DNSBL** list refreshes, the running Python DNSBL module can throw exceptions on new queries, producing **intermittent SERVFAIL** — failure rates in the 9–18% range — until Unbound is restarted.

Recognise it by the pattern: **some** queries fail, not all; it comes and goes; a restart fixes it for a while.

Mitigations:
- Reduce the **number and size** of blocklists
- Change the **DNSBL update schedule** to an hour you don't care about
- Add a **cron job** to restart Unbound after the blocklist refresh
- Watch the Unbound log for `pythonmod` exceptions to confirm

## 2. Total failure = config or root hints

If nothing resolves at all:

```
# at the console / SSH
unbound-checkconf /var/unbound/unbound.conf
cat /var/unbound/root.hints | head
drill @127.0.0.1 example.com
```

Reported after one upgrade: **corrupted root hints**, with log lines like *"Syntax error, could not parse the RR's type"*. Fix by letting OPNsense re-fetch the root hints file, or replacing it from `https://www.internic.net/domain/named.root`.

Also check:
- **Outgoing Network Interfaces**: setting this to **WAN** rather than the default *All* has resolved failures for people. With *All*, Unbound can try to send queries from an interface with no route out
- **Incoming interfaces** still include your LANs
- **DNSSEC** enabled with a broken upstream, or a clock that's wrong (DNSSEC fails hard on time skew)
- **Port 53 conflicts** with Dnsmasq/AdGuard/Pi-hole also installed on the box

## 3. Restore only the Unbound configuration

A clean trick worth knowing: **System → Configuration → Backups → Restore**, and restore **only the Unbound section** from a pre-upgrade backup. That's a documented fix for an upgrade that left the Unbound config in a bad state, without rolling back the whole firewall.

You need a backup from before the upgrade — OPNsense keeps config history on the box (**System → Configuration → History**), which is usually enough.

## 4. Plugin vs built-in

If you also run the **AdGuard Home plugin**, note that firewall updates have shipped plugin versions that don't start. Check the OPNsense forum thread for your release, and decide which resolver owns port 53. Two resolvers both wanting 53 is a reliable way to lose DNS on every reboot.

## 5. Read the log, not the dashboard

```
# Services → Unbound DNS → Log File, or:
tail -f /var/log/resolver/latest.log
```

The actual reason — a parse error, an interface problem, a Python exception, an upstream refusal — is in there, and it decides which section above applies.

## Prevention

1. **Keep a second resolver** you can switch clients to in a minute
2. Note how to change **DHCP DNS** by heart
3. **Keep the config history** (it's on by default) and know how to restore a single section
4. Read the **release notes and the forum thread** before upgrading a firewall
5. Upgrade when you have **console access**, not remotely from elsewhere

## FAQ

**Why do only some queries fail?**
That's the DNSBL refresh pattern. A restart clears it; trimming lists and rescheduling reduces it.

**Should I set outgoing interfaces to WAN?**
It's a documented fix when resolution fails after an upgrade. Try it and keep it if it helps.

**Can I restore just Unbound's settings?**
Yes — restore that section only from a config backup or the on-box history.

**Unbound or AdGuard Home on OPNsense?**
Pick one for port 53. Running both without a clear split is how DNS breaks at every reboot.
