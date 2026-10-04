---
title: "OctoPrint Plugin Manager Not Installing Anything? pip, Python 3 and --no-build-isolation"
slug: octoprint-plugin-not-loading
meta_description: "Plugins that install but never appear, an empty plugin list, or 'pip could not be found'. Python 3 compatibility, the build-isolation flag and checking the plugins folder."
updated: October 2026
cluster: round 12 (tech) — OctoPrint community forum and GitHub issues
competition: LOW
---

# OctoPrint Plugin Manager Not Installing Anything? pip, Python 3 and --no-build-isolation

Four distinct failures. Find yours before changing settings.

## 1. "pip could not be found or does not work correctly" / empty plugin list

The Plugin Manager shells out to **pip** inside OctoPrint's virtualenv. If it can't, you get an empty repository list and an error.

```bash
~/oprint/bin/pip --version          # typical OctoPi path
~/oprint/bin/python -V
```

- Wrong or missing path → set it in **Settings → Plugin Manager → pip command**
- A **broken virtualenv** after an OS upgrade (Python minor version changed under it) → recreate the venv, or reinstall OctoPrint and restore your config backup
- On a fresh install, there's a known startup window where this appears before the environment is ready — restart OctoPrint and retry

## 2. The install window opens and installs nothing

Reported fix: set **`--no-build-isolation`** in the Plugin Manager's pip arguments.

Build isolation makes pip create a clean environment to build the package in, which fails on systems without build dependencies (a Pi with no compiler toolchain, or no network access to fetch build requirements). Disabling it lets pip build against what's already installed.

**Settings → Plugin Manager → Advanced options → pip arguments**: add `--no-build-isolation`.

Related: a plugin needing compilation will fail without `python3-dev` and `build-essential` installed on the host.

## 3. The plugin installs but doesn't appear

```bash
ls ~/.octoprint/plugins/
~/oprint/bin/pip list | grep -i octoprint
```

- Nothing there → the install didn't actually complete; read the install log in the dialog, not just the result line
- Present but not listed in OctoPrint → **restart OctoPrint** (a plugin isn't loaded until restart), then check the log at startup for an import error
- An **import error** at startup, often a Python 3 incompatibility, means the plugin loads nowhere. The log names the module

## 4. Python 2 era plugins

Plugins that haven't been updated **in years** don't work with modern OctoPrint on Python 3 — the Python 2 → 3 transition is the dividing line.

- Check the plugin's repository for its last release and Python 3 support
- Look for a maintained fork
- Accept that some old plugins are gone, especially webcam/timelapse helpers
- Check the plugin's declared **compatibility** in the repository entry before installing

## 5. Installing from a URL or file

When the repository is unreachable (DNS, firewall, the plugin not listed):

```bash
~/oprint/bin/pip install https://github.com/user/OctoPrint-Plugin/archive/master.zip
sudo service octoprint restart
```

Use OctoPrint's own pip, not the system one — installing into the system Python puts the plugin somewhere OctoPrint will never look. That mistake accounts for a lot of "it installed but isn't there".

## 6. Disk, network and permissions

- **Disk full** on `/` or `/home` — installs fail halfway and leave a broken package
- DNS/proxy blocking PyPI and the plugin repository: `curl -sI https://pypi.org/simple/`
- Permissions: the OctoPrint user must own its venv and `~/.octoprint`

## Recovering from a bad plugin

A plugin that crashes OctoPrint at startup locks you out of the UI. Start in **safe mode** (which disables all third-party plugins):

```bash
sudo service octoprint stop
~/oprint/bin/octoprint serve --safe
# or uninstall directly
~/oprint/bin/pip uninstall OctoPrint-TheBadOne
sudo service octoprint restart
```

Safe mode is the reason you don't need to reflash an SD card over a plugin.

## Prevention

1. **Back up** (Settings → Backup & Restore) before adding or updating plugins
2. Install **one plugin at a time** and restart between
3. Check **Python 3 compatibility** before installing anything old
4. Keep `--no-build-isolation` noted if your host needs it
5. Know **safe mode** before you need it

## FAQ

**Why does the plugin list come up empty?**
Plugin Manager can't run pip, or can't reach the repository. Check both.

**What does --no-build-isolation actually do?**
It stops pip building in an isolated environment, so installs succeed on hosts without build tooling.

**Can I use any pip?**
No — use OctoPrint's virtualenv pip, or the plugin lands outside OctoPrint.

**A plugin broke OctoPrint. Now what?**
Start in safe mode and uninstall it.
