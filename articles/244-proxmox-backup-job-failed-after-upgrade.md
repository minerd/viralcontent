---
title: "Proxmox Backup Job Failing After an Upgrade? Read the Task Log First"
slug: proxmox-backup-job-failed-after-upgrade
meta_description: "Backups that ran for months fail after a Proxmox upgrade. Kernel regressions, storage format changes, fleecing, verify failures and the exact log lines to look for."
updated: October 2026
cluster: round 11 (tech) — Proxmox forum threads only
competition: LOW
---

# Proxmox Backup Job Failing After an Upgrade? Read the Task Log First

Backups ran nightly for a year. You upgrade PVE or PBS, and now jobs fail — on some VMs, not all — or finish "with errors", or crash the guest while they run.

Everything useful is in the **task log**. Start there, because the five causes below look nothing alike once you've read it.

## Get the real error

**In the GUI:** Datacenter → Backup → the job → the failed task → **open the log**. Also Tasks at the bottom of the node view.

**On the CLI:**
```bash
# the backup task's own log
cat /var/log/pve/tasks/*/UPID*vzdump*
journalctl -u pvescheduler -u pvedaemon --since "yesterday"
pveversion -v                      # paste this in any forum post
# PBS side
journalctl -u proxmox-backup-proxy --since "yesterday"
```

Match the error text against this table before changing anything:

| In the log | Likely cause |
|---|---|
| `job failed with err -11` (EAGAIN) on some VMs | Resource/lock contention — often a stuck previous task or a QEMU bug |
| `VM is locked (backup)` | A previous job left a lock |
| `volume ... does not exist` / format error | Storage or volume format change after upgrade |
| Guest crashed/reset during backup | **Kernel or QEMU regression** — see below |
| `verify failed` on many snapshots in PBS | Verification/chunk problem, not the backup itself |
| `no space left on device` | Datastore or local staging full |
| `connection refused` / TLS errors to PBS | Fingerprint, certificate, or PBS not running |
| `unable to open file ... permission denied` | Storage permissions after an upgrade |

## 1. Kernel regressions — the most frequent post-upgrade cause

Proxmox ships new kernels regularly, and backup-time VM crashes have been traced to specific kernel versions, with the fix being a newer kernel from the test/no-subscription repository.

Act on this the same way you would any kernel issue:
```bash
proxmox-boot-tool kernel list
proxmox-boot-tool kernel pin <known-good-version>
proxmox-boot-tool refresh
reboot
```
If backups succeed on the older kernel, you have your answer — then watch the forum's known-issues thread for the release that fixes it, rather than leaving the pin forever.

Also check **CPU microcode** and system firmware; several backup-crash threads end with a BIOS or microcode update.

## 2. Stale locks and the scheduler

```bash
qm unlock <vmid>          # only after confirming no task is running
ls /var/lock/qemu-server/
systemctl restart pvescheduler
```
A job that was killed mid-run leaves a lock, and every subsequent attempt fails instantly. Restarting `pvescheduler` is a documented fix for jobs that simply stop firing after an upgrade.

Check for a **stuck task** in the task list before unlocking anything — unlocking a VM that genuinely has a running backup is how you corrupt one.

## 3. Snapshot mode, fleecing and I/O pressure

If guests stall or crash *during* backups:

- **Snapshot mode** needs the storage to support snapshots. After a storage change (LVM-thin → LVM, or a new ZFS dataset layout) the mode you had may no longer be valid for that disk
- Enable **fleecing** (Proxmox's backup fleecing option) — it absorbs guest writes during backup and is the designed answer to guests stalling under backup I/O
- Add **bandwidth limits** to the job so backups don't saturate the storage
- Stagger job schedules so several nodes don't hit one PBS datastore at once

## 4. PBS side: verify failures and datastore health

A wave of `verify failed` after an upgrade points at the datastore, not the backup job:

- Check **datastore free space** — PBS needs room for garbage collection and chunk writes
- Run **garbage collection** and then a **verify** job, and read which chunks fail
- Check the underlying disks: `zpool status`, SMART. Repeated chunk corruption is a hardware story
- Confirm the **fingerprint** in the PVE storage config still matches PBS's certificate (it changes if you regenerate certs)

## 5. Storage and permissions

- `volume ... does not exist`: a volume naming/format change after upgrade. The forum fix is renaming on the storage and updating the config — read the specific thread for your storage type before renaming anything
- NFS/CIFS backup targets: check the mount is actually mounted (an empty directory is a classic), and that `root` can write
- Verify the storage still has the **Backup** content type enabled

## Before the next upgrade

1. **Read the release's known-issues thread** on the Proxmox forum — these regressions are documented there first
2. **Keep two kernels** and know how to pin
3. **Test one VM's backup** right after upgrading rather than finding out at 2am
4. **Monitor the job results** (email/webhook notifications) so a silent failure doesn't run for weeks
5. Keep **restore** tested too — a backup you've never restored is a hypothesis

## FAQ

**Why do only some VMs fail?**
Usually resource contention, a specific disk's snapshot capability, or guest-side behaviour under I/O — not a global config problem.

**Is pinning a kernel safe?**
As a bridge, yes. Don't leave it pinned indefinitely; you'll miss security fixes.

**`err -11` on two of six VMs — what is it?**
EAGAIN: something was temporarily unavailable. Look for locks, concurrent jobs, and kernel/QEMU version issues.

**Should I switch snapshot mode to stop/suspend?**
It's a valid workaround while diagnosing, at the cost of downtime. Fleecing is the better answer if your storage supports it.
