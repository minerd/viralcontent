---
title: "Zigbee2MQTT: External Converter Not Loading, Device Unsupported"
slug: zigbee2mqtt-external-converter-not-loading
meta_description: "A device that worked is suddenly unsupported, or the converter is renamed to .invalid. The 2.x path change and why one bad converter kills them all."
updated: October 2026
cluster: round 14 (tech) — Koenkk/zigbee2mqtt GitHub issues
competition: LOW
---

# Zigbee2MQTT: External Converter Not Loading, Device Unsupported

If a device that worked for months suddenly reports **unsupported** after an update, and you use an external converter, the cause is almost certainly one of three version changes — not your converter's logic.

## 1. The path changed in 2.x

Zigbee2MQTT 2.0 changed how external converters are declared and where they live. The 1.x style:

```yaml
# configuration.yaml — 1.x
external_converters:
  - my_device.js
```

The 2.x style puts them in a directory that Zigbee2MQTT scans automatically:

```
/app/data/external_converters/my_device.js
```

and the `external_converters:` key in `configuration.yaml` is removed. Leaving the old key in place on 2.x, or leaving files in the old location, means they are never loaded and every device that depended on them goes unsupported.

Check where your data directory actually is:

```bash
docker exec zigbee2mqtt ls -la /app/data/external_converters/
docker logs zigbee2mqtt 2>&1 | grep -i 'external converter'
```

A startup line naming each converter it loaded is what you want. Silence means none were found.

A related trap in a specific 2.2.x release: Zigbee2MQTT looked for the directory inside its `dist` folder rather than the data directory. If you're on that version and the file is in the documented place, upgrading is the fix — not moving the file.

## 2. The module format changed

2.x converters use ES module syntax:

```js
// 2.x
import * as m from 'zigbee-herdsman-converters/lib/modernExtend';

export default {
    zigbeeModel: ['TS0601'],
    model: 'MyDevice',
    vendor: 'Tuya',
    description: 'My thing',
    extend: [m.onOff()],
};
```

The 1.x `const fz = require(...)` / `module.exports = {...}` form fails to load on 2.x, and the error is a syntax or import error rather than anything about the device. A converter copied from a 2022 forum post will not work.

## 3. One bad converter stops all of them

This is the behaviour that makes diagnosis confusing: an error while loading **one** converter has, in several versions, aborted the whole loading loop. So adding a new broken converter silently breaks the three working ones you already had, and every associated device goes unsupported at once.

The log names the failing file. Move converters out one at a time:

```bash
docker exec zigbee2mqtt sh -c 'mkdir -p /app/data/_disabled && mv /app/data/external_converters/suspect.js /app/data/_disabled/'
docker restart zigbee2mqtt
```

If everything else comes back, you've found it.

A fourth variant: Zigbee2MQTT has **renamed converters to `*.invalid`** when it could not parse them. If your file has vanished, look for `my_device.js.invalid` — the rename is the clue that it's a parse failure, not a path problem.

## 4. The device is genuinely unsupported

Separate case. The log line is:

```
Device 'xyz' with Zigbee model 'TS0601' and manufacturer name '_TZE200_abcd1234' is NOT supported
```

`TS0601` is a generic Tuya model; the **manufacturer name** is the identifier that matters. A converter must list your exact `_TZE200_...` string:

```js
fingerprint: [{modelID: 'TS0601', manufacturerName: '_TZE200_abcd1234'}],
```

Adding your manufacturer name to an existing converter for the same physical device is usually all that's needed, and it's the right thing to contribute upstream.

Do **not** re-pair the device to fix this. Unsupported is a converter-side state; re-pairing changes nothing and loses the device's bindings.

## 5. After fixing it

```bash
docker restart zigbee2mqtt
```

Then, in the frontend, the device should show its model. If it still shows unsupported with the converter loaded, the fingerprint doesn't match — compare the exact strings from the log, character for character, including the leading underscore.

## What not to do

- **Don't re-pair devices that show unsupported.** It's not a pairing problem.
- **Don't copy converters from old posts.** Check the syntax matches your major version.
- **Don't keep converters you don't need.** Each one is a chance to break the loading loop.
- **Don't skip the coordinator backup before a major upgrade.** `coordinator_backup.json` in the data directory is what saves your network.

## Prevention

| Habit | Why |
|---|---|
| Read the 2.0 migration notes before upgrading | The path and module changes are both breaking |
| One converter per file, in the documented directory | Isolates failures |
| Check the startup log after every restart | Loading failures are only visible there |
| Keep `coordinator_backup.json` backed up | The only recovery from a coordinator problem |

## FAQ

**Can I use ZHA quirks instead?**
Different ecosystem; quirks don't load into Zigbee2MQTT.

**Will my device keep working while unsupported?**
It stays joined and you get raw attribute reporting at best. Automations keyed on named entities break.

**How do I find my device's manufacturer name?**
It's in the log line when the device is rejected, and in the frontend's device page under Zigbee model/manufacturer.

**Should I contribute the converter upstream?**
Yes — adding a fingerprint to an existing converter is a small PR and removes your dependency on a local file.
