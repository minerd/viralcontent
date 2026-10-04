---
title: "Scrutiny Showing No SMART Data for Your Drives"
slug: scrutiny-no-smart-data
meta_description: "Drives are listed but show No Data, or don't appear at all. It is almost always smartctl's device-type detection, not Scrutiny."
updated: October 2026
cluster: round 14 (tech) — AnalogJ/scrutiny GitHub issues
competition: LOW
---

# Scrutiny Showing No SMART Data for Your Drives

Scrutiny does not read SMART itself. It runs **`smartctl --scan`** to find devices and then `smartctl -a` on each. So every "no data" problem is a smartctl problem, and you can prove it in one command.

```bash
docker exec scrutiny smartctl --scan
docker exec scrutiny smartctl -a /dev/sda
```

If smartctl in the container can't read the drive, Scrutiny cannot either, and nothing in Scrutiny's config helps.

## 1. The container needs raw device access

```yaml
services:
  scrutiny:
    image: ghcr.io/analogj/scrutiny:master-omnibus
    cap_add:
      - SYS_RAWIO
      - SYS_ADMIN
    devices:
      - /dev/sda:/dev/sda
      - /dev/sdb:/dev/sdb
      - /dev/nvme0:/dev/nvme0
    volumes:
      - /run/udev:/run/udev:ro
      - ./config:/opt/scrutiny/config
      - ./influxdb:/opt/scrutiny/influxdb
```

Three things people omit:

- **`SYS_RAWIO`** — without it, ATA pass-through fails and you get permission errors in the collector log.
- **`/run/udev:ro`** — Scrutiny uses it to get device names and models. Without it drives appear with ugly identifiers or not at all.
- **NVMe needs `SYS_ADMIN`** as well as the device node, and the node is `/dev/nvme0` (the controller), not only `/dev/nvme0n1`.

Each device must be listed explicitly. `--privileged` works but is a blunt instrument; the capability list above is sufficient.

## 2. Device type not detected

The most common real cause. `smartctl --scan` guesses the device type and guesses wrong behind RAID controllers, USB bridges and some SAS expanders. The result is a drive that appears with partial or no attributes.

Find the type that works:

```bash
docker exec scrutiny smartctl -a -d sat /dev/sda          # USB/SATA bridge
docker exec scrutiny smartctl -a -d sat,12 /dev/sda       # some JMicron bridges
docker exec scrutiny smartctl -a -d megaraid,0 /dev/sda   # LSI MegaRAID
docker exec scrutiny smartctl -a -d cciss,0 /dev/sda      # HP Smart Array
docker exec scrutiny smartctl -a -d nvme /dev/nvme0
```

When one of those returns a full attribute table, tell Scrutiny to use it:

```yaml
# config/scrutiny.yaml
devices:
  - device: /dev/sda
    type: 'sat'
  - device: /dev/sda
    type:
      - 'megaraid,0'
      - 'megaraid,1'
```

This overrides the detected type and is the documented mechanism — it exists precisely because `--scan` isn't reliable on every controller.

## 3. USB enclosures

Many USB-SATA bridges do not pass SMART commands at all. `-d sat` fixes the ones that do; for the rest, there is no software solution. Known-bad chipsets simply don't forward ATA pass-through, and the drive will never report through that enclosure.

Test by connecting the drive directly to SATA. If it reports there and not in the enclosure, that's your answer.

## 4. External / split collector setups

If you run the collector separately from the web UI:

```yaml
  collector:
    image: ghcr.io/analogj/scrutiny:master-collector
    environment:
      COLLECTOR_API_ENDPOINT: http://scrutiny-web:8080
    cap_add: [SYS_RAWIO, SYS_ADMIN]
    devices: [...]
    volumes:
      - /run/udev:/run/udev:ro
```

The reported failure mode here is drives **registering but showing "No Data"** — the collector found the device and reported no attributes. That's section 2: the collector container has the device but not a working device type.

Check the collector's own output:

```bash
docker logs scrutiny-collector --tail 50
docker exec scrutiny-collector /opt/scrutiny/bin/scrutiny-collector-metrics run --debug
```

Running the collector manually with `--debug` prints the smartctl invocation it used, which is the fastest way to see the wrong `-d` being passed.

## 5. Drives take a few minutes to appear

The collector runs on a schedule (every 15 minutes by default). After a fresh start, an empty dashboard for a few minutes is normal. Force a run with the command above rather than waiting.

## What not to do

- **Don't run with `--privileged` and stop there.** It masks which capability was actually missing, and it's an unnecessary grant on a host with disks.
- **Don't trust a partial attribute table.** A drive showing only temperature usually means the wrong device type, not a drive with few attributes.
- **Don't spin down drives aggressively and expect SMART polling to be free.** Each poll can wake a sleeping disk. Use `-n standby` behaviour where your setup supports it.
- **Don't treat Scrutiny as a backup for smartd.** Scrutiny visualises; `smartd` is what emails you at 3am.

## Prevention

| Habit | Why |
|---|---|
| Explicit device list and types in `scrutiny.yaml` | Survives controller and enclosure quirks |
| `/run/udev` mounted read-only | Proper model names and serials |
| Run smartd alongside, with alerts | Scrutiny's dashboard is not a notification system |
| Record the working `-d` type per drive | Needed again after every rebuild |

## FAQ

**Does it work behind hardware RAID?**
With `-d megaraid,N` / `cciss,N` per physical drive, yes — one entry per disk behind the controller.

**NVMe shows fewer attributes than SATA.**
Expected; NVMe exposes a different, smaller health log.

**What does the failure prediction mean?**
Scrutiny overlays Backblaze failure-rate data on your attributes. It's a heuristic, not a prophecy — act on reallocated and pending sector counts first.

**Can I run it without InfluxDB?**
No; the omnibus image bundles it. History lives there, so back that volume up.
