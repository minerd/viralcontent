---
title: "Jellyfin Intel Quick Sync Stopped Working After an Update? Driver, Kernel or Device"
slug: jellyfin-qsv-broke-after-update
meta_description: "QSV transcoding that worked for months fails after a host update. The non-free VA driver, Proxmox LXC passthrough, compute runtime and how to test outside Jellyfin."
updated: October 2026
cluster: round 11 (tech) — Jellyfin forum, GitHub and Proxmox threads; setup guides answer a different question
competition: LOW
---

# Jellyfin Intel Quick Sync Stopped Working After an Update? Driver, Kernel or Device

Hardware transcoding worked for months. You updated the host — kernel, distro, Proxmox, or the container image — and now playback either falls back to CPU or fails outright with *"No device available for decoder"* or `libva info: va_openDriver() failed`.

The setup guides you'll find all answer **"how do I set up QSV"**. This is the other question: **it was working, what did the update break?**

## Step 1: test outside Jellyfin

Prove whether the GPU is available at all before touching Jellyfin's settings.

**Inside the Jellyfin container:**
```bash
ls -l /dev/dri/                 # renderD128 present?
vainfo                          # profiles listed?
vainfo | grep -i -e hevc -e h264
```

What the answers mean:
- **`/dev/dri` missing** → device passthrough broke (step 2)
- **`vainfo` fails with `va_openDriver() failed`** → the VA driver is missing or wrong (step 3)
- **`vainfo` works but no HEVC/AV1 encode entries** → you're on the wrong driver package (step 3)
- **Everything looks right** → Jellyfin settings or the specific file (step 5)

On the host, `ls -l /dev/dri` and `vainfo` tell you whether the problem is host-side or container-side. Fix host first.

## Step 2: device passthrough after an update

**Docker:** the device and group must still be passed:
```yaml
devices:
  - /dev/dri:/dev/dri
group_add:
  - "989"        # the host's 'render' group GID — check it, it changes between distros
```
Get the real GID: `getent group render`. A distro upgrade that renumbers `render` silently removes access while the device node is still visible.

**Proxmox LXC:** an unprivileged container needs the device plus the right cgroup/idmap entries, and **kernel updates have broken QSV in LXC before**. Check your container config still has the `dev0`/`lxc.mount.entry` lines for `/dev/dri` and that the GIDs inside match the host.

**VM:** passthrough of an iGPU is fragile; a kernel update changing IOMMU grouping will break it. Check `dmesg | grep -i -e vfio -e iommu`.

## Step 3: the VA driver (the most common real cause)

Two traps:

**1. The non-free package.** On Debian 12 / Ubuntu 24.04, the default `intel-media-va-driver` does **not** include HEVC encode. You need **`intel-media-va-driver-non-free`**. A distro upgrade that replaced the non-free package with the stock one removes HEVC transcoding — which is exactly "it worked, now it doesn't".

```bash
apt install intel-media-va-driver-non-free intel-opencl-icd
# plus firmware: linux-firmware / firmware-misc-nonfree
```

**2. The right driver for your generation.** `iHD` (intel-media-driver) for Gen8+; the older `i965` for much older chips. Force it if detection is wrong:
```bash
export LIBVA_DRIVER_NAME=iHD
```

Also: **firmware**. Missing GuC/HuC firmware produces a device that appears but can't encode. `dmesg | grep -i -e i915 -e guc -e huc` shows firmware load failures plainly.

**Newer Arc / Xe hardware** additionally wants a current **compute runtime**; Proxmox users on newer kernels have specifically had to install the latest release to get QSV back.

## Step 4: kernel and i915

```bash
dmesg | grep -i i915 | head -30
```

Look for the driver failing to bind, firmware errors, or the GPU being claimed by something else. A kernel upgrade can:
- Change the **i915 module parameters** needed on your generation
- Enable **`xe`** (the newer driver) on hardware that worked under `i915`, or vice versa
- Lose a `GRUB_CMDLINE_LINUX` option you'd added (`i915.enable_guc=2`)

Pin the previous kernel and boot it as a test. If QSV comes back, you've localised it with no guesswork — then fix forward with the driver/firmware packages.

## Step 5: Jellyfin-side settings

Only once `vainfo` is healthy:

- **Dashboard → Playback → Hardware acceleration**: `Intel QuickSync (QSV)`, and the **device path** (`/dev/dri/renderD128`)
- Enable only the **codecs your hardware actually supports** — enabling AV1 encode on hardware that can't do it causes failures that look like a broken setup
- **Enable hardware decoding** for the formats you have; leave exotic ones off
- Check the **transcode log** for the failing item (Dashboard → Logs): the FFmpeg command line and its error are there, and that tells you whether it's decode, filter or encode failing
- Keep **low-power encoding** off unless you know your chip wants it

## Step 6: container image changes

If you updated the **Jellyfin image**:
- The image may have changed base distro, and with it the VA driver packages inside
- `jellyfin/jellyfin` vs linuxserver's image handle drivers differently — don't follow instructions for the other one
- Pin the image tag and test an upgrade deliberately rather than letting it land at 3am

## Fast triage

| Symptom | Where to look |
|---|---|
| `/dev/dri` missing in container | Passthrough / LXC config / `render` GID |
| `va_openDriver() failed` | VA driver package not installed |
| vainfo works, no HEVC encode | Need `intel-media-va-driver-non-free` |
| Works on host, fails in container | GID or device mapping |
| Worked on old kernel only | i915/xe or firmware — pin the kernel, then fix packages |
| Only some files fail | Codec support (AV1/HEVC 10-bit) or tone mapping, not QSV itself |

## FAQ

**Why would a distro upgrade break HEVC specifically?**
Because HEVC encode lives in the non-free VA driver package, and upgrades can replace it with the stock one.

**Does Jellyfin need the GPU for tone mapping too?**
Yes — HDR→SDR tone mapping requires hardware acceleration, so a broken QSV setup breaks tone mapping as well.

**Is `vainfo` enough to prove it works?**
It proves the driver and device are fine. The rest is Jellyfin configuration and codec support.

**Should I use `i915` or `xe`?**
Whichever your kernel binds for your generation. Don't force it unless `dmesg` shows the wrong one being used.
