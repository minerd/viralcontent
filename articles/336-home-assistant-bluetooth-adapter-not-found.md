---
title: "Home Assistant: Bluetooth Adapter Not Found"
slug: home-assistant-bluetooth-adapter-not-found
meta_description: "The Bluetooth integration can't find an adapter, or finds it and sees no devices. Container access to DBus, Proxmox passthrough, and the USB 3 interference problem."
updated: October 2026
cluster: round 13 (tech) — HA community, core GitHub, Proxmox forum
competition: LOW
---

# Home Assistant: Bluetooth Adapter Not Found

Two different failures:

- **The integration won't set up / no adapter listed** — HA has no access to the hardware
- **The adapter is there but discovers nothing** — range, interference, or the adapter is busy

## 1. Which install type are you running?

This determines everything, and most advice online is written for one and applied to another.

**HA OS (Home Assistant Operating System)** — Bluetooth works out of the box with a supported adapter. If no adapter appears, it's hardware: the dongle isn't supported, isn't seated, or isn't passed through to the VM.

**HA Supervised / Container (Docker)** — the container needs DBus and the adapter:

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    network_mode: host
    privileged: true
    volumes:
      - /run/dbus:/run/dbus:ro
      - ./config:/config
```

`/run/dbus` is the one people miss. HA talks to BlueZ over DBus, not to the device node directly. Without that mount there is no adapter, however the USB device is mapped. `network_mode: host` is also required for Bluetooth to work properly.

**HA Core in a venv** — the user running HA must be in the `bluetooth` group, and BlueZ must be installed and running:

```bash
systemctl status bluetooth
bluetoothctl list
```

## 2. Prove the host can see it

Before anything in HA:

```bash
bluetoothctl list
# Controller AA:BB:CC:DD:EE:FF hci0 [default]

sudo hciconfig -a
lsusb | grep -i blue
dmesg | grep -i blue | tail
```

No controller at host level means HA cannot have one. Then:

- **Firmware missing.** Many adapters need firmware blobs. `dmesg` says so plainly:

```
Bluetooth: hci0: Direct firmware load for intel/ibt-20-1-3.sfi failed
```

Install your distribution's firmware package (`linux-firmware`, `firmware-realtek`, etc.) and reboot.

- **Adapter soft-blocked.**

```bash
rfkill list
rfkill unblock bluetooth
```

- **Built-in Pi adapter disabled.** Check `/boot/firmware/config.txt` for `dtoverlay=disable-bt`, which some guides add to free the UART for Zigbee.

## 3. Virtualised installs (Proxmox, ESXi, Hyper-V)

A USB Bluetooth adapter must be passed through as a **USB device**, and there are two reliable gotchas:

- **Pass through by vendor:product ID, not by port**, so a reboot or a replug doesn't change it. In Proxmox:

```
qm set 100 -usb0 host=0a12:0001
```

- **USB 2 port, not USB 3.** This is not superstition: USB 3 controllers emit broadband noise around 2.4 GHz, and a Bluetooth or Zigbee dongle in or next to a USB 3 port has dramatically reduced range. Use a USB 2 port, and where possible a short extension cable to get the dongle away from the chassis. If your adapter "works but only within 1 metre", this is almost certainly why.

- **Don't pass through the whole USB controller** unless you've checked what else is on it — you can take the host's keyboard with it.

## 4. Adapter present, nothing discovered

- **Something else holds the adapter.** BlueZ gives exclusive access for some operations. A second container (a BLE proxy, an ESPHome tool, `bluetoothctl` left in scan mode) can starve HA. Only one consumer per adapter.
- **Range.** BLE sensors are low-power; through two walls is optimistic. This is what **Bluetooth proxies** exist for: an ESP32 running the ESPHome Bluetooth Proxy forwards advertisements over Wi-Fi, so you can place receivers where the devices are. For a house-wide BLE setup, proxies are the architecture, not a workaround — one adapter at the server will always be the weak link.
- **The device needs pairing, not just discovery.** Some devices (certain locks, thermostats) must be paired, and some only advertise while in pairing mode. A sensor that appears once and then vanishes has usually just stopped advertising on your schedule.
- **Passive vs. active scanning.** HA's Bluetooth integration options include active scanning, which queries devices rather than only listening. Some devices only appear with it on; it uses more airtime, so leave it off unless needed.

## 5. The adapter drops out after hours or days

```bash
dmesg -T | grep -i 'usb\|bluetooth' | tail -30
```

- `usb 1-2: USB disconnect` — power or cable. A powered hub, or a better cable.
- Pi-specific: an underpowered supply drops USB devices under load.
- Some adapters have firmware bugs that need a reset; `hciconfig hci0 reset` recovers them, and if you need that regularly, replace the adapter.

## What not to do

- **Don't put the dongle directly in a USB 3 port** next to an SSD. It's the most common cause of "poor range" on a mini PC.
- **Don't run two integrations against one adapter.** Pick one consumer.
- **Don't use `privileged: true` as a first resort** if you can mount `/run/dbus` and the device explicitly — but note that for Bluetooth specifically, privileged plus host networking is what reliably works in Docker.
- **Don't expect a single adapter to cover a house.** Add ESPHome Bluetooth proxies.

## Prevention

| Habit | Why |
|---|---|
| USB 2 port, on an extension cable, away from the case | The biggest single improvement to range |
| ESPHome Bluetooth proxies in each area | Turns coverage from a hardware limit into a solved problem |
| Pass through by vendor:product in VMs | Survives reboots and replugs |
| One consumer per adapter | Removes the contention class |

## FAQ

**Which adapters work best?**
Those with well-supported chipsets and external antennas. An integrated Pi adapter works but has the worst range of any option.

**Can I use Bluetooth and Zigbee dongles side by side?**
Only with physical separation — both are 2.4 GHz and adjacent dongles interfere badly. Extension cables, and different Zigbee/Wi-Fi channels.

**Does the ESPHome proxy replace the adapter entirely?**
Largely yes for passive sensors. Active connections (locks, some thermostats) are supported by proxies in recent versions too.

**Devices show as unavailable intermittently.**
Normal for battery BLE sensors with long advertising intervals. Raise the integration's unavailability timeout rather than chasing the adapter.
