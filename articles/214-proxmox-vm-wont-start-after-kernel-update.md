---
title: "Proxmox VM Won't Start After a Kernel Update? Boot the Old Kernel First"
slug: proxmox-vm-wont-start-after-kernel-update
meta_description: "After a Proxmox kernel upgrade, VMs failing to start usually trace to ZFS module mismatch, a stale initramfs, lost passthrough or a full /boot. Recovery order and how to pin a kernel."
updated: October 2026
cluster: round 9 (tech) — Proxmox forum threads only
competition: LOW
---

# Proxmox VM Won't Start After a Kernel Update? Boot the Old Kernel First

You ran updates, rebooted the node, and now guests won't start — or the host itself won't come up cleanly. The Proxmox forum is full of these threads and they resolve the same handful of ways.

**Rule one: get back to a working kernel before you change anything else.** Diagnose from a running system, not from a rescue shell.

## Step 1: boot the previous kernel

At boot, open the GRUB menu (hold **Shift** on BIOS systems; use the boot menu on systemd-boot/EFI installs), choose **Advanced options for Proxmox VE**, and select the **previous kernel version**.

If the node and the VMs come up normally, you've confirmed it's the new kernel and bought yourself time to fix it properly.

## Step 2: find out which failure you have

**ZFS module mismatch**
Root on ZFS, and the new kernel's ZFS module doesn't match the installed `zfs-utils`/DKMS build. Pools don't import, VM disks aren't there, guests fail instantly.
```
zpool status        # pools visible at all?
dmesg | grep -i zfs # module load errors
```

**Stale or broken initramfs**
The new kernel's initramfs was built badly or wasn't written to the ESP. Rebuild from the working kernel:
```
update-initramfs -u -k <new-kernel-version>
proxmox-boot-tool refresh
```

**/boot or the ESP is full**
Classic. A failed update leaves half-written images and nothing boots properly.
```
df -h /boot /boot/efi
```
Remove old kernels through `apt`, never by deleting files by hand:
```
apt autoremove --purge
proxmox-boot-tool kernel list
proxmox-boot-tool refresh
```

**Lost PCIe passthrough**
A GPU, HBA or NIC passed into a VM stops binding to `vfio-pci` after a kernel change: new IOMMU grouping, a module load order change, or a driver in the new kernel claiming the device first. Guests with passthrough fail to start while others are fine.
```
dmesg | grep -i -e iommu -e vfio
lspci -nnk   # which driver is bound?
```
Re-check `/etc/modprobe.d/` blacklists and your kernel command line, and rebuild the initramfs after changes.

**Missing out-of-tree modules**
DKMS modules (ZFS, some NIC drivers, nvidia) that didn't rebuild for the new kernel:
```
dkms status
apt install --reinstall proxmox-kernel-<version>
depmod -a
```

**Guest-side kernel panic**
If the **host** is fine and a specific Linux **VM** panics at "switch root", the guest's own initramfs or `/boot` is the problem — fix it inside the guest (boot its previous kernel, rebuild initramfs there), not on the host.

## Step 3: decide — fix forward or pin back

**Pin the working kernel** while you investigate:
```
proxmox-boot-tool kernel pin <good-version>
proxmox-boot-tool refresh
```
Unpin later with `proxmox-boot-tool kernel unpin`.

**Or remove the bad kernel** once you're running on a good one:
```
apt remove proxmox-kernel-<bad-version>
proxmox-boot-tool refresh
update-grub   # legacy boot installs
```

Don't leave a pin in place forever — you'll miss security updates. Pin, fix, unpin.

## Reading the actual error

Start a failing guest from the CLI, where the error is readable:
```
qm start <vmid>
qm showcmd <vmid>
journalctl -u pve-cluster -u pvedaemon -b
journalctl -b -1          # the boot that failed
```
"Timeout waiting on systemd" and `task error` messages in the GUI hide the real cause; the journal doesn't.

## Avoiding the next one

- **Snapshot or back up the host config** before upgrades (`/etc/pve`, `/etc/network/interfaces`, modprobe files)
- Keep at least **two kernels** installed, and know how to reach the GRUB menu on your hardware
- Check **free space on /boot and the ESP** before upgrading
- On ZFS-root systems, treat kernel upgrades as something to do **with console access available**, not remotely from a café
- Read the Proxmox forum's known-issues thread for the release before upgrading a production node

## FAQ

**Can I just reinstall the kernel?**
Often yes: `apt install --reinstall proxmox-kernel-<version>` then `depmod -a` and a refresh. Do it from a booted older kernel.

**Why did only one VM fail?**
Almost always PCIe passthrough, or storage that didn't come back for that specific disk.

**Is pinning a kernel safe long-term?**
It's safe as a bridge, not as a policy — pinned nodes stop receiving kernel fixes.

**The host won't boot at all, not even the old kernel.**
Boot the Proxmox ISO in rescue mode, import the pool / mount root, then rebuild initramfs and refresh the boot tool from there.
