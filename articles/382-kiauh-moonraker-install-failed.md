---
title: "KIAUH: Moonraker Install Fails on Dependencies"
slug: kiauh-moonraker-install-failed
meta_description: "The install aborts parsing dependencies, or virtualenv isn't found. The system-dependencies.json syntax change and the clean-image gaps."
updated: October 2026
cluster: round 14 (tech) — dw-0/kiauh GitHub issues
competition: LOW
---

# KIAUH: Moonraker Install Fails on Dependencies

Two distinct failures, both from the same root: KIAUH installs Moonraker's dependencies by parsing a file Moonraker ships, and the format of that file has changed.

## 1. "Error parsing moonraker dependencies"

Moonraker moved to a **conditional dependency syntax** in `scripts/system-dependencies.json`:

```json
{
  "debian": [
    "python3-virtualenv",
    "wireless-tools;distro_id!='ubuntu'",
    "libcurl4-openssl-dev"
  ]
}
```

Older KIAUH passes the whole string — `wireless-tools;distro_id!='ubuntu'` — to `apt install` as a package name, which fails:

```
E: Unable to locate package wireless-tools;distro_id!='ubuntu'
```

Fixes, in order of preference:

```bash
cd ~/kiauh && git pull
```

The parsing fix landed upstream; updating KIAUH is the correct answer. If you're on a fork or an air-gapped machine, install the dependencies by hand and then let KIAUH continue:

```bash
sudo apt update
sudo apt install -y python3-virtualenv python3-dev libopenjp2-7 \
  libsodium-dev zlib1g-dev libjpeg-dev packagekit wireless-tools curl \
  libcurl4-openssl-dev libssl-dev liblmdb-dev libsodium-dev
```

Then re-run KIAUH's Moonraker install — it skips what's already present.

Some people resolve it by using **KIAUH v5** instead of v6. That works, and it also means you're on an older installer; prefer updating v6.

## 2. "virtualenv: command not found"

On a clean **Raspberry Pi OS Lite** image, `virtualenv` isn't present, and KIAUH's dependency step may not install it before trying to create Moonraker's environment. The install appears to succeed and Moonraker won't start, because `~/moonraker-env` was never created.

```bash
ls -la ~/moonraker-env/bin/python
```

If that's missing:

```bash
sudo apt install -y virtualenv python3-virtualenv
# then, in KIAUH: remove Moonraker, install Moonraker
```

The remove-then-reinstall matters. A half-created environment confuses the next install attempt; KIAUH's own remove option cleans it up.

## 3. Python dependency conflicts

```
ERROR: Cannot install moonraker ... MarkupSafe ...
```

The virtual environment picked up a system package version that conflicts. The clean fix is to rebuild the environment rather than force versions:

```bash
rm -rf ~/moonraker-env
cd ~/moonraker
virtualenv -p python3 ~/moonraker-env
~/moonraker-env/bin/pip install -r scripts/moonraker-requirements.txt
sudo systemctl restart moonraker
```

Pay attention to the Python version: Moonraker has minimum requirements, and a very old distribution (Debian Buster-era images) may simply be too old. `python3 --version` — if you're below Moonraker's minimum, a fresh OS image is less work than backporting Python.

## 4. Installed but Moonraker won't come up

Different problem from the install. Read its own log, not KIAUH's:

```bash
tail -n 60 ~/printer_data/logs/moonraker.log
sudo systemctl status moonraker
```

Common entries:

- **`Unable to open database`** — LMDB permissions or a full disk. `df -h` and check ownership of `~/printer_data/database`.
- **`Invalid config`** naming a section — a `moonraker.conf` option that moved or was removed. Moonraker is strict; the log names the line.
- **Klipper socket missing** — `klippy_uds_address` must match where Klipper puts its socket:

```ini
[server]
host: 0.0.0.0
port: 7125
klippy_uds_address: ~/printer_data/comms/klippy.sock
```

- **`[authorization]` missing or too narrow** — Fluidd and Mainsail then can't connect, which reads as a broken install:

```ini
[authorization]
trusted_clients:
    127.0.0.1
    192.168.1.0/24
cors_domains:
    *://localhost
    *://*.local
    *://my.mainsail.xyz
    *://app.fluidd.xyz
```

## 5. Paths: the data-directory migration

Moonraker moved from `~/klipper_config` to `~/printer_data/`. A mix of old and new paths — an old KIAUH installing into the new layout, or a config file that still references `~/klipper_config` — produces "file not found" errors everywhere.

```bash
ls -la ~/printer_data/
# config  database  logs  comms  gcodes  systemd
```

If you have both directories, consolidate into `printer_data` and update any absolute paths in `printer.cfg` and `moonraker.conf`.

## What not to do

- **Don't pip-install into the system Python** to work around the venv. Everything else on the Pi depends on it.
- **Don't install Klipper and Moonraker from mixed sources** (KIAUH plus a vendor script plus manual). Pick one installer.
- **Don't edit `system-dependencies.json`** to get past the parse error. Update KIAUH.
- **Don't run a Creality/vendor Klipper image and then KIAUH.** Those builds don't use virtualenvs and KIAUH's assumptions don't hold.

## Prevention

| Habit | Why |
|---|---|
| `git pull` in `~/kiauh` before any install | Dependency-format changes land upstream first |
| Fresh Raspberry Pi OS Lite (current release) | Old images lack Python and virtualenv prerequisites |
| One installer, recorded in your notes | Mixed installs are the hardest to unpick |
| Back up `~/printer_data` | Config, macros and database in one place |

## FAQ

**KIAUH or the vendor's script?**
KIAUH for a Pi you control. Vendor images on printers with custom hardware, where their fork matters.

**Can I install on Ubuntu?**
Yes; the conditional dependencies exist precisely because package names differ.

**Moonraker updates itself?**
Through its update manager, if configured. KIAUH is for install and major surgery.

**Fluidd works, Mainsail doesn't (or vice versa).**
`cors_domains` — each frontend's hosted domain must be listed if you use the hosted version.
