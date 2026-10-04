---
title: "ZFS Pool Degraded After Reboot: Device Names, Not Dead Disks"
slug: zfs-pool-degraded-after-reboot
meta_description: "A pool comes up DEGRADED or UNAVAIL with a disk 'missing' that is physically fine. Device naming, import by id, and when it really is the drive."
updated: October 2026
cluster: round 13 (tech) — OpenZFS GitHub issues and forums
competition: LOW
---

# ZFS Pool Degraded After Reboot: Device Names, Not Dead Disks

A pool that was healthy before a reboot and DEGRADED after it is usually a **naming** problem, not a hardware one. Before you buy a disk, spend five minutes confirming which.

## 1. Read the status carefully

```bash
zpool status -v
```

The device column tells you most of what you need:

```
  pool: tank
 state: DEGRADED
config:
        NAME                      STATE     READ WRITE CKSUM
        tank                      DEGRADED     0     0     0
          raidz1-0                DEGRADED     0     0     0
            ata-WDC_WD80-ABC123   ONLINE       0     0     0
            ata-WDC_WD80-DEF456   ONLINE       0     0     0
            15738364892193847192  UNAVAIL      0     0     0
```

- **A bare number instead of a name** — ZFS knows a device by GUID but can't find it. This is the naming case.
- **A `/dev/sdX` name and `UNAVAIL`** — almost certainly reordering. `sdc` is now `sdd`.
- **A proper `ata-`/`wwn-` name with non-zero READ/WRITE/CKSUM counts** — a real device problem.
- **`FAULTED` with "too many errors"** — ZFS removed it deliberately after repeated failures.

Zero error counts with an UNAVAIL device is the signature of "present but not found", not "failing".

## 2. Is the disk actually there?

```bash
lsblk -o NAME,SIZE,SERIAL,MODEL
ls -l /dev/disk/by-id/ | grep -v part
```

If the disk appears in `lsblk`, the kernel sees it. Then the pool simply isn't looking in the right place.

```bash
sudo zpool export tank
sudo zpool import -d /dev/disk/by-id tank
```

`-d /dev/disk/by-id` is the important part: it tells ZFS to scan stable, serial-based names rather than whatever `/dev/sdX` happens to be today. In the overwhelming majority of "degraded after reboot" cases, this single command brings the pool back ONLINE with no resilver needed beyond catching up.

Make it permanent:

```bash
sudo zpool set cachefile=/etc/zfs/zpool.cache tank
```

and, on systems that build an initramfs, update it so the pool imports correctly at boot:

```bash
sudo update-initramfs -u -k all    # Debian/Ubuntu
sudo dracut --force                # Fedora/RHEL
```

A pool created with `/dev/sdX` names will keep doing this until you export and re-import by id. Doing that once is the real fix.

## 3. If the disk isn't in `lsblk`

Now it's physical. In order of likelihood:

- **Power or data cable.** Reseat both ends. SATA connectors loosen, and this is the most common actual cause.
- **Backplane or HBA port.** Move the disk to a different port; if it appears, the port is at fault.
- **HBA firmware or a missing driver after a kernel update.** `dmesg | grep -iE 'mpt|sas|ahci|ata[0-9]'` right after boot. An LSI card in IR mode rather than IT mode will also hide disks from ZFS.
- **Power supply marginal.** Eight spinning disks spinning up simultaneously is the peak load on the system. A PSU that's fine at idle can drop a disk on cold boot — the signature is a *different* disk missing each time.
- **The disk is dead.** `smartctl -a /dev/sdX` returning nothing at all, or the disk not spinning up.

## 4. When it really is the disk

```bash
sudo smartctl -a /dev/sdX | grep -E 'Reallocated_Sector|Current_Pending|Offline_Uncorrect|result|Power_On_Hours'
```

Replacement, with the pool still running:

```bash
# physically connect the new disk, find its id
ls -l /dev/disk/by-id/

sudo zpool replace tank 15738364892193847192 /dev/disk/by-id/ata-NEW_DISK_SERIAL
zpool status 1
```

Then wait. A resilver on an 8 TB raidz member can take many hours to days. **During a resilver the pool has no redundancy** (in raidz1 / 2-way mirror), so:

- Don't run a scrub at the same time
- Don't put heavy write load on it
- If you have a second failure here, you lose the pool — which is the argument for raidz2 on large disks

## 5. Checksum errors with no device failure

```
            ata-WDC_WD80-DEF456   ONLINE       0     0    47
```

Non-zero CKSUM with zero READ/WRITE means data came back wrong but the disk accepted the request. Causes, in order: cable, HBA, **RAM**. If multiple disks show checksum errors simultaneously, suspect memory or the controller, not the disks:

```bash
sudo zpool clear tank
sudo zpool scrub tank
```

If errors return after a clear and scrub, test memory before anything else. ZFS will faithfully write corrupted data if the corruption happens before it computes the checksum.

## What not to do

- **Don't `zpool clear` and walk away** on a device with growing error counts. You're suppressing the warning, not fixing it.
- **Don't create pools with `/dev/sdX`.** Use `/dev/disk/by-id`. This is the root cause of the whole naming class.
- **Don't force-import (`-f`) a pool you don't understand** — especially if it may be imported elsewhere (a shared SAS enclosure, a VM passthrough). Dual import corrupts.
- **Don't replace a disk based on a DEGRADED state alone.** Check `lsblk` first; you may be replacing a working drive.
- **Don't run a scrub during a resilver.** You add load exactly when redundancy is lowest.

## Prevention

| Habit | Why |
|---|---|
| Always `zpool create ... /dev/disk/by-id/...` | Eliminates reordering failures permanently |
| ZED email alerts configured and tested | You hear about the first error, not the fourth |
| Monthly scrub, scheduled | Finds rot while redundancy still exists |
| raidz2 (or 3-way mirrors) for disks ≥8 TB | Resilver windows are long enough that a second failure is realistic |
| ECC RAM where you can | ZFS trusts what it's given; bad RAM defeats every other protection |

## FAQ

**Is DEGRADED dangerous?**
It means reduced redundancy. The data is intact and available, but another failure in the same vdev loses it. Treat it as urgent, not as an emergency.

**Can I expand a raidz vdev?**
Modern OpenZFS supports raidz expansion by adding a disk. It's a long operation and doesn't rebalance existing data. Adding a whole vdev is still the simpler route.

**The pool imports but datasets are missing.**
Check `zfs mount -a` and the `canmount`/`mountpoint` properties. Unmounted is different from missing.

**`zpool import` says the pool was last used by another system.**
That's the dual-import guard. Confirm nothing else has it, then `-f`. Don't skip the confirmation.
