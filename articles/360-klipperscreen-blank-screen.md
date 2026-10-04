---
title: "KlipperScreen Blank or Not Starting"
slug: klipperscreen-blank-screen
meta_description: "The service says running and the display shows nothing. Xorg permissions, HDMI force-enable, screen blanking and the boot loop."
updated: October 2026
cluster: round 14 (tech) — Klipper Discourse and KlipperScreen GitHub
competition: LOW
---

# KlipperScreen Blank or Not Starting

Three different failures look the same from the front:

- **Service running, display black from boot** → Xorg or HDMI (sections 1–2)
- **Worked, went black after a print finished** → screen blanking (section 3)
- **Continuously restarting** → config or Moonraker (section 4)

```bash
sudo systemctl status KlipperScreen
tail -n 60 ~/printer_data/logs/KlipperScreen.log
```

## 1. Xorg isn't there, or can't start

KlipperScreen needs a graphical stack. On **Raspberry Pi OS Lite** there is no Xorg by default, and the install script's dependency step may fail quietly on some images.

```bash
which Xorg xinit
ls -l /usr/share/X11/xorg.conf.d/
```

If Xorg is missing:

```bash
sudo apt update
sudo apt install --no-install-recommends xserver-xorg xinit x11-xserver-utils
```

Permission errors are the other half of this. Starting X as a non-root user needs the right configuration:

```bash
sudo dpkg-reconfigure xserver-xorg-legacy
# choose "Anybody"
```

or create `/etc/X11/Xwrapper.config`:

```
allowed_users=anybody
needs_root_rights=yes
```

The log line to look for is `(EE) Cannot open virtual console` or a permission denial on `/dev/tty0`.

## 2. HDMI not enabled

A Pi with no display attached at boot disables the HDMI output, and attaching the screen later gives you nothing. Force it on:

```bash
sudo nano /boot/firmware/cmdline.txt
# append to the single existing line:
 video=HDMI-A-1:e
```

(On older Raspberry Pi OS the file is `/boot/cmdline.txt`.) For DSI and SPI displays the overlay must be right in `config.txt` instead — and a display that works with `fbcp` but not with KlipperScreen usually needs the KMS driver rather than the legacy framebuffer.

```bash
# confirm the kernel sees a display
cat /sys/class/drm/*/status
```

`connected` on one of them is what you want.

## 3. Black after idle or after a print

Power saving. The display turns off and cannot come back:

```bash
xset -display :0 s off
xset -display :0 s noblank
xset -display :0 -dpms
```

Make it persistent — KlipperScreen's own service can run these, or add them to the X startup. In KlipperScreen's config there is also a screen-blanking option that is the supported way:

```ini
# ~/printer_data/config/KlipperScreen.conf
[main]
screen_blanking: off
```

If you *want* blanking but want it to recover, the DPMS route (`-dpms` off, `screen_blanking` handled by KlipperScreen) is more reliable than letting X manage it.

## 4. Boot loop

```bash
journalctl -u KlipperScreen -n 80 --no-pager
```

Causes:

- **Invalid `KlipperScreen.conf`.** A bad `[printer]` section or a malformed macro reference crashes it on start. Move the config aside and let it use defaults to confirm:

```bash
mv ~/printer_data/config/KlipperScreen.conf ~/KlipperScreen.conf.bak
sudo systemctl restart KlipperScreen
```

- **Can't reach Moonraker.** KlipperScreen talks to Moonraker over HTTP and websocket. It must be listed in Moonraker's trusted clients:

```ini
# moonraker.conf
[authorization]
trusted_clients:
    127.0.0.1
    192.168.1.0/24
cors_domains:
    *://localhost
    *://*.local
```

- **A corrupt saved-variables or uploaded-files state.** Clearing `saved_variables.cfg` and old uploads has resolved continuous-boot cases; back them up first.
- **Missing Python dependencies after a system upgrade.** Re-run the install script's dependency step rather than pip-installing by hand.

## 5. Touch works but is offset or inverted

Separate, and purely a calibration matter:

```ini
[main]
# rotate the display
rotate: 180
```

For resistive touch panels the X input transformation matrix is the tool:

```bash
xinput list
xinput set-prop <id> 'Coordinate Transformation Matrix' 0 1 0 -1 0 1 0 0 1
```

Get it right interactively, then persist it in an Xorg config snippet.

## What not to do

- **Don't reflash the SD card as a first move.** Almost all of these are two-line fixes.
- **Don't run KlipperScreen as root to fix permissions.** Configure Xwrapper instead.
- **Don't install a full desktop environment.** It costs CPU that Klipper needs, and brings its own display manager to fight with.
- **Don't leave X's DPMS on with a display that can't wake.** It will go black mid-print.

## Prevention

| Habit | Why |
|---|---|
| `video=HDMI-A-1:e` on any Pi with a detachable screen | Survives booting without the display |
| `screen_blanking: off` while you're still validating | Removes the hardest-to-attribute failure |
| Moonraker trusted_clients set to your subnet | Prevents the boot loop on every reinstall |
| Back up `KlipperScreen.conf` | It's the first thing to bisect |

## FAQ

**Can I run it on a separate Pi from Klipper?**
Yes — point it at the printer's Moonraker over the network.

**Fluidd/Mainsail work, KlipperScreen doesn't.**
Then Moonraker is fine and it's the local display stack: sections 1–2.

**Does it work on Wayland?**
Support varies by version; X11 is the well-trodden path.

**Screen is upside down after an update.**
`rotate:` in the config, or the display overlay changed. Set it explicitly rather than relying on autodetection.
