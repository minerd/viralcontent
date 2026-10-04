---
title: "SnapRAID Sync Errors: \"Unexpected time change\" and Missing Files"
slug: snapraid-sync-errors
meta_description: "Sync aborts on a time change, UUID change, or too many deletions. What each guard is protecting you from, and the safe way past it."
updated: October 2026
cluster: round 13 (tech) — SnapRAID forum and GitHub
competition: LOW
---

# SnapRAID Sync Errors: "Unexpected time change" and Missing Files

SnapRAID's error messages look like faults but most are **deliberate safety stops**. Each one is protecting your parity from an action that would silently destroy its ability to recover data. Understanding which guard tripped tells you whether to override it or to stop and investigate.

## 1. "Unexpected time change at file ..."

```
Unexpected time change at file 'data1/movies/x.mkv'.
WARNING! You cannot modify files during a sync.
```

SnapRAID hashed the file, then found its modification time changed mid-run. Causes:

- Something wrote to the array during the sync (a download client, a media scanner writing metadata, a backup job)
- The system clock jumped (NTP correcting a large offset, or a VM resuming)
- A filesystem with coarse timestamp granularity after a move

**What to do:** re-run `snapraid sync`. If it completes, the file was simply in flux. If it trips repeatedly on the same file, find what's writing to it:

```bash
sudo lsof +D /mnt/data1 | head -20
```

Schedule syncs when nothing is writing. A sync during an active download will always be a fight.

## 2. "UUID change for disk ..."

```
UUID change for disk 'd1' from 'abc-123' to 'def-456'
```

SnapRAID tracks each data disk by filesystem UUID. A change means either:

- **You replaced or reformatted the disk.** Expected — but SnapRAID can't tell this apart from the dangerous case.
- **The mount points got swapped.** A disk mounted at `/mnt/data1` is now a *different* physical disk. If you sync now, SnapRAID will treat every file as deleted and every file on the new disk as added, destroying the parity relationship for the real data.

**This is the one to take seriously.** Before overriding anything:

```bash
lsblk -o NAME,UUID,MOUNTPOINT,SIZE
cat /etc/fstab
snapraid status
```

Confirm each mount point holds the disk you expect. If mounts are swapped, fix `/etc/fstab` to mount by UUID — never by `/dev/sdX`, which changes order — and re-run. If you genuinely replaced a disk, the correct procedure is `snapraid fix -d dN` to restore it, not a sync.

```
# /etc/fstab — mount by UUID, always
UUID=abc-123-def  /mnt/data1  ext4  defaults  0 2
```

## 3. "You have N deleted files" / "exceeded the --force-empty threshold"

```
You have 2847 deleted files.
Use 'snapraid sync -E' to sync anyway.
```

SnapRAID stops when a large proportion of files vanished, because that's the signature of a disk that failed to mount — the directory is empty, so every file looks deleted. Syncing would overwrite parity with the information "those files don't exist", after which you cannot recover them.

**Before using `-E` or `--force-empty`, verify the disk is actually mounted and actually empty on purpose:**

```bash
findmnt /mnt/data1
ls /mnt/data1 | head
df -h /mnt/data1
```

A directory that exists but isn't a mount point is the failure case. SnapRAID's `content` files include a check for this if you declare them properly — put a `content` file on **every** data disk:

```ini
content /mnt/data1/snapraid.content
content /mnt/data2/snapraid.content
content /mnt/parity1/snapraid.content
```

With a content file per disk, an unmounted disk means a missing content file, and SnapRAID refuses to run at all — a much better failure than a destructive sync. This is the most valuable configuration habit in SnapRAID.

## 4. Silent errors found by scrub

```bash
snapraid scrub -p 10 -o 7
snapraid status
```

```
There are 3 files with zero sub-second timestamps.
DANGER! 2 errors in the array!
```

A scrub error means data read back differently from its hash — bit rot, a failing drive, or bad RAM. Procedure:

```bash
snapraid -e fix          # fix only the blocks marked in error
snapraid scrub -p 100    # verify
```

Then check SMART on every disk:

```bash
for d in /dev/sd?; do echo "== $d"; sudo smartctl -H -A "$d" | grep -E 'Reallocated|Pending|Uncorrect|result'; done
```

If errors recur in the same place after a fix, the disk is failing. Replace it rather than fixing repeatedly.

If errors appear across *multiple* disks at once, suspect RAM or the controller, not the disks. Run a memory test before touching the array — bad RAM plus a fix operation can write corruption into good files.

## 5. The right operation order

```bash
snapraid diff          # see what changed — always first
snapraid sync          # update parity
snapraid scrub -p 10   # verify 10% of the oldest data
snapraid status        # review
```

`snapraid diff` before every sync is the habit that prevents all of the above from becoming data loss. It tells you how many files were added, removed and moved. If the numbers surprise you, stop.

## What not to do

- **Don't use `-E` / `--force-empty` reflexively.** It exists for legitimate mass deletions. Used on an unmounted disk, it is the one command that will cost you data.
- **Don't sync immediately after a disk failure.** Fix first. Syncing commits the failure into parity.
- **Don't mount by `/dev/sdX`.** Device order changes across reboots and controller changes.
- **Don't skip scrubs.** Parity you never verify is parity you don't know you have.
- **Don't treat SnapRAID as a backup.** It protects against disk failure, not deletion, ransomware or fire. A deleted file synced into parity is gone.

## Prevention

| Habit | Why |
|---|---|
| `content` file on every disk | Turns an unmounted disk into a refusal instead of a disaster |
| `snapraid diff` before every sync, read the numbers | Catches every one of the above before it commits |
| Mount by UUID in fstab | Eliminates the swapped-disk class |
| Scheduled `sync` + rolling `scrub`, with the output emailed | You learn about rot in weeks, not years |
| SMART monitoring with alerts | Replace disks before they take data with them |

## FAQ

**How much parity do I need?**
One parity disk tolerates one disk failure. With 8+ data disks or very large drives, two is the common recommendation — rebuild times are long and a second failure during rebuild is a real risk.

**Can parity be smaller than the data disks?**
No. Each parity disk must be at least as large as the largest data disk.

**Does it work with mergerfs?**
Yes, and that's the standard pairing. Point SnapRAID at the individual disks, never at the mergerfs mount.

**Sync is extremely slow.**
It reads every changed file plus parity. Check for a disk with high latency in `iostat -x 5`; one failing drive throttles the whole run.
