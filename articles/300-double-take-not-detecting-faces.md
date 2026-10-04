---
title: "Double-Take Not Detecting Faces? The Frigate Event Chain, Step by Step"
slug: double-take-not-detecting-faces
meta_description: "Double-Take shows no matches, empty matches, or unknown only. How to prove each link in the MQTT → snapshot → detector chain before changing settings."
updated: October 2026
cluster: round 13 (tech) — Double-Take GitHub issues
competition: LOW
---

# Double-Take Not Detecting Faces? The Frigate Event Chain, Step by Step

Double-Take is a thin coordinator. It listens for an event, fetches an image, sends it to a detector, and records the answer. When "it isn't detecting", exactly one of those four links is broken — and the UI looks the same for all four.

Work the chain in order. Don't touch the recognition settings until you've proved the first three.

## 1. Is Double-Take receiving the event?

Double-Take subscribes to Frigate's MQTT topic. If that connection is wrong, the UI stays permanently empty — no matches, no unknowns, nothing.

Watch the broker directly:

```bash
mosquitto_sub -h 192.168.1.10 -u user -P pass -t 'frigate/events' -v
```

Walk in front of a camera. If nothing prints, the problem is Frigate→MQTT, not Double-Take. If events print, check Double-Take's own log:

```bash
docker logs double-take --tail 50 | grep -i mqtt
```

You want `MQTT: connected`. Common causes of a silent failure:

- The broker now requires authentication (Mosquitto 2.x removed anonymous access by default) and Double-Take's config has no credentials
- `topics.frigate` in config doesn't match Frigate's `mqtt.topic_prefix`
- The broker hostname resolves inside Home Assistant but not inside the Double-Take container

```yaml
mqtt:
  host: 192.168.1.10
  username: mqttuser
  password: mqttpass
frigate:
  url: http://192.168.1.10:5000
```

## 2. Can Double-Take fetch the snapshot?

This is the single most common real cause. Double-Take gets an event ID over MQTT, then makes an **HTTP request back to Frigate** for the image. If that URL is wrong or unreachable from inside the container, you get events with no images and therefore no detections.

```bash
docker exec -it double-take \
  curl -s -o /dev/null -w '%{http_code}\n' http://192.168.1.10:5000/api/version
```

A 000 or a timeout means the `frigate.url` in your config is not reachable from the container. Things that break it:

- `localhost` or `127.0.0.1` in `frigate.url` — that's the Double-Take container, not Frigate
- A reverse proxy with auth in front of Frigate, so the request gets a login page instead of a JPEG
- Frigate on a different Docker network

Use the host's LAN IP, not a hostname and not localhost.

## 3. Is the detector answering?

Check which detector you configured and prove it independently. For CompreFace:

```bash
curl -s -X POST \
  -H "x-api-key: YOUR_RECOGNITION_KEY" \
  -F file=@/tmp/testface.jpg \
  'http://192.168.1.10:8000/api/v1/recognition/recognize'
```

The two failures here are mundane and specific:

- **Wrong API key type.** CompreFace issues separate keys for *Recognition*, *Detection* and *Verification* services. A detection key in the recognition slot returns an authorisation error. This catches almost everyone once.
- **No trained subjects.** A recognition service with zero faces enrolled returns results with no subject — which Double-Take correctly records as `unknown`. That's not a bug.

For DeepStack/CodeProject.AI, the equivalent check is `POST /v1/vision/face/recognize`, and the equivalent trap is that the face *registration* endpoint is different from the recognition one.

## 4. Only then, tune matching

If images arrive and the detector answers but everything is `unknown`:

```yaml
detect:
  match:
    save: true
    confidence: 60
    purge: 168
  unknown:
    save: true
    confidence: 40
```

- **Lower `confidence` to around 50–60** to start. The default is often too strict for the small, angled faces a doorbell camera produces.
- **Set `unknown.save: true`.** Then look at the saved unknowns in the UI — this is the fastest way to learn whether you have a *recognition* problem or an *image quality* problem. Blurry 150-pixel faces will never match, no matter the threshold.
- **Train from your own camera's images, not from phone photos.** Enrol 5–10 faces captured by the same camera at the same angle and lighting. Recognition accuracy from camera-native training images is dramatically better, and this is the change that fixes most "it never matches" reports.

Also check `detect.cameras` — if you've listed cameras explicitly, any camera not in that list is ignored silently.

## What not to do

- **Don't raise confidence to force matches.** It's the wrong direction; you'll get false positives on anyone walking past.
- **Don't train on 50 images of the same frame.** Variety of angle and light beats volume.
- **Don't run detection on every frame.** Double-Take is event-driven by design; pointing it at a continuous stream burns CPU for no accuracy gain.
- **Don't skip step 2.** "Detector settings" is where people start and it's almost never the cause.

## Prevention

| Habit | Why |
|---|---|
| Put Frigate, the broker and Double-Take on one Docker network with service names | Removes the whole class of URL-reachability failures |
| Keep `unknown.save: true` permanently | Gives you evidence on every miss instead of a blank UI |
| Re-train when you change a camera or its mount | Angle and lens change the embedding more than people expect |
| Note which CompreFace key is which, in a comment | The three-key confusion recurs every reinstall |

## FAQ

**Should I use Frigate's built-in face recognition instead?**
If your Frigate version has it, yes for simple cases — fewer moving parts. Double-Take still wins when you want one recognition database shared across Frigate, HA and other sources.

**Matches work but no Home Assistant sensor appears.**
That's the MQTT publish side, not detection. Check that Double-Take's `mqtt.topic_prefix` matches what your HA template sensor subscribes to.

**It worked and then stopped after an update.**
Check the broker first: a Mosquitto major upgrade silently cutting anonymous clients is the most frequent post-update cause.

**Can it use a Coral TPU?**
Frigate's object detection can. Face recognition runs on the detector you've chosen, which is CPU or GPU — the Coral isn't in that path.
