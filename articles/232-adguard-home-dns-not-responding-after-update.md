---
title: "AdGuard Home Not Responding After an Update? Config, Ports and the 100% CPU Window"
slug: adguard-home-dns-not-responding-after-update
meta_description: "DNS stops resolving after an AdGuard Home update. Why the service may not be running, what the blocklist-update CPU spike does, and how to recover from your YAML."
updated: October 2026
cluster: round 10 (tech) — AdGuardHome GitHub issues and router/firewall forums
competition: LOW
---

# AdGuard Home Not Responding After an Update? Config, Ports and the 100% CPU Window

The whole house loses the internet, which in practice means **DNS stopped working**. The web UI may still load, or may not. Reboots don't help.

Because this takes down everything, start by restoring service and diagnose afterwards.

## Step 0: get the network working again

Point your router's DHCP (or the one machine you need) at **1.1.1.1 / 8.8.8.8** temporarily. Now you can research the problem on a working connection, and nobody in the house is standing behind you.

## Step 1: is the service actually running?

```
systemctl status AdGuardHome        # binary install
docker compose ps && docker compose logs --tail=100 adguardhome
```

What you're looking for in the logs:
- **Port 53 already in use** — the single most common post-update failure. `systemd-resolved` (Linux), another resolver, or a leftover container has taken it:
  ```
  sudo ss -lntup | grep ':53'
  ```
  On Ubuntu/Debian, `systemd-resolved` re-enabling itself after a system upgrade is the classic. Disable its stub listener (`DNSStubListener=no`) and restart it
- **Config parse error** — AdGuard refuses to start on invalid YAML. The log names the line
- **Permission denied binding to 53** — a capability lost after a package update (`CAP_NET_BIND_SERVICE`), or a container that lost `--cap-add`

## Step 2: the blocklist-update CPU spike

A documented behaviour: while filter lists are being updated, **CPU can hit 100% and DNS resolution fails for around a minute**. On low-power hardware (Pi Zero, cheap router, small VM) it can be much longer.

If your outages are **periodic and short**, this is the likely cause, not the update you just installed:
- Reduce the **number and size** of blocklists — a handful of good lists beats thirty overlapping ones
- Lengthen the **filter update interval**
- Give the box more CPU, or move AdGuard off a Pi Zero
- Run a **second DNS server** on the network so a one-minute stall isn't an outage (two AdGuard instances, not AdGuard plus an unfiltered resolver, or you lose filtering)

## Step 3: upstream DNS and DNS rewrites

- **Upstreams unreachable:** if you use DoH/DoT upstreams, they need working *bootstrap* DNS. A config change that removed bootstrap servers breaks everything with a confusing error
- Test upstreams from the box: `dig @1.1.1.1 example.com`
- **DNS rewrites stopped working** is its own reported post-update regression — if blocking works but your local hostnames don't resolve, check the Rewrites page and the issue tracker for your version
- **Private reverse DNS / local domain** settings get reset by some upgrades, breaking internal name resolution

## Step 4: recover from your YAML

`AdGuardHome.yaml` holds everything — settings, lists, rewrites, clients. The documented recovery path when a version is broken:

1. **Copy `AdGuardHome.yaml` somewhere safe**
2. **Remove / reinstall** AdGuard Home (or roll the container image back to the previous tag)
3. **Put the YAML back** and start the service

That turns a reinstall into a five-minute job instead of reconfiguring from scratch. Back that file up on a schedule — it's the only thing you need.

## Step 5: platform-specific traps

- **OPNsense/pfSense plugins**: a firewall update can ship a plugin version that doesn't start. Check the firewall's own forum thread for that release
- **Router firmware (Asuswrt-Merlin etc.)**: AdGuard not starting after firmware updates is common; the script and binary paths change
- **Home Assistant add-on**: check the add-on log, and whether the DNS port is still mapped
- **Docker**: if you switched to `latest` and it broke, pin the previous tag. Also confirm the host didn't start resolving on 53 itself after a host reboot

## Before the next update

1. **Back up `AdGuardHome.yaml`** (automate it)
2. **Pin container tags**; don't run `latest` on infrastructure the whole house depends on
3. Keep a **second resolver** configured somewhere you can switch to in a minute
4. Know the **DHCP change** by heart so you can restore internet access instantly
5. Update when you have time to watch the log, not at 11pm

## FAQ

**Why does the web UI work but DNS doesn't?**
The HTTP listener is up and the DNS listener isn't — usually port 53 taken by another resolver, or an upstream failure.

**DNS dies for about a minute, regularly.**
That's the filter-update CPU spike. Trim lists or lengthen the interval.

**Should I set an unfiltered secondary DNS on the router?**
No — clients will use it and bypass filtering. Run two filtered resolvers instead.

**Is reinstalling safe?**
Yes, if you keep `AdGuardHome.yaml`. That file is your whole configuration.
