---
title: "A Self-Hosted Service Broke After an Update: What to Check, in Order"
slug: self-hosted-after-update-checklist
meta_description: "A repeatable first-hour routine when an update breaks a homelab service: stop the loop, read the right log, prove the data path, roll back, then fix forward."
updated: October 2026
cluster: round 11 (tech) — hub page for the update-regression cluster
competition: LOW
---

# A Self-Hosted Service Broke After an Update: What to Check, in Order

Every one of these has the same shape: it worked yesterday, an update landed, now it doesn't. After writing up a few dozen of them, the same routine solves most cases — and the same four mistakes make them worse.

This is the order. Work top to bottom; don't skip to the interesting part.

## 0. Stop the loop first

A crash-looping container isn't just broken, it's actively doing damage: burning ACME rate limits, hammering a camera or a Z-Wave stick, filling logs, starving the host.

```bash
docker compose stop <service>      # or systemctl stop
```

You lose nothing by stopping it. You can lose a week of certificate quota by leaving it running.

## 1. Write down what actually changed

One line, before you touch anything:

- Service version, **from → to**
- Did the **host** change too (kernel, distro, Proxmox, DSM, firmware)?
- Did **something else** change (new DHCP lease, new disk, new reverse proxy)?
- Was it **you** or an **unattended** update (`latest` tag, Watchtower, add-on auto-update)?

Half of these problems are "two things changed at once and I only remember one".

## 2. Read the right log, not the dashboard

The UI tells you a service is down. The log tells you why. Nearly every article in this cluster comes down to one log line:

```bash
docker compose logs --tail=200 <service>
journalctl -u <service> -n 200 --no-pager
dmesg -T | tail -50                       # OOM kills, USB, GPU, i915
docker inspect <c> --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
```

Three things to look for immediately:

| Clue | Meaning |
|---|---|
| **Exit 137 / OOMKilled: true** | Memory. Not a bug in the release |
| **Config parse error** naming a line | A breaking config change — read the release notes |
| **Permission denied** on a path or device | UID/GID or device passthrough changed |

## 3. Prove the data path

The single most common cause of "all my data is gone" after an update is that the service is **reading a different directory than before**. It is almost never deletion.

