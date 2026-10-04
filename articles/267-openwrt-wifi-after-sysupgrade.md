---
title: "OpenWrt Wi-Fi Dead After a Sysupgrade? Radios Disabled, Firmware, or a Stale MAC Line"
slug: openwrt-wifi-after-sysupgrade
meta_description: "No wireless after flashing a new OpenWrt release. Radios disabled by default, missing firmware packages, stale MAC entries in /etc/config/wireless and how to recover."
updated: October 2026
cluster: round 12 (tech) — OpenWrt forum and GitHub issues only
competition: LOW
---

# OpenWrt Wi-Fi Dead After a Sysupgrade? Radios Disabled, Firmware, or a Stale MAC Line

You flash a new release, the router boots, LAN works over Ethernet — and there's no Wi-Fi. Four causes, in the order to check them.

## 1. The radios are simply disabled

OpenWrt ships wireless **disabled by default**, and depending on how config was carried over you can land in that state.

```sh
uci show wireless | grep disabled
# enable both radios
uci set wireless.radio0.disabled='0'
uci set wireless.radio1.disabled='0'
uci commit wireless
wifi reload
```

In LuCI: **Network → Wireless** → each radio → **Enable**.

If the **Wireless menu is missing entirely** in LuCI, that's cause 2.

## 2. Missing firmware/driver packages

A custom image (from the firmware selector, an attended sysupgrade, or your own build) can come without the **kmod driver and firmware** for your radio. Then there is no `radio0` to configure:

```sh
ls /sys/class/ieee80211/         # any phy present?
logread | grep -i -e firmware -e mt76 -e ath1 -e wlan
opkg update
opkg install kmod-mt7915-firmware   # example: use YOUR chipset's package
```

Common ones: `kmod-mt76*`, `kmod-ath9k`, `kmod-ath10k-ct` + `ath10k-firmware-*`, `kmod-ath11k`, plus `wpad`/`wpad-openssl` for WPA support.

A missing **`wpad`/`hostapd`** variant is its own trap: the radio exists but no encrypted SSID can come up. The minimal `wpad-mini`/`wpad-basic` builds don't support WPA3.

## 3. First boot is slow and Wi-Fi gives up

Reported behaviour: on some devices the **firmware is extracted from flash on first boot**, and that is slow enough that wireless initialisation fails before the firmware is ready.

Fix: **reboot again**. Genuinely. If Wi-Fi works on the second boot, this was it, and nothing is wrong.

## 4. A stale MAC line in /etc/config/wireless

Also reported: after a sysupgrade, `macaddr` lines in `/etc/config/wireless` reappear or no longer match the hardware, and Wi-Fi won't come up until they're **removed**.

```sh
cat /etc/config/wireless
uci delete wireless.radio0.macaddr
uci commit wireless
wifi reload
```

The cleanest version of this fix is to regenerate the file from scratch:

```sh
rm /etc/config/wireless
wifi config          # detect radios and write a fresh default config
# then re-add your SSIDs
```

That is also the right move when a config carried over from an old release has keys the new one doesn't understand.

## 5. Decide between keeping and dropping settings

- **Keep settings** on a minor upgrade within the same release branch
- **Drop settings** (`sysupgrade -n`, or untick "keep settings") when crossing major versions — 21.x → 22.x → 23.x → 24.x have all moved things, and carried-over config is the most common cause of a broken upgrade
- Either way: **export the config first** (System → Backup / `sysupgrade -b`), so re-entering settings is a ten-minute job

## 6. Recovery when you're locked out

- Ethernet to a LAN port, `192.168.1.1`
- **Failsafe mode**: power on and press the reset button when the LED flashes, then `telnet 192.168.1.1` / `ssh root@192.168.1.1`, `mount_root`, fix or `firstboot`
- Restore from your **pre-upgrade backup**
- TFTP recovery for a device that won't boot — model-specific, check the device page on the wiki

## Prevention

1. **Back up the config** before every sysupgrade (`sysupgrade -b /tmp/backup.tar.gz`, copied off the device)
2. Read your **device page** on the OpenWrt wiki for the target release
3. Use the **firmware selector / attended sysupgrade** so your installed packages come along
4. **Drop settings** across major versions and re-enter them
5. Upgrade with **physical access** and an Ethernet cable in hand

## FAQ

**Why is Wi-Fi disabled by default?**
It's OpenWrt's deliberate out-of-the-box state. Enable the radios after a fresh install.

**The Wireless menu is missing in LuCI.**
No radio is detected — missing kmod/firmware packages for your chipset.

**Should I keep settings when upgrading?**
Within a branch, yes. Across major versions, no.

**Wi-Fi came back on the second reboot. Is something wrong?**
Probably just slow first-boot firmware extraction. Keep an eye on it, but that's a known pattern.
