---
title: "Node-RED: Palette Manager Install Fails"
slug: node-red-palette-install-failed
meta_description: "Installing or updating nodes fails with npm errors, and then every install fails. The package.json left in a broken state, and the Node version rule."
updated: October 2026
cluster: round 14 (tech) — Node-RED forum and GitHub issues
competition: LOW
---

# Node-RED: Palette Manager Install Fails

The important dynamic: **one failed install can break all subsequent installs.** A node that failed to install (or uninstall) leaves an entry in `~/.node-red/package.json`, and npm then tries to resolve it on every later install — so an unrelated node fails with an error about the first one.

That's why "it started failing for everything" is the usual report.

## 1. Clean up package.json

```bash
cd ~/.node-red
cp package.json package.json.bak
cat package.json
```

```json
{
  "name": "node-red-project",
  "dependencies": {
    "node-red-contrib-good": "1.2.3",
    "node-red-contrib-broken": "0.1.0"
  }
}
```

Remove the offending entry, then reinstall cleanly:

```bash
# edit package.json, delete the broken dependency line
rm -rf node_modules package-lock.json
npm install
sudo systemctl restart nodered
```

Deleting `node_modules` and `package-lock.json` is safe — everything is reinstalled from `package.json`. Your **flows are not in there**; they live in `flows.json`, which this does not touch.

Check what's conflicting first:

```bash
cd ~/.node-red && npm list --depth=0 2>&1 | grep -iE 'invalid|unmet|error'
```

## 2. Node.js version

```bash
node --version
npm --version
```

The failure mode is specific: a node's `package.json` declares an `engines` range, and npm refuses to install outside it.

```
npm ERR! notsup Unsupported engine
npm ERR! notsup Required: {"node":">=18.0.0 <21"}
```

Two directions here:

- **Node too old** — upgrade. Node-RED itself has a minimum, and contributed nodes track it.
- **Node too new** — a less-maintained node may cap at an older major. Those will not install on Node 22+, and nothing on your side changes that. Find a maintained alternative, or run Node-RED on the supported major.

On Debian/Ubuntu, use the official Node-RED install script rather than the distribution's Node package, which is usually far behind:

```bash
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
```

## 3. Nodes that need to compile

Some nodes include native code (serialport, sqlite3, canvas). They need build tools present:

```bash
sudo apt install -y build-essential python3 git
```

On a Raspberry Pi, a native build can take many minutes and **appears to hang** — check CPU usage before concluding it's stuck. Prebuilt binaries exist for common Pi/Node combinations; an unusual combination forces a source build.

```bash
cd ~/.node-red
npm install --verbose node-red-node-serialport
```

`--verbose` from a shell is far more informative than the palette manager's dialog, which truncates.

## 4. Package names with special characters

Scoped packages (`@scope/node-red-contrib-x`) and names containing `@` or `/` have had install and uninstall problems in the palette manager. Install them from the command line instead:

```bash
cd ~/.node-red
npm install @scope/node-red-contrib-thing
sudo systemctl restart nodered
```

That is also the general workaround whenever the palette manager misbehaves: **the palette manager is a wrapper around npm in `~/.node-red`.** Anything it can do, you can do there directly, with better error messages.

## 5. Permissions

```bash
ls -ld ~/.node-red ~/.node-red/node_modules
```

The user running Node-RED must own both. The classic break is installing something with `sudo` once, which leaves root-owned directories inside `node_modules`:

```bash
sudo chown -R $USER:$USER ~/.node-red
```

In the Home Assistant add-on the paths differ (`/config/node-red/`) and the add-on manages permissions; install from the palette there, not from a shell, or your changes are lost on add-on update.

## 6. Installed but nodes don't appear

- **Node-RED wasn't restarted.** The palette manager usually handles it; after a manual npm install you must restart.
- **The node failed to load.** The startup log says why:

```bash
journalctl -u nodered -n 80 --no-pager | grep -iE 'error|failed|missing'
```

A node whose dependencies didn't install logs a load failure at startup and is absent from the palette with no other indication.

## What not to do

- **Don't install nodes with `sudo`.** It breaks ownership and the next install.
- **Don't delete `flows.json`** while cleaning up. Back it up; it's your actual work.
- **Don't force a node past its engine range** with `--force`. It installs and then misbehaves at runtime.
- **Don't debug in the palette manager dialog.** Use npm from the shell.

## Prevention

| Habit | Why |
|---|---|
| Keep Node.js on a version Node-RED supports | Most install failures are engine ranges |
| Back up `~/.node-red/flows.json` and `package.json` | Flows are the irreplaceable part |
| Install from the shell when the palette fails | Readable errors |
| Remove nodes you stopped using | Fewer dependencies to break on upgrade |

## FAQ

**Can I move my flows to another machine?**
Copy `flows.json`, `flows_cred.json`, `settings.js` and `package.json`, then `npm install`. The credentials file needs the same `credentialSecret`.

**Does updating Node-RED break nodes?**
Occasionally, on majors. Read the release notes and keep a backup of `~/.node-red`.

**Why is the palette manager empty?**
It fetches the catalogue from the Node-RED site; no internet or a blocked request means an empty list.

**Can I pin node versions?**
Yes — edit `package.json` to exact versions and `npm install`. The palette manager always takes the latest.
