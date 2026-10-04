---
title: "Node-RED Flows Gone After an Update? Don't Deploy — Find the Flow File"
slug: node-red-flows-missing-after-update
meta_description: "An empty Node-RED canvas after an update usually means it's reading a different flow file or directory. Why you must not deploy, where the backups are, and how to restore."
updated: October 2026
cluster: round 11 (tech) — Node-RED forum, HA community and GitHub issues
competition: LOW
---

# Node-RED Flows Gone After an Update? Don't Deploy — Find the Flow File

You update Node-RED (or the Home Assistant add-on, or your device's firmware), open the editor, and the canvas is **completely empty**. Years of flows, apparently gone.

**They're almost certainly still on disk.** Node-RED is reading a different file or directory than before.

## Rule one: do not press Deploy

If you deploy now, Node-RED writes the **current (empty) canvas** over the flow file and the backup. That turns a recoverable situation into a real loss.

Also: **don't install nodes, don't change settings, don't let anything trigger a deploy.** Stop the editor if you can and work on the files.

## Why it happens

**The flow file is named after the hostname.** By default Node-RED derives the flow filename from the machine's hostname (`flows_<hostname>.json`). Change the hostname — a new container name, a restored VM, a device firmware update that renames the host — and Node-RED looks for a file that has never existed, finds nothing, and gives you a blank canvas.

**The user or data directory changed.** A documented case: an update moved the process from running as `root` to its own user, so the user directory went from `/data/home/root/.node-red/` to `/data/home/nodered/.node-red/`. Same software, different directory, empty flows.

**The volume isn't mounted where it was.** In Docker, `/data` not mounted (or mounted to a new named volume) means a fresh install every start.

**An add-on data path change** — the same pattern that bites Zigbee2MQTT and Z-Wave JS UI users.

## Find the file

```bash
# in the container / on the host
find / -name "flows*.json" -mmin -100000 2>/dev/null | head -20
ls -la ~/.node-red/
ls -la /data/            # docker / add-on
```

You're looking for `flows.json`, `flows_<somehostname>.json`, and the `.backup` variants. Note the **size** — a file of a few hundred bytes is an empty flow; yours is probably much bigger.

Then check what Node-RED thinks it should be using: the **startup log** prints the user directory and the flow file on every boot:

```
docker logs node-red | head -30
```

That line is the answer to "where is it looking".

## Restore, in order of safety

**1. Point Node-RED at the file it already has.**
In `settings.js`:
```js
flowFile: 'flows.json',
```
Or start with `node-red flows_oldhostname.json`, or set the environment variable (`FLOWS=flows_oldhostname.json`). This is the cleanest fix when the hostname changed: pin the filename explicitly so it can never happen again.

**2. Rename the old file to what it now expects.**
Copy (don't move) `flows_oldhostname.json` to the expected name, restart, check the canvas, then keep the original as a backup.

**3. Use the backup files.**
Every deploy writes `.flows.json.backup` (and `.flows_cred.json.backup`) in the user directory. If the main file was truncated, the backup is one deploy old:
```bash
cp .flows.json.backup flows.json
```
Dot-prefixed, so use `ls -la`.

**4. Restore the whole directory from a system backup / snapshot.**
On Home Assistant, a full add-on backup from before the update. On Proxmox/VM, a snapshot.

**5. Import a previous export.**
If you ever exported flows (hamburger menu → Export), import that JSON. This is why exporting after every significant change is worth the ten seconds.

## Credentials are a separate file

`flows_cred.json` holds encrypted credentials and is **tied to your `credentialSecret`**. If you restore flows from one install and credentials from another — or lose the secret — nodes come back with empty passwords and tokens.

- Set an explicit **`credentialSecret`** in `settings.js` and keep it with your backups. Without it, Node-RED generates one and stores it in `.config.runtime.json`; lose that and your credentials are unreadable
- Restore `flows.json` and `flows_cred.json` **as a pair**

## Prevent it properly

1. **Pin `flowFile`** in `settings.js` so the hostname never decides your filename
2. **Set `credentialSecret`** explicitly, and store it where your backups are
3. **Named volume for the user directory**, mounted at the same path every time
4. **Export your flows** to a file (or a git repo) after significant changes — `projects` mode gives you git integration built in
5. **Back up before updating**, and check the first startup log line after

## FAQ

**Are my flows deleted?**
Very unlikely. Look for `flows*.json` and the dot-prefixed `.backup` files before concluding anything.

**Why did a hostname change break it?**
The default flow filename is derived from the hostname, so a rename points Node-RED at a file that doesn't exist.

**Can I recover credentials without the secret?**
No. That's the point of the encryption — which is why the secret belongs in your backups.

**Is it safe to restart Node-RED while debugging?**
Restarting is fine. **Deploying** is what overwrites your file.
