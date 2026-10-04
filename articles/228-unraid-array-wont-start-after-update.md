---
title: "Unraid Array Won't Start After an Update? Empty Pools and Safe Mode"
slug: unraid-array-wont-start-after-update
meta_description: "After an Unraid upgrade the array won't start or hangs on Starting. Empty pools with no device assigned, plugin conflicts and safe mode — plus how to roll back."
updated: October 2026
cluster: round 10 (tech) — Unraid forum threads only
competition: LOW
---

# Unraid Array Won't Start After an Update? Empty Pools and Safe Mode

You upgrade Unraid, reboot, and the array either refuses to start with no useful message, or sits on **"Starting..."** indefinitely. Downgrading fixes it, which tells you it's the new release interacting with your configuration — not your disks.

Two causes dominate the reports, and they're both quick to check.

## 1. A pool with no device assigned (the 7.x classic)

Newer Unraid releases are **strict about pools**: you cannot have a pool defined with **no device assigned to it**. An empty pool left over from an old cache setup, or created and never populated, blocks array start after the upgrade.

Fix:
1. **Main** tab → look at each pool, including ones you'd forgotten
2. Any pool with **no device**: click it and choose **Remove pool**
3. Start the array

This is the reported resolution for the 7.1.x → 7.2.x "array won't start, works again after downgrade" pattern, and for empty cache pools after 7.0.x upgrades. Check it before anything else.

## 2. Plugins

Plugins hook deep into the OS, and a release upgrade can leave an incompatible one blocking array start.

- **Boot in Safe Mode** (no plugins): from the boot menu, choose the Safe Mode entry. If the array starts in safe mode, a plugin is your culprit
- Then boot normally and **update every plugin** — particularly **Unraid Connect** and the **NVIDIA/driver** plugins, which are the usual suspects
- The right order is: **update plugins first, then upgrade Unraid**. Doing it the other way round causes exactly this

## 3. Disks spun down, missing or unassigned

- **USB-attached or JBOD disks showing as spun down** after an upgrade have blocked array start. Power-cycle the enclosure; USB enclosures are a known weak point for array membership and are best avoided for array disks
- A disk that enumerated differently: compare the **assigned devices** against what's physically present. Unraid identifies disks by serial, so a genuinely missing serial means a cable, a power connector, or a dead drive
- **Never** reassign disks to different slots to "fix" a layout you don't understand — that's how parity gets invalidated. Get help on the forum with your diagnostics first

## 4. Read the diagnostics, not the dashboard

**Tools → Diagnostics** produces a zip with syslog and disk detail. That's what the forum will ask for, and it usually contains the actual reason:

- Look in `syslog` for the array start attempt and what failed
- `unassigned` or filesystem errors on a specific disk
- An unmountable filesystem — that's a different problem (file system check, not array config), and **don't format anything**

Also: `tail -f /var/log/syslog` in a terminal while you click Start, and watch what appears.

## 5. Stuck on "Starting..." specifically

- Give it **real time** if a parity check or a filesystem check is running underneath
- Look for a disk the system is waiting on (spin-up timeout) in syslog
- An **unmountable pool** can hold the whole start sequence
- Docker/VM services starting against a pool that isn't ready — disable **Docker** and **VM Manager** autostart (Settings), start the array clean, then re-enable them one at a time

## Rolling back

Unraid makes this straightforward and there's no shame in it:

- **Tools → Update OS → Restore Previous Version** (or restore the previous `bz*` files from the flash backup)
- Keep a **flash drive backup** before every upgrade — Main → Flash → Flash Backup. It's your config, and it's the difference between a rollback and a rebuild

Then upgrade again later, with plugins current and empty pools removed.

## Before the next upgrade

1. **Back up the flash drive**
2. **Update all plugins**
3. Read the release's **forum announcement thread** — breaking changes land there first
4. Remove **unused pools** and stale config
5. Upgrade when you can be at the machine with a monitor attached

## FAQ

**Why does downgrading fix it?**
Because the new release enforces something your configuration violates — most often an empty pool.

**Is my data at risk?**
Not from a failed array start by itself. It's at risk from reassigning disks or formatting things while guessing.

**Should I run a parity check after this?**
If the array starts cleanly and nothing was reassigned, there's no need to force one. If you changed disk assignments, stop and ask on the forum with diagnostics attached.

**Safe mode starts the array fine. Now what?**
A plugin is the cause. Update all of them, or disable them one at a time to find it.
