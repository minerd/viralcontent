---
title: "OrcaSlicer: Network Plugin Missing or Won't Install"
slug: orcaslicer-network-plugin-missing
meta_description: "'Network plugin not detected' blocks device control and cloud login. Where the plugin actually goes, why the download fails, and the offline install."
updated: October 2026
cluster: round 13 (tech) — OrcaSlicer GitHub issues
competition: LOW
---

# OrcaSlicer: Network Plugin Missing or Won't Install

The network plugin is a separate binary OrcaSlicer downloads after installation. It's needed for Bambu device control and cloud login — **not** for printing to Klipper, Prusa or OctoPrint over their own APIs. Knowing which camp you're in saves the whole exercise.

## 1. Do you actually need it?

| You print to | Plugin needed? |
|---|---|
| Bambu Lab printer (LAN or cloud mode) | Yes |
| Klipper via Moonraker/Fluidd/Mainsail | **No** |
| OctoPrint | **No** |
| PrusaLink / PrusaConnect | **No** |
| SD card / USB | No |

If you're on Klipper and seeing the plugin warning, you can ignore it. The Device tab won't work, but **Print → Send to printer** via the physical printer's host settings does. Many people chase this for days without needing it.

## 2. The normal install path

**Help → Install network plugin** (or the prompt on first launch). OrcaSlicer fetches the plugin from GitHub releases and places it in its data directory.

Where it goes:

| OS | Path |
|---|---|
| Windows | `%APPDATA%\OrcaSlicer\plugins\` |
| macOS | `~/Library/Application Support/OrcaSlicer/plugins/` |
| Linux (AppImage/native) | `~/.config/OrcaSlicer/plugins/` |
| Linux (Flatpak) | `~/.var/app/io.github.softfever.OrcaSlicer/config/OrcaSlicer/plugins/` |

The filename is `plugins/bambu_networking.so` (Linux), `.dll` (Windows) or `.dylib` (macOS). Check whether it's there before concluding the install failed:

```bash
ls -l ~/.config/OrcaSlicer/plugins/
```

A file present and the warning still showing means a **version mismatch**, not a missing file — see section 4.

## 3. When the download fails

The in-app download reaches GitHub. It fails for mundane reasons:

- **No internet in the sandbox.** Flatpak and Snap builds may lack network permission for this path. For Flatpak:

```bash
flatpak override --user --share=network io.github.softfever.OrcaSlicer
```

- **Corporate proxy / DNS filtering.** The plugin URL is on `github.com` and its CDN; a blocked CDN gives a silent failure.
- **Write permission.** An OrcaSlicer installed system-wide but run as a user may be unable to write its plugin directory. The AppImage run from a read-only mount is the common case.

**Offline install:** download the plugin asset from the OrcaSlicer GitHub release matching your version, and drop it into the `plugins/` path above by hand. This works and is the reliable fallback. The asset is named for the platform; make sure you take the one for your OS *and* architecture (an x86_64 plugin in an ARM build fails to load with no message).

## 4. Installed but still "not detected"

Three causes:

- **Version mismatch.** The plugin is built against a specific OrcaSlicer version. Upgrading OrcaSlicer without re-running the plugin install leaves the old plugin in place, which won't load. Re-install the plugin after every OrcaSlicer update — this is the single most common recurrence.
- **Missing system libraries** (Linux). The plugin is a shared object with dependencies:

```bash
ldd ~/.config/OrcaSlicer/plugins/libbambu_networking.so | grep 'not found'
```

Anything reported as not found needs installing. `libwebkit2gtk` and `libsoup` are the usual suspects on newer distributions where the version the plugin wants has been superseded.

- **Wrong data directory.** If you've ever launched with a custom `--datadir`, the plugin went to one directory and OrcaSlicer is now looking in another. Launch without the flag, or put the plugin in the directory actually in use (Help → Show Configuration Folder tells you which).

## 5. LAN-only mode as an alternative

For a Bambu printer where you don't want cloud at all: enable **LAN Only Mode** on the printer, then in OrcaSlicer add the device by IP with its access code. This path still uses the plugin for device control, but it removes the cloud login — which is where a good share of plugin-related login failures actually come from (expired tokens, region mismatch between the account and the slicer).

If cloud login fails with the plugin present, check the account **region**. An account created in one region and a slicer set to another fails to authenticate in a way that reads as a plugin fault.

## What not to do

- **Don't reinstall OrcaSlicer to fix the plugin.** It won't touch the plugin directory, which is where the stale file is.
- **Don't copy a plugin from a different OrcaSlicer version.** That's the mismatch case, created deliberately.
- **Don't delete the whole config folder.** You lose every printer profile, filament profile and process preset. Delete only `plugins/`.
- **Don't chase this at all if you print to Klipper.** The warning is cosmetic for you.

## Prevention

| Habit | Why |
|---|---|
| Re-run "Install network plugin" after every update | Removes the dominant recurrence |
| Keep the offline plugin asset alongside your installer | Makes an offline or firewalled install trivial |
| Export your profiles before any config-folder surgery | Profiles are the valuable, hard-to-replace part |
| Use LAN Only Mode if you don't need cloud | Fewer moving parts, fewer auth failures |

## FAQ

**Is the plugin open source?**
No — it's a closed binary from Bambu, which is why it's distributed separately from OrcaSlicer itself.

**Can I control a Bambu printer without it?**
You can send jobs via SD card or, with LAN mode, via third-party tools. Full device control in the slicer needs it.

**It installs, then disappears after a restart.**
Write permissions on the config directory, or a sandbox that resets it. Check ownership of the `plugins/` folder.

**Does Bambu Studio have the same problem?**
Bambu Studio ships the plugin in its installer, so no. That difference is why guides for one don't help with the other.