- Did the **data path** change? (Zigbee2MQTT's `data_path`, Node-RED's user directory, an add-on's config location)
- Is the **volume still mounted** where it was? `docker inspect <c>` → Mounts
- Is the service **naming the file after the hostname** (Node-RED) or the device node (`/dev/ttyUSB0` vs `/dev/serial/by-id/...`)?
- Find the real files before concluding anything:
  ```bash
  find / -name "<the file>" -size +1k 2>/dev/null | head
  ```

**And do not write anything until you've looked.** Deploying an empty Node-RED canvas, re-pairing a Zigbee network, or re-adding Z-Wave nodes destroys the thing you were about to recover.

## 4. Check what the update changed on purpose

Before debugging a bug, check you aren't fighting an intentional breaking change. Recent real examples from this cluster:

- Mosquitto **removed anonymous logins** — every client needs credentials now
- Vaultwarden **moved WebSockets** off port 3012 onto the main HTTP port
- Traefik **v3 changed rule syntax** — old labels are invalid
- DSM 7 added **per-user SMB application permissions**
- Unraid 7.x **refuses to start an array** with an empty pool
- Grafana identifies datasources by **UID**, and name-based references break

Read the release notes for the version you landed on. Ten minutes there beats two hours of guessing.

## 5. Localise it with one variable

Change exactly one thing and observe:

- **Roll the service back** one version (pinned tag, previous add-on version, previous package)
- Or **pin the previous kernel** and reboot (`proxmox-boot-tool kernel pin`, GRUB advanced options)
- Or bypass a layer: hit the container's port **directly**, skipping the reverse proxy and the tunnel
- Or test on the **LAN** instead of through Cloudflare

Rolling back is not defeat. It gets the household working and converts an outage into a scheduled task.

## 6. Then fix forward

With service restored and the cause known:

- Apply the real fix (credentials, labels, driver package, permissions, config key)
- **Unpin** what you pinned, once the upstream fix lands
- Write down what it was. You will hit the same class of thing again

## The four mistakes

1. **Re-pairing, re-flashing or re-adding devices** before proving the data is gone
2. **Deploying / saving** over an empty configuration
3. **Leaving a crash loop running** while you read forums
4. **Changing five things at once**, so you never learn which one mattered

## Make the next one boring

| Habit | Why |
|---|---|
| **Pin image tags**; never `latest` on infrastructure | Unattended updates are how 3am outages start |
| **Named volumes** for `/data`, config and ACME state | A recreate shouldn't be a fresh install |
| **Back up config, not caches** — `AdGuardHome.yaml`, `database.db`, NVM/Z-Wave backups, `flows.json` + credentials + secret, dashboards as JSON | Restores take minutes when the file exists |
| **Stable device paths** (`/dev/serial/by-id/...`) and DHCP reservations | USB and DHCP reorder on reboot |
| **Read release notes** for major versions | Breaking changes are announced, not hidden |
| **Update when you can watch the first start** | Not at bedtime, not before a trip |
| **Test one thing after upgrading** (a backup job, one dashboard, one device) | Catches it the same day |

## The specific write-ups

Work in this cluster, by service:

- **Media:** Jellyfin [HDR tone mapping](/jellyfin-hdr-tone-mapping-broken), [Intel Quick Sync after an update](/jellyfin-qsv-broke-after-update) · [Sonarr not importing downloads](/sonarr-import-failed)
- **Photos & documents:** Immich [ML container restarting](/immich-machine-learning-restarting), [mobile uploads stuck](/immich-mobile-upload-stuck) · Nextcloud [iOS auto upload](/nextcloud-ios-auto-upload-not-working), [behind a Cloudflare tunnel](/nextcloud-cloudflare-tunnel) · [Paperless-ngx not consuming](/paperless-ngx-consumer-not-working)
- **Home automation:** [Zigbee2MQTT devices unavailable](/zigbee2mqtt-devices-unavailable-after-update) · [Z-Wave JS UI nodes dead](/zwave-js-ui-devices-dead-after-update) · [ESPHome encryption key invalid](/esphome-encryption-key-invalid), [OTA failures](/esphome-ota-failed) · [Mosquitto not authorised](/mosquitto-not-authorised-after-update) · [Node-RED flows missing](/node-red-flows-missing-after-update) · [Scrypted plugin crash loops](/scrypted-plugin-crash-loop) · [Frigate Coral not detected](/frigate-coral-not-detected-after-update) · [Home Assistant app slow on iOS 27](/home-assistant-app-lag-ios-27)
- **Infrastructure:** [Proxmox VM won't start after a kernel update](/proxmox-vm-wont-start-after-kernel-update), [backup jobs failing](/proxmox-backup-job-failed-after-upgrade) · [TrueNAS app stuck deploying](/truenas-app-stuck-deploying) · [Unraid array won't start](/unraid-array-wont-start-after-update) · [Synology SMB after DSM](/synology-smb-not-working-after-dsm-update)
- **Network & access:** [Traefik 404s](/traefik-404-after-update) · [Caddy certificate failures](/caddy-certificate-error-after-update) · [authentik login loops](/authentik-login-loop-after-upgrade) · [Vaultwarden WebSockets](/vaultwarden-websocket-not-working) · [AdGuard Home not responding](/adguard-home-dns-not-responding-after-update) · [Pi-hole not blocking](/pihole-not-blocking-after-update)
- **Dashboards:** [Grafana panels showing No Data](/grafana-no-data-after-upgrade)

### Added in the latest round

- **Home automation:** [Homebridge child bridge No Response](/homebridge-child-bridge-no-response) · [ESPHome Bluetooth proxy stopped](/esphome-bluetooth-proxy-stopped) · [Tasmota lost MQTT](/tasmota-mqtt-stopped) · [WLED won't rejoin Wi-Fi](/wled-not-connecting-wifi) · [Wyoming satellite not detected](/wyoming-satellite-not-detected) · [Music Assistant player unavailable](/music-assistant-player-unavailable) · [Grocy barcode scanner](/grocy-barcode-scanner-not-working)
- **Home Assistant itself:** [recorder database corrupt](/ha-recorder-database-corrupt) · [MariaDB migration stuck](/ha-mariadb-recorder-migration-stuck) · [backups failing](/home-assistant-backup-failed) · [InfluxDB not writing](/ha-influxdb-not-writing)
- **Cameras & NVR:** [Frigate recordings missing](/frigate-recordings-missing) · [Frigate go2rtc streams](/frigate-go2rtc-stream-not-working) · [Frigate semantic search](/frigate-semantic-search-not-working) · [motionEye cameras offline](/motioneye-camera-offline)
- **Media & library tools:** [Jellyfin trickplay](/jellyfin-trickplay-failing) · [Sonarr imports](/sonarr-import-failed) · [Bazarr subtitles](/bazarr-not-downloading-subtitles) · [Jellyseerr requests](/jellyseerr-requests-not-reaching-sonarr) · [Kometa collections](/kometa-collections-not-updating) · [Tautulli notifications](/tautulli-notifications-not-working) · [Tdarr nodes](/tdarr-node-not-connecting) · [Kavita scans](/kavita-scan-stuck) · [Stash scans](/stash-scan-not-finding-scenes) · [Calibre-Web uploads](/calibre-web-upload-failing) · [Audiobookshelf podcasts](/audiobookshelf-podcasts-not-downloading) and [Android Auto](/audiobookshelf-android-auto) · [qBittorrent behind Gluetun](/qbittorrent-gluetun-no-internet)
- **Photos & documents:** [Immich ML container](/immich-machine-learning-restarting) · [Immich duplicates](/immich-duplicate-detection-not-working) · [Paperless-ngx OCR](/paperless-ngx-ocr-failing) · [Nextcloud notify_push](/nextcloud-notify-push-not-working) · [Nextcloud Office loading failed](/collabora-document-loading-failed) · [Mealie imports](/mealie-recipe-import-failing)
- **Network & DNS:** [Pi-hole v6 web interface](/pihole-v6-web-interface-not-loading) · [OPNsense Unbound](/opnsense-unbound-not-resolving) · [OpenWrt Wi-Fi after sysupgrade](/openwrt-wifi-after-sysupgrade) · [Jitsi no audio or video](/jitsi-no-audio-video-self-hosted)
- **Dev & platform:** [Gitea/Forgejo push hooks](/forgejo-gitea-hook-push-failing) · [Wiki.js after an update](/wikijs-not-loading-after-update) · [Pterodactyl console](/pterodactyl-wings-websocket) · [Beszel agents](/beszel-agent-not-connecting) · [Uptime Kuma notifications](/uptime-kuma-notifications-not-working) · [Gotify](/gotify-notifications-stopped) · [ntfy on Android](/ntfy-notifications-not-arriving) · [Vikunja email](/vikunja-email-not-sending) · [Firefly III imports](/firefly-iii-import-stuck) · [Syncthing out-of-sync items](/syncthing-out-of-sync-items) · [Duplicati rebuilds](/duplicati-database-rebuild-stuck)
- **3D printing:** [Moonraker database locked](/moonraker-database-locked) · [OctoPrint serial connection](/octoprint-serial-connection-failed) · [OctoPrint plugins](/octoprint-plugin-not-loading)

## FAQ

**What's the first thing to do?**
Stop the service if it's looping, then read its log. Not the dashboard — the log.

**My data is gone after an update. Is it really?**
Almost certainly not. Find the files on disk before you write anything, and don't deploy, re-pair or re-add.

**Is rolling back bad practice?**
No. It restores service and isolates the cause. Just don't stay on the pinned version forever.

**How do I stop this happening so often?**
Pin tags, use named volumes, back up config files, use stable device paths, and read release notes for major versions.
