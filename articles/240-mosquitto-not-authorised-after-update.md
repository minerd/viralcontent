---
title: "Mosquitto 'Connection Refused: Not Authorised' After an Update? Anonymous Logins Are Gone"
slug: mosquitto-not-authorised-after-update
meta_description: "Every MQTT client stops connecting after a Mosquitto upgrade. Anonymous access removal, password and ACL file formats, and how to add credentials to each client."
updated: October 2026
cluster: round 11 (tech) — HA addons GitHub issues and project forums only
competition: LOW
---

# Mosquitto 'Connection Refused: Not Authorised' After an Update? Anonymous Logins Are Gone

You update the broker and **everything** stops at once: Zigbee2MQTT, ESPHome devices, Node-RED, your own scripts, `mosquitto_sub`. The log is a wall of `disconnected: not authorised`.

**The usual cause is deliberate: support for anonymous MQTT logins was removed.** The Home Assistant Mosquitto add-on dropped anonymous access in its 6.0.0 release, and other packagings have tightened the same default. Anything that was connecting without a username and password now can't.

This is a breaking change, not a bug. The fix is to give every client credentials.

## Step 1: create a user

**Home Assistant add-on:** create a normal Home Assistant user for MQTT — **Settings → People → Users → Add**, with a name and password, **no administrator rights and no remote access needed**. The add-on authenticates MQTT clients against Home Assistant users, so that account becomes your MQTT login.

**Standalone Mosquitto:**
```bash
mosquitto_passwd -c /mosquitto/config/passwd mqttuser     # -c creates, omit it to add
```
and in `mosquitto.conf`:
```
allow_anonymous false
password_file /mosquitto/config/passwd
listener 1883
```
Then restart. Note `mosquitto_passwd` rewrites the file in place — the file must be readable by the broker user (`chown mosquitto:mosquitto`, `chmod 0700`), or Mosquitto refuses to start and you get a different error.

## Step 2: add the credentials to every client

Go through them one at a time. The usual list:

- **Home Assistant MQTT integration** — Settings → Devices & Services → MQTT → Configure → re-enter username/password
- **Zigbee2MQTT** — `configuration.yaml`:
  ```yaml
  mqtt:
    server: mqtt://core-mosquitto:1883
    user: mqttuser
    password: yourpassword
  ```
- **Z-Wave JS UI** — MQTT settings in the UI
- **ESPHome** — in each device's YAML if it uses MQTT directly (most use the native API instead), then reflash
- **Node-RED** — each MQTT broker config node, Security tab
- **Tasmota / Shelly / ESP devices** — web UI → MQTT settings, per device
- **Frigate, Scrypted, Room Assistant, your own scripts** — config files and env vars
- **`mosquitto_sub` / `mosquitto_pub`** — add `-u user -P password`

Anything you forget shows up as the only thing still failing, which is actually a convenient way to find them all.

## Step 3: if you had a working password/ACL file

Upgrades have also broken **custom password and ACL files** that worked on the previous version (reported going from 6.5.x to 7.x). Check:

- **Password file format** — regenerate it with the **new version's** `mosquitto_passwd` rather than carrying the old file over. Hash formats have changed across major versions
- **ACL file syntax** — `user`, `topic read/write`, `pattern` lines; a single malformed line can deny everything
- **File paths inside the container** — an add-on or image update can change where it looks
- **Permissions and ownership** on both files

Read the broker's own startup log: it reports which password and ACL files it loaded, and complains about ones it couldn't parse.

## Step 4: tell the error messages apart

| Log line | Meaning |
|---|---|
| `Connection Refused: not authorised` | Authentication or ACL rejected the client |
| `Connection refused` (TCP level) | Nothing is listening — port, listener config, or container down |
| `Socket error on client ..., disconnecting` | Often TLS mismatch (client plain, broker TLS, or vice versa) |
| `Bad user name or password` | Credentials wrong, or password file format mismatch |
| Connects then drops every few seconds | Two clients using the **same client ID** — each kicks the other off |

That last one is worth remembering: duplicate client IDs cause a flapping loop that looks like an auth problem.

## Step 5: as a temporary bridge only

You can re-enable anonymous access on a standalone broker (`allow_anonymous true`) to get the house working while you add credentials. Understand what that means: anything on your network can read and publish everything, including your door locks. On the Home Assistant add-on, anonymous support is simply gone in current versions, so plan on credentials.

If you need unauthenticated local devices, put them on a **separate listener** bound to a restricted interface, with ACLs limiting their topics — not on the main one.

## Prevention

1. **Pin versions** for the broker; read the release notes before a major bump
2. **Back up** `mosquitto.conf`, the password file and the ACL file together
3. Use a **separate MQTT user per client** so a rotated password doesn't take down everything at once
4. Keep a **list of MQTT clients** — you will need it on the day you rotate credentials

## FAQ

**Why did anonymous access stop working?**
It was removed from the add-on in 6.0.0, and similar defaults tightened elsewhere. It's intentional.

**Do I need a separate Home Assistant user for MQTT?**
With the add-on, yes — that's how clients authenticate. It needs no admin rights.

**My old password file stopped working.**
Regenerate it with the new version's `mosquitto_passwd`; hash formats change between major versions.

**Everything connects except one device.**
You missed its credentials — or two devices share a client ID.
