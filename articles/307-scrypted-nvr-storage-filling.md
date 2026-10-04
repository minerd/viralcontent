---
title: "Scrypted NVR Storage Keeps Filling Up (Even After Deleting)"
slug: scrypted-nvr-storage-filling
meta_description: "Recordings are pruned but free space doesn't return. The NAS recycle bin, snapshots, and the retention settings that aren't what you think."
updated: October 2026
cluster: round 13 (tech) — Scrypted Discord and GitHub
competition: LOW
---

# Scrypted NVR Storage Keeps Filling Up (Even After Deleting)

Scrypted NVR prunes old recordings on its own. When the disk fills anyway, the usual cause is that something is *keeping* the deleted files — and that something is almost never Scrypted.

Check in this order. The first two account for most cases.

## 1. The NAS recycle bin

If your recordings live on a Synology, QNAP or TrueNAS share, and that share has a recycle bin enabled, every file Scrypted deletes is **moved, not removed**. The NVR correctly reports that it pruned; the disk correctly reports that it's full.

On Synology, the folder is `#recycle` at the root of the share:

```bash
du -sh /volume1/nvr/#recycle
```

Disable it for this share specifically — **Control Panel → Shared Folder → Edit → Enable Recycle Bin**, unchecked. A recycle bin makes sense for documents and is actively harmful for a surveillance share that rewrites terabytes a month.

On TrueNAS the equivalent is the SMB share's **Export Recycle Bin** option, plus any **periodic ZFS snapshots** covering the dataset.

## 2. ZFS snapshots

This is the subtler version of the same problem. A snapshot pins every block that existed when it was taken. Delete a 500 GB month of footage with a snapshot covering it and you free nothing.

```bash
zfs list -t snapshot -o name,used -s used tank/nvr
```

If `used` on the snapshots is large, that's your missing space. For a recording dataset, the correct configuration is **no periodic snapshots at all** — there is nothing to recover; the footage is transient by design.

```bash
# remove the periodic snapshot task for the dataset first, then
zfs destroy tank/nvr@auto-2026-09-01_00-00
```

Also check `zfs get reservation,refreservation,quota tank/nvr` — a reservation on a sibling dataset can make this one look full.

## 3. Retention settings that don't do what you expect

In Scrypted NVR's settings, per camera, there are two independent limits: a **duration** (keep N days) and a **size** (use at most N GB). Several things trip people up:

- The settings are **per camera**. Eight cameras at 500 GB each is 4 TB, not 500 GB. Adding a camera without lowering the others is the most common "it suddenly filled up".
- A **duration-only** setting with no size cap means a camera that starts recording more (a new motion zone, a change from motion to continuous) grows without bound.
- Changing the retention down does not delete immediately; pruning runs on a schedule.

Set a size cap on every camera, and make the sum comfortably less than the volume's capacity. Leave real headroom: ZFS performance degrades badly above about 80% full, and a filesystem at 100% can corrupt in-flight writes.

## 4. What's actually using the space

Before changing anything, measure:

```bash
# per-camera usage
du -sh /path/to/nvr/* | sort -h | tail -20

# is the filesystem lying to you? deleted-but-open files
sudo lsof +L1 | head -20
```

`lsof +L1` lists files with a link count of zero that a process still holds open — the classic "I deleted it and nothing happened" on Linux. If Scrypted is holding a deleted multi-gigabyte file, restarting the container releases it. This is rarer than the recycle bin but takes ten seconds to rule out.

## What not to do

- **Don't delete recording files by hand** from the filesystem. Scrypted's index then references files that don't exist, and the UI shows unplayable events. Use the retention settings.
- **Don't fill the volume to 95% and leave it.** On ZFS especially, this is where write amplification and fragmentation make everything slow, and the slowness reads as a Scrypted problem.
- **Don't put recordings on the same dataset as anything you snapshot.** One policy can't suit both.
- **Don't enable continuous recording on every camera to "be safe"** without doing the arithmetic. 8 cameras × 4 Mbps × 30 days is roughly 10 TB.

## Prevention

| Habit | Why |
|---|---|
| Dedicated dataset/share for NVR, no snapshots, no recycle bin | Removes the two main causes permanently |
| Size cap on every camera, summing to ~70% of the volume | Headroom for growth and filesystem health |
| Re-check totals whenever you add a camera | Per-camera limits don't self-adjust |
| A disk-usage alert at 80% | Gives you days of warning instead of a full disk |

## FAQ

**Does Scrypted NVR support a separate fast cache disk?**
You can point it at any mount. A common layout is an SSD for the active segment and spinning disk for the bulk, but Scrypted won't tier automatically.

**Can I keep some events forever?**
Export the clips you want to keep out of the NVR storage. Anything inside the retention-managed directory is subject to pruning.

**Recordings stopped and the disk shows free space.**
Check inodes (`df -i`) and permissions on the directory — a read-only remount after an I/O error presents exactly this way.

**H.265 to save space?**
Yes, roughly 40% smaller for the same quality, if your cameras and your clients both handle it. Check playback on the devices you actually use before converting everything.
