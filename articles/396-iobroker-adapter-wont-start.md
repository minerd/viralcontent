---
title: "ioBroker: Adapter Instance Stays Red and Won't Start"
slug: iobroker-adapter-wont-start
meta_description: "An instance exits with code 1, can't find adapter-core, or just stays red. The Node version rebuild, the fix script, and reading the right log."
updated: October 2026
cluster: round 14 (tech) — ioBroker GitHub and forum
competition: LOW
---

# ioBroker: Adapter Instance Stays Red and Won't Start

Red means the instance isn't running. The reason is in the log, and ioBroker's log is per-adapter — look at the adapter's own lines, not the aggregate:

```bash
iobroker logs --lines 100
tail -n 100 /opt/iobroker/log/iobroker.current.log | grep -i '<adapter-name>'
```

Three errors cover most cases.

## 1. "Cannot find module '@iobroker/adapter-core'"

The adapter's dependencies are missing or were installed for a different Node version. This is the most common cause after a Node.js upgrade.

```bash
cd /opt/iobroker
iobroker stop
npm rebuild
iobroker start
```

If that doesn't do it, reinstall the single adapter:

```bash
iobroker stop <adapter>.0
npm install iobroker.<adapter> --production
iobroker start <adapter>.0
```

And the project's own repair script, which is the sanctioned fix for a mixed-up installation:

```bash
iobroker stop
curl -sL https://iobroker.net/fix.sh | bash -
iobroker start
```

`fix.sh` corrects ownership, permissions and the Node module tree. It is the right first move whenever several adapters break at once — that pattern is almost always environmental rather than per-adapter.

## 2. "terminated with code 1 (JS_CONTROLLER_STOPPED)" after a Node upgrade

A documented case: upgrading Node from 16 to 18 (and the same applies to later majors) leaves native modules built against the old ABI. Adapters using native code — `echarts`, `zigbee`, `sql`, anything with a serial port — fail to load.

```bash
node --version
cd /opt/iobroker && npm rebuild
```

Check what ioBroker expects:

```bash
iobroker version
iobroker nodejs-update       # where available
```

Running a Node major that ioBroker doesn't support yet is a real cause of unexplained failures. Stay on the version the project recommends; newest is not best here.

## 3. "Adapter fails to start but logs nothing"

Reported for several adapters, and genuinely awkward. Things to try:

**Raise the log level for that instance** — Instances → the adapter → expert settings → log level `debug` or `silly`. Many adapters log their startup failure only at debug.

**Run it in the foreground**, which prints what the log swallows:

```bash
cd /opt/iobroker
node node_modules/iobroker.<adapter>/main.js --instance 0 --force --logs
```

This is the single most useful diagnostic for a silent adapter — a configuration validation error or a missing binary appears immediately.

**Check the instance's configuration object** for something invalid:

```bash
iobroker object get system.adapter.<adapter>.0
```

An empty required field (a serial port that no longer exists, a host that's gone) makes some adapters exit before logging.

## 4. "Instances won't start — they're already running"

A real and confusing state: the UI shows red, and the processes are alive.

```bash
iobroker status
ps aux | grep io\\. | head -20
```

If processes exist for instances the UI calls stopped, js-controller has lost track of them:

```bash
iobroker stop
pkill -f 'io\.'
iobroker start
```

On a Raspberry Pi, a full restart is the reported remedy:

```bash
sudo systemctl restart iobroker
```

## 5. The red-for-ten-seconds case

Worth separating so you don't chase it: after a **browser refresh or a tab switch**, adapters can show red for roughly ten seconds before turning green. That's the admin UI re-establishing its socket, not an adapter problem. If it goes green on its own, nothing is wrong.

Similarly, the **Devices** adapter showing red after a refresh has been reported as a UI artefact.

## 6. Adapter-specific: the Node-RED adapter

```bash
ls -la /opt/iobroker/iobroker-data/node-red/
```

Credentials and settings files in the Node-RED data directory can prevent startup — a `flows_cred.json` that can't be decrypted because `credentialSecret` changed is the classic. Remove the credentials file (you lose stored credentials in flows, not the flows themselves) and restart:

```bash
iobroker stop node-red.0
mv /opt/iobroker/iobroker-data/node-red/flows_cred.json{,.bak}
iobroker start node-red.0
```

## What not to do

- **Don't run `npm install` as root in `/opt/iobroker`.** It breaks ownership; `fix.sh` exists to repair that.
- **Don't upgrade Node to the newest major** because it's available. Match ioBroker's supported version.
- **Don't delete an instance to fix it.** You lose its objects and states. Reinstall the adapter instead.
- **Don't ignore a red that clears itself.** It's the UI, and chasing it wastes time.

## Prevention

| Habit | Why |
|---|---|
| `npm rebuild` after every Node upgrade | Native modules are ABI-bound |
| `fix.sh` as the first move for multi-adapter failures | Repairs the environment, not symptoms |
| Node on ioBroker's supported major | Removes a whole class of unexplained exits |
| Back up with ioBroker's own backitup adapter | Objects, states and configuration in one archive |

## FAQ

**Where are objects and states stored?**
`/opt/iobroker/iobroker-data/`. Back that up, not just the config.

**Can I run two instances of one adapter?**
Yes, `.0`, `.1` and so on, each with its own configuration.

**An adapter is "not available" in the admin UI.**
Repository list stale or unreachable. Update it from the Adapters page, and check outbound access.

**Multi-host setup, instance red on one host.**
The adapter must be installed on the host that runs it; check `system.adapter.<adapter>.0.common.host`.
