---
title: "Moonraker 'Database Is Locked'? What SQLite Is Telling You"
slug: moonraker-database-locked
meta_description: "Moonraker logging 'database is locked' and dropping events. Why nested SQLite writers cause it, how to check for a second instance, and how to recover the database safely."
updated: October 2026
cluster: round 12 (tech) — Moonraker GitHub issues; the rest of the SERP is Oracle and IBM
competition: LOW
---

# Moonraker 'Database Is Locked'? What SQLite Is Telling You

Search this error and you get Oracle manuals and IBM support pages. The Moonraker version of it is a different thing entirely.

**`database is locked` is SQLite refusing a second simultaneous writer.** Something already holds a write transaction when another write starts, so the second one fails — and the event it was carrying (telemetry, print history, a job update) is dropped.

## The two realistic causes

**1. Nested writers inside Moonraker**
Reported behaviour: telemetry publication fires while another write transaction is open, a second writer opens, and SQLite rejects it. You see dropped history/telemetry events rather than a crash, which is why prints finish but the history is incomplete.

This is a software-side race, not something you misconfigured. What you can do:
- **Update Moonraker** — these races get fixed as they're reported
- Check the **issue tracker** for your version with the exact log line
- Turn off components you don't need (telemetry, extra sensors, unused plugins) to reduce write pressure

**2. Two things holding the database open**
Check this before anything else:

```bash
sudo systemctl status moonraker
ps aux | grep -c "[m]oonraker"
ls -la ~/printer_data/database/
lsof ~/printer_data/database/moonraker-sql.db 2>/dev/null
```

Classic causes:
- **Two Moonraker instances** (a leftover service from a KIAUH reinstall, or a second printer's instance pointed at the same data dir)
- A **manual `sqlite3` session** you left open in another terminal
- A **backup script** copying the database file while Moonraker writes to it
- The data directory on **NFS/SMB** — network filesystems break SQLite locking. Keep it on local storage, always

## Storage is the hidden third cause

SQLite waits on the filesystem. A dying SD card, a full disk, or heavy I/O makes lock waits long enough to time out:

```bash
df -h ~/printer_data
dmesg -T | grep -i -e "I/O error" -e mmcblk | tail
```

A Pi on a worn SD card produces exactly this error plus a dozen unrelated ones. If you see I/O errors, stop debugging Moonraker and replace the card — ideally with an SSD.

## Recovering the database

Moonraker's database holds history, job queue and some settings — not your printer config (`printer.cfg`) or your gcode. Losing it costs statistics, not your printer.

```bash
sudo systemctl stop moonraker
cd ~/printer_data/database
cp moonraker-sql.db moonraker-sql.db.bak        # keep a copy first
sqlite3 moonraker-sql.db "PRAGMA integrity_check;"
```

- Integrity OK → the lock was live contention, not corruption. Find the second writer
- Corrupt → try `.recover`, or move the file aside and let Moonraker create a fresh one:
  ```bash
  mv moonraker-sql.db moonraker-sql.db.broken
  sudo systemctl start moonraker
  ```

Never delete the file while the service is running, and never delete `printer.cfg` chasing this.

## Prevention

1. **Local storage only** for `printer_data` — never NFS or SMB
2. **One Moonraker per data directory**; clean up old services after a reinstall
3. **Back up with the service stopped**, or use SQLite's backup API — not `cp` on a live file
4. **Watch SD card health**; move to SSD if you print a lot
5. **Keep Moonraker updated**, and read release notes before major jumps

## FAQ

**Does this stop my print?**
Usually not — Klipper runs the print, Moonraker handles the API and history. You lose records, not the job.

**Can I just delete the database?**
Yes, if you accept losing history and the job queue. Stop the service first and keep a backup.

**Why did it start after I added a plugin?**
More write pressure, and some plugins write on every status update. Disable it and see.

**Is `printer.cfg` in the database?**
No. Your configuration is a separate file and isn't affected.
