---
title: "ESPHome Bluetooth Proxy Stopped Working After an Update? Connection Slots and Stuck States"
slug: esphome-bluetooth-proxy-stopped
meta_description: "A BT proxy that works for hours then stops, or stops seeing devices after an ESPHome update. Connection slot limits, stuck CONNECTING states and what to change."
updated: October 2026
cluster: round 12 (tech) — HA community threads and ESPHome GitHub issues
competition: LOW
---

# ESPHome Bluetooth Proxy Stopped Working After an Update? Connection Slots and Stuck States

Typical reports: BLE sensors update for a few hours after a reboot and then stop; a tracker that was reliable isn't seen any more; the device is pingable and the ESPHome API is fine but Bluetooth does nothing.

## 1. Know which mode you're in

`bluetooth_proxy` has two jobs and they behave differently:

- **Passive scanning** — forwarding advertisements (temperature sensors, trackers). Cheap, many devices
- **Active connections** — HA connects *through* the proxy to a device (locks, kettles, some thermostats). Each ESP32 supports only **about three concurrent connections**

If your problem is "my connected device drops after a while", you are almost certainly out of **connection slots**. Symptoms include connections stuck in `CONNECTING` and other BLE devices going stale at the same time.

What to do:
- Add **more proxies** rather than asking one to do everything
- Set `active: false` on proxies you only want for advertisements:
  ```yaml
  bluetooth_proxy:
    active: false
  ```
- Keep active proxies physically near the devices that need connections
- Remove BLE integrations you don't actually use — each one may hold a slot

## 2. It stopped after an ESPHome update

Reported across several releases: proxies hang after a few hours, or BLE updates stop while the device stays reachable.

In order:
1. **Update ESPHome and reflash** the device (the fix is often already released)
2. If the update caused it, **pin the previous ESPHome version** and reflash; this is a legitimate recovery
3. Check the **ESPHome GitHub issues** for your version plus "bluetooth_proxy"
4. If your config uses the **remote package** for the proxy, make sure the package URL is the current one — stale package references are a documented cause after version bumps

```yaml
packages:
  esphome.bluetooth-proxy: github://esphome/firmware/bluetooth-proxy/esp32-generic.yaml@main
```

## 3. Rule out the boring causes

- **IP changed.** Give every ESPHome device a **DHCP reservation**. An address change breaks the API connection and takes BLE with it
- **Wi-Fi signal.** Check the device's `wifi_signal` sensor; a proxy at the edge of coverage drops its API session and stops forwarding
- **Power.** Cheap USB supplies cause ESP32 brownouts under Wi-Fi + BLE load. Use a decent 5V supply
- **Too much else on the same device.** A proxy that's also running a display, a presence sensor and a dozen entities has less headroom. Dedicated proxies are more reliable
- Only **one Home Assistant** should be connected to the device

## 4. Restore it quickly when it hangs

- **Power-cycle the ESP** (the reliable reset)
- Add an automation that **reboots the proxy** on a schedule or when BLE sensors go stale — crude, effective, and many people run it
- Reload the **ESPHome integration** in HA, or remove and re-add the device from the discovery notification if encryption state got confused
- Keep `safe_mode` configured so a bad flash isn't a trip up a ladder

## 5. Decide whether BT proxy is the right tool

For a handful of advertisement-only sensors, proxies are excellent. For **several actively connected devices**, consider dedicated hardware near them, or a different integration path. Expecting one ESP32 to serve ten connected BLE devices will keep failing whatever the firmware version.

## Prevention

1. **DHCP reservations** for all ESPHome devices
2. **`active: false`** on advertisement-only proxies
3. **Dedicated** proxies — don't stack other roles on them
4. Note the **ESPHome version** before bulk-updating, so rollback is an option
5. Update a **couple of devices first**, not all thirty

## FAQ

**How many BLE devices can one proxy handle?**
Unlimited for advertisements; roughly three concurrent active connections.

**Why does it work after a reboot and then stop?**
Connection slots filling up, or a known firmware hang. Check whether connected devices (not just sensors) are involved.

**Does Wi-Fi signal affect Bluetooth forwarding?**
Yes — the data goes to HA over Wi-Fi. A weak link breaks the whole path.

**Should I run `active: true` everywhere?**
No. Only on proxies you want HA to make connections through.
