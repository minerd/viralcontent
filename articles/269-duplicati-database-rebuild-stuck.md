---
title: "Duplicati Database Rebuild Taking Days? When to Wait and When to Start Over"
slug: duplicati-database-rebuild-stuck
meta_description: "A recreate that stalls around 70%, or downloads every dblock. The old-version bug, why the machine matters, and how to decide between waiting and a fresh backup."
updated: October 2026
cluster: round 12 (tech) — Duplicati forum and GitHub issues only
competition: LOW
---

# Duplicati Database Rebuild Taking Days? When to Wait and When to Start Over

A database recreate that should take an hour is on day three at 73%. Here's how to tell which situation you're in.

## 1. Are you on an old version with the dblock bug?

Older Duplicati versions had a bug where recreate would **download every dblock file** — effectively re-downloading the entire backup — which turns a metadata rebuild into a multi-day transfer.

The documented fix: **abort the recreate, upgrade to 2.0.5.1 beta or newer, and start the recreate again.**

Check your version first. If it's old, this is your answer and nothing else in this article matters.

## 2. Is it downloading dblocks right now?

That's the diagnostic that separates "working" from "doomed":

- **dlist and dindex** files only → normal, metadata-only rebuild, let it run
- **dblock** files being pulled → it's falling back to reading actual data chunks because index files are missing or inconsistent

Watch the live log (**About → Show log → Live → Verbose**) or your bandwidth graph. Sustained heavy download = dblocks.

If it's pulling dblocks, the expected duration is roughly **as long as restoring the whole backup**, because that's effectively what's happening. For a 2 TB backup over a home upload link, that genuinely is days.

## 3. The machine matters more than you'd think

Recreate is SQLite-heavy and **CPU/IO bound**. Reported experience: a rebuild that takes days or weeks on a NAS finishes in hours on a laptop.

If you can:
- Copy the backup destination credentials to a **faster machine**
- Run the recreate there
- Move the resulting `.sqlite` database back

That's the single biggest practical speed-up available, and it's why "it's stuck" is often "it's on a Synology with 1 GB of RAM".

## 4. The 70% wall

Many reports describe progress crawling once it passes roughly **70%**. That's the phase where it starts the expensive work — the earlier percentage is not linear with time. Progress at 70% after a day does **not** mean 30% to go in half a day.

So: don't kill it at 70% assuming it's hung. Check whether dblocks are downloading (section 2) and whether CPU/disk is busy. Busy = working.

## 5. The honest alternative: start a new backup

Duplicati's own forum reaches this conclusion regularly: when a recreate estimate runs to **weeks**, creating a **fresh backup** is faster and leaves you with a known-good state.

You keep the old destination data for restores (you can still restore directly from files without the local database, just slowly), and you start a new job with a new local database.

Decide with arithmetic, not stubbornness:
- Estimated recreate time vs. time for a fresh full backup
- Whether you actually need the old version history
- Whether the old backup's integrity is in doubt anyway (if the database broke, something went wrong)

## 6. Avoid needing a recreate at all

The rebuild only happens because the local database is lost or broken. The causes are preventable:

1. **Back up the Duplicati database and configuration.** Export each job's configuration (Job → Export → *To file*, include the passphrase if you accept the risk), and keep a copy off the machine
2. **Don't store the database on an SD card** — wear kills it
3. **Shut down cleanly**; killed processes mid-backup are the classic cause
4. **Smaller remote volume size** (dblock size) makes everything about recovery faster, at the cost of more files. The default 50 MB is a compromise; many people raise it for speed and then regret it at restore time
5. **Run `verify` jobs** occasionally so you learn about problems early
6. Keep **fewer, larger backup jobs** rather than dozens of tiny ones — each has its own database

## 7. If it genuinely is hung, not slow

```bash
# linux
top -p $(pgrep -f Duplicati)
iostat -x 5
ls -la ~/.config/Duplicati/*.sqlite
```

Zero CPU, zero disk, no network for an extended period = hung. Then stop the service, keep the partial `.sqlite` aside, and restart the recreate (or go to section 5).

## FAQ

**Can I restore without rebuilding the database?**
Yes — direct restore from the destination works without a local database, though it's slower. That's often the right move when you just need files back.

**Should I kill a rebuild at 70%?**
Not on the percentage alone. Check whether it's downloading dblocks and whether the CPU is busy.

**Why does it download everything?**
Missing or inconsistent index files, or an old version with the known bug. Upgrade first.

**Is a fresh backup losing my history?**
Yes, the version history in the new job starts now. The old destination data remains restorable.
