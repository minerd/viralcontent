---
title: "Fluidd: \"No Moonraker Connection\""
slug: fluidd-moonraker-not-connected
meta_description: "Fluidd or Mainsail won't connect after an update. cors_domains, trusted_clients, the dependency failure on vendor Klipper builds, and the one-command check."
updated: October 2026
cluster: round 14 (tech) — Klipper Discourse, Arksine/moonraker, Fluidd docs
competition: LOW
---

# Fluidd: "No Moonraker Connection"

One command decides where to look:

```
http://<printer>/server/info
```

Open that in a browser.

- **JSON with `klippy_state`** → Moonraker is running and reachable. The problem is CORS or the websocket (sections 2–3).
- **Nothing / connection refused** → Moonraker isn't running (section 1).
- **A 502 from nginx** → nginx is up, Moonraker isn't.

## 1. Moonraker isn't running

```bash
sudo systemctl status moonraker
tail -n 60 ~/printer_data/logs/moonraker.log
```

Common entries:

- **`Invalid config` naming a section** — Moonraker is strict and refuses to start on an unknown option. The log names the line. Options move between versions, so this is the usual post-update failure.
- **A missing Python dependency.** This is the documented cause of the most common post-update breakage, and it has a specific shape:

> On a normal install, new dependencies are installed during the Moonraker update. **Creality machines (and some other vendor builds) do not install Moonraker in a proper virtualenv with pip available**, so a Moonraker update that adds a dependency leaves it uninstallable, and Moonraker won't start.

```bash
~/moonraker-env/bin/python -c 'import moonraker' 2>&1 | tail -3
ls ~/moonraker-env/bin/pip
```

No `moonraker-env` means a vendor install. On those machines, use the vendor's or community helper script's Moonraker update path rather than `git pull` in `~/moonraker`. The Creality helper-script communities maintain exactly this because the standard update breaks.

For a standard install, reinstall the dependencies:

```bash
cd ~/moonraker
~/moonraker-env/bin/pip install -r scripts/moonraker-requirements.txt
sudo systemctl restart moonraker
```

- **Database or lock problems** — `Unable to open database` points at permissions or a full disk:

```bash
df -h
ls -ld ~/printer_data/database
```

## 2. cors_domains

Fluidd and Mainsail run in your browser and call Moonraker directly. Moonraker enforces CORS, so the origin you load the UI from must be allowed:

```ini
# ~/printer_data/config/moonraker.conf
[authorization]
trusted_clients:
    10.0.0.0/8
    127.0.0.0/8
    169.254.0.0/16
    172.16.0.0/12
    192.168.0.0/16
    FE80::/10
    ::1/128
cors_domains:
    *.lan
    *.local
    *://localhost
    *://localhost:*
    *://my.mainsail.xyz
    *://app.fluidd.xyz
```

Points that matter:

- **`app.fluidd.xyz` and `my.mainsail.xyz`** are needed if you use the hosted frontends. Omit them and the hosted UI connects to nothing while the locally-served one works — a confusing asymmetry.
- **`trusted_clients`** must include the subnet you browse from. A client outside it gets 401s on every API call, which Fluidd reports as no connection.
- **A hostname you reach the printer by** must be covered. `*.lan` covers `printer.lan`; it does not cover `printer.home.arpa`.
- Changes need a Moonraker restart.

## 3. The websocket

Fluidd polls over HTTP and streams over a websocket. Behind a reverse proxy, the upgrade must pass:

```nginx
location /websocket {
    proxy_pass http://127.0.0.1:7125/websocket;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $http_host;
    proxy_read_timeout 86400s;
}

location ~ ^/(printer|api|access|machine|server)/ {
    proxy_pass http://127.0.0.1:7125$request_uri;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Without the upgrade headers you get a UI that loads, shows some data once, and reports no connection. With a short `proxy_read_timeout` it connects and drops every minute.

## 4. Klipper is down, not Moonraker

```bash
curl -s http://localhost:7125/printer/info | python3 -m json.tool
```

```json
{"result": {"state": "shutdown", "state_message": "MCU 'mcu' shutdown: Timer too close"}}
```

Moonraker connected to Klipper and Klipper is in error. The UI may show a connection warning that reads like Moonraker's. The `state_message` is Klipper's own and tells you the real problem:

```bash
tail -n 40 ~/printer_data/logs/klippy.log
```

`klippy_uds_address` must point at where Klipper actually puts its socket:

```ini
[server]
host: 0.0.0.0
port: 7125
klippy_uds_address: ~/printer_data/comms/klippy.sock
```

A path mismatch after the `klipper_config` → `printer_data` migration is a frequent cause.

## 5. "Switch it off and on again" is sometimes correct

Reported for Creality machines specifically: after a Moonraker update, **power-cycling the printer restores the connection**. That isn't superstition — on those builds a service restart leaves stale state, and a cold boot re-runs the vendor's init properly.

Try it before deeper investigation on a vendor machine. On a standard Pi install, a service restart is equivalent and a power cycle tells you nothing extra.

## 6. Works locally, not remotely

- `trusted_clients` doesn't include the remote range (and shouldn't — use a VPN rather than widening it).
- A tunnel or proxy not passing the websocket.
- `cors_domains` missing the external hostname.

Exposing Moonraker directly to the internet is a bad idea regardless: it has no authentication by default and can run arbitrary G-code. Use Tailscale, WireGuard or a vendor relay.

## What not to do

- **Don't widen `trusted_clients` to `0.0.0.0/0`.** That hands printer control to anyone who can reach it.
- **Don't `git pull` Moonraker on a vendor build.** Use the vendor's or helper script's path.
- **Don't edit `moonraker.conf` while Moonraker is running** and expect it to apply. Restart.
- **Don't debug Fluidd when `/printer/info` shows a Klipper shutdown.** Fix Klipper.

## Prevention

| Habit | Why |
|---|---|
| `cors_domains` including both hosted frontends | Removes the works-locally-only confusion |
| `trusted_clients` scoped to your LAN, VPN for remote | Secure and correct |
| Note whether yours is a standard or vendor install | Determines the entire update procedure |
| Back up `printer_data/config` | Config, macros and Moonraker settings together |

## FAQ

**Fluidd or Mainsail?**
Both talk to the same Moonraker and can be installed side by side. Everything here applies to both.

**Can I run them on a different machine?**
Yes — the frontend is static files; point it at the printer's Moonraker, and add that origin to `cors_domains`.

**Timelapse stopped working too.**
moonraker-timelapse is a component; a Moonraker update can leave it incompatible. Update it alongside.

**Update manager says a repo is dirty.**
Local edits in a managed repo. Revert them or mark the repo as unmanaged.
