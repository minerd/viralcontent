---
title: "motionEye Cameras Offline After an Update? The Stale Motion Process"
slug: motioneye-camera-offline
meta_description: "RTSP cameras that stop displaying after a motionEye or OS update, or stay grey after reconnecting. Why changing a setting fixes it, and what to check in the log."
updated: October 2026
cluster: round 12 (tech) — motionEye GitHub issues and HA community
competition: LOW
---

# motionEye Cameras Offline After an Update? The Stale Motion Process

Two characteristic symptoms, both pointing at the same place:

- Cameras that **worked before an update** no longer display, while **VLC still plays the same RTSP URL**
- A camera that reconnected but the live view keeps showing grey **"Unable to open video device"**

## 1. Force motion to restart

motionEye is a front-end for **motion**. The documented workaround for a stuck camera is to **modify any camera setting**, which triggers a motion restart and restores the live view.

That's worth internalising: the camera isn't gone, motion's process state is stale.

```bash
sudo systemctl restart motioneye
# container
docker restart motioneye
```

If a setting change or restart fixes it every time, you have a workaround and the rest of this is about the root cause.

## 2. Read the log

```bash
tail -50 /var/log/motioneye.log
journalctl -u motioneye -n 100 --no-pager
docker logs motioneye --tail 100
```

What to look for:
- `Unable to open video device` with the RTSP URL → motion can't connect: credentials, URL, transport
- ffmpeg/libav errors naming a codec → format problem (section 3)
- Repeated reconnect attempts → the camera is dropping the connection, or limiting clients

## 3. RTSP cameras after an update

Reported: RTSP cameras stopped working after a system update while working fine in VLC. Causes worth checking in order:

- **ffmpeg/libav version change** on the host, altering how the stream is negotiated. Try forcing TCP transport in the camera's URL or motion options (`rtsp_transport tcp`)
- **H.265** streams that the new build won't decode — switch the camera to **H.264**
- **URL-encode special characters** in the password (`@` → `%40`)
- Camera **client limits**: motionEye plus a phone app plus an NVR is often one connection too many. Use the substream
- Camera **firmware** updated itself and changed the stream path

Test from the motionEye host, not your laptop:

```bash
ffprobe -rtsp_transport tcp "rtsp://user:pass@192.168.1.60:554/stream1"
```

## 4. Pi camera / local devices

- After a Raspberry Pi OS update, the **legacy camera stack vs libcamera** change breaks local camera access. motionEyeOS and motionEye in a container handle these differently — check which stack your version expects
- `/dev/video*` missing → the module didn't load, or the container isn't passed the device:
  ```yaml
  devices:
    - /dev/video0:/dev/video0
  ```
- Reported for Pi cameras: going offline intermittently, often power or ribbon-cable related. Re-seat the cable, use a better supply

## 5. One offline camera breaking the whole list

Documented bug: an **offline camera behind a remote motionEye** breaks the entire camera list with an HTTP 500 (`KeyError: 'enabled'`).

If the UI won't load at all after one camera went away:
- Remove or disable that camera from the config (`/etc/motioneye/camera-*.conf`) and restart
- Keep remote-motionEye setups simple; a failing remote takes its parent with it

## 6. The update itself takes a long time

motionEyeOS updates can take **up to 30 minutes** depending on network, SD card and CPU. A device that looks dead ten minutes in may simply be mid-update. Don't power-cycle during that window.

## Prevention

1. **Pin versions**; motionEye is quiet upstream, so don't chase updates you don't need
2. **Substreams** for motion detection, main streams only where needed
3. **Static IPs** for cameras; URL-encode credentials
4. **H.264** for compatibility
5. Back up `/etc/motioneye/` — it's your whole camera configuration

## FAQ

**Why does changing a setting fix the camera?**
It restarts motion, clearing the stale process state behind the grey view.

**VLC plays the stream but motionEye doesn't.**
Transport, codec, or a client limit on the camera. Test with ffprobe from the motionEye host.

**The whole UI 500s after one camera went offline.**
A known issue with offline cameras in remote setups — disable that camera's config and restart.

**Is motionEye still the right tool?**
It works, but it's lightly maintained. If you're hitting repeated breakage, Frigate or go2rtc-based setups are the active alternatives.
