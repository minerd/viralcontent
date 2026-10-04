---
title: "Frigate: One of Several Coral TPUs Not Detected"
slug: frigate-multiple-coral-tpu-not-detected
meta_description: "Two PCIe Corals and only one /dev/apex device, or a dual TPU that crashes after detection. The gasket driver, UEFI, and the dual-TPU lane problem."
updated: October 2026
cluster: round 14 (tech) — blakeblackshear/frigate GitHub issues
competition: LOW
---

# Frigate: One of Several Coral TPUs Not Detected

Single-Coral setups are well covered. The multi-TPU case has its own failure modes, and most of them are below Frigate — at the driver, the BIOS, or the physical lanes.

Start at the bottom:

```bash
# on the Docker host, not in the container
lspci | grep -i 'coral\|global unichip'
ls -l /dev/apex_*
dmesg | grep -i 'apex\|gasket' | tail -20
```

| What you see | Where the problem is |
|---|---|
| No `lspci` entry | Physical / BIOS — section 3 |
| `lspci` entry, no `/dev/apex_N` | Gasket driver — section 1 |
| Fewer `/dev/apex_N` than cards | Section 2 |
| All devices present, Frigate sees one | Config — section 4 |

## 1. The gasket driver

PCIe and M.2 Corals need the out-of-tree `gasket` driver. It is the most common reason for no `/dev/apex_0` at all.

```bash
sudo apt install -y git devscripts dh-dkms dkms
git clone https://github.com/google/gasket-driver.git
cd gasket-driver
sudo debuild -us -uc -tc -b
sudo dpkg -i ../gasket-dkms_*.deb
sudo reboot
```

Points that matter:

- **Rebuild after every kernel update.** DKMS should handle it; verify with `dkms status`. A Coral that stopped working after `apt upgrade` is nearly always this.
- The packaged `gasket-dkms` in older distribution repositories fails to build on recent kernels — build from the upstream repository.
- Group permissions: the device should be readable by the group Docker runs as, or pass it explicitly.

## 2. Two cards, one device node

With a dual Edge TPU M.2 module or two cards in PCIe adapters:

**The dual-TPU module needs two PCIe lanes.** Most consumer M.2 slots — especially the ones wired for NVMe only, and almost all E-key Wi-Fi slots — expose a single lane, so only one of the two TPUs enumerates. This is a hardware limitation of the slot, not a configuration problem. There is no software fix; the card works fully only in a slot that bifurcates or provides two lanes.

So if you have a dual TPU and see exactly one `/dev/apex_0`, check your slot's lane allocation in the board manual before anything else.

**For two separate cards**, each should appear:

```
/dev/apex_0
/dev/apex_1
```

If one is missing, swap the cards between slots. If the same physical card fails in both, it's the card; if the same *slot* fails with both cards, it's the slot or the BIOS.

Also reported: with four TPUs, one consistently undetected — usually power or lane sharing on the adapter board rather than the TPU.

## 3. Virtualisation and firmware

- **Proxmox / ESXi**: pass the device through by PCI ID, and give the VM the whole IOMMU group. Corals frequently share a group with other devices; passing a partial group fails.
- **BIOS → UEFI**: switching the VM's firmware from SeaBIOS to **UEFI (OVMF)** has resolved detection failures. It's a documented fix worth trying early in a VM.
- **Above 4G decoding** enabled in the host BIOS. Without it, PCIe devices needing large BAR allocations fail to initialise.
- **IOMMU enabled** (`intel_iommu=on` / `amd_iommu=on`) for passthrough.

## 4. Frigate configuration

Once the host has both nodes, Frigate needs both declared — one detector per TPU:

```yaml
detectors:
  coral1:
    type: edgetpu
    device: pci:0
  coral2:
    type: edgetpu
    device: pci:1
```

For USB Corals:

```yaml
detectors:
  coral:
    type: edgetpu
    device: usb
```

And the container needs the devices:

```yaml
services:
  frigate:
    devices:
      - /dev/apex_0:/dev/apex_0
      - /dev/apex_1:/dev/apex_1
```

A detector block referencing `pci:1` with no `/dev/apex_1` mapped in makes Frigate fail to start, with a clear message. Two detector blocks pointing at the same device will appear to work and halve your throughput.

## 5. Detected, then crashes

Reported for dual-TPU setups: detection succeeds and Frigate crashes immediately afterwards.

```bash
docker logs frigate --tail 100 | grep -iE 'edgetpu|detector|segfault'
```

Causes seen in practice: insufficient power to the adapter, a riser introducing signal problems, and thermal throttling — Corals get hot and an M.2 card with no airflow will misbehave under sustained load. If it runs for a few minutes and then dies, suspect heat before software.

Test with one detector declared at a time. If each TPU works alone and they fail together, it's power, lanes or heat.

## What not to do

- **Don't buy a dual Edge TPU for a single-lane slot.** You get one TPU's performance and a week of debugging.
- **Don't skip the DKMS check after a kernel upgrade.** It's the most common regression.
- **Don't declare more detectors than devices.** Frigate won't start.
- **Don't run a Coral with no airflow.** Throttling presents as random crashes.

## Prevention

| Habit | Why |
|---|---|
| `dkms status` in your post-upgrade checklist | Catches the kernel-update break |
| One detector per `/dev/apex_N`, verified | Prevents silent halving of throughput |
| Airflow over M.2 Corals | Removes the thermal-crash class |
| Note the slot's lane count before buying | The dual-TPU limitation is physical |

## FAQ

**Do I need two TPUs?**
One handles roughly a dozen cameras at typical detection rates. Count your `detection_fps`, not your cameras.

**USB and PCIe together?**
Supported — declare both detector types.

**Coral vs GPU detection?**
Recent Frigate supports OpenVINO and TensorRT detectors; a modern iGPU is competitive and needs no driver gymnastics. Worth considering before buying more Corals.

**`/dev/apex_0` exists but permission denied in the container.**
Add the device explicitly and check its group ownership; `group_add` with the host's GID is the clean fix.
