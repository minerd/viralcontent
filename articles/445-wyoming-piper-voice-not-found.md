---
title: "Wyoming Piper: Voice Not Found in Home Assistant"
slug: wyoming-piper-voice-not-found
meta_description: "A new Piper voice doesn't appear, or TTS fails entirely. The integration reload that's required, language options, and the voice download path."
updated: October 2026
cluster: round 14 (tech) — HA community and home-assistant/addons
competition: LOW
---

# Wyoming Piper: Voice Not Found in Home Assistant

The documented cause of most of these, and the one nobody guesses:

> **Home Assistant caches the voice list. After adding a voice, you must reload the Wyoming integration for Piper before the new voice appears.**

```
Settings → Devices & Services → Wyoming Protocol → (the Piper entry) → ⋮ → Reload
```

Do that first. If the voice appears, you're done.

## 2. Language options gate the voice list

A second documented behaviour with the same symptom:

> **While a language option is off, its voices are not offered to Home Assistant at all**, so they will not appear in the Wyoming integration's voice list.

In the Piper add-on configuration:

```yaml
voice: en_US-lessac-medium
length_scale: 1.0
noise_scale: 0.667
noise_w: 0.333
speaker: 0
max_piper_procs: 1
update_voices: true
```

The add-on exposes language toggles; enabling the language, restarting the add-on, **then reloading the Wyoming integration** is the full sequence. Skipping the reload is where it goes wrong.

## 3. Voice downloads

Piper downloads voice models from Hugging Face on first use. Reported failures:

> Socket errors and hostname resolution issues when Piper tried to download voice files, which prevented voice models being downloaded.

So a voice that's selected and never works may simply not be present.

```bash
# the add-on's data directory
ls -la /share/piper/ 2>/dev/null
# or for the container
docker exec wyoming-piper ls -la /data
```

You want `.onnx` and `.onnx.json` pairs per voice. A `.onnx` without its `.json` is a partial download — delete both and let it re-fetch.

Check connectivity from where Piper runs:

```bash
docker exec wyoming-piper sh -c 'curl -s -o /dev/null -w "%{http_code}\n" https://huggingface.co/'
```

For an instance with no internet, download the voice files manually and place them in the data directory:

```bash
V=en_US-lessac-medium
B=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium
curl -L -o /share/piper/$V.onnx      "$B/$V.onnx"
curl -L -o /share/piper/$V.onnx.json "$B/$V.onnx.json"
```

Then restart Piper and reload the integration.

## 4. Piper isn't discovered at all

```bash
docker logs wyoming-piper --tail 50
nc -zv 192.168.1.10 10200
```

The Wyoming protocol for Piper and Whisper is **not always auto-discovered** — a documented report. Add it manually:

```
Settings → Devices & Services → Add integration → Wyoming Protocol
Host: 192.168.1.10
Port: 10200
```

Manual addition is more reliable than discovery and survives mDNS problems. Piper's default port is **10200**; Whisper's is **10300**. Pointing the Piper entry at Whisper's port produces an integration that connects and offers no voices — a confusing symptom with a trivial cause.

```yaml
services:
  wyoming-piper:
    image: rhasspy/wyoming-piper
    command: --voice en_US-lessac-medium
    ports:
      - "10200:10200"
    volumes:
      - ./piper-data:/data
```

Note `command:` carries the voice. Changing it needs a container recreate, not a restart.

## 5. `tts.speak` fails while the UI test works

A documented pair of issues around `tts.speak` with Piper. Check the call shape — the service changed and old examples break:

```yaml
action: tts.speak
target:
  entity_id: tts.piper
data:
  media_player_entity_id: media_player.kitchen
  message: "Dinner is ready"
```

- **`entity_id` is the TTS entity**, `media_player_entity_id` is the speaker. Older `tts.piper_say` examples put the media player in `entity_id`, which fails.
- **A voice override** must name a voice Piper actually has:

```yaml
  options:
    voice: en_US-amy-medium
```

An unavailable voice here fails the whole call — exactly the "voice not found" error, now at call time rather than in the list.

```bash
grep -iE 'piper|tts' /config/home-assistant.log | tail -30
```

## 6. Audio produced but nothing plays

Separate from Piper entirely:

- The media player is unreachable or muted.
- Home Assistant's `external_url`/`internal_url` is wrong, so the speaker is given a URL it can't fetch. This is the classic cause of silent TTS on Chromecast and Sonos:

```yaml
homeassistant:
  internal_url: http://192.168.1.10:8123
  external_url: https://ha.example.com
```

Test by playing the generated file through the media player's own browse interface — if that works and TTS doesn't, it's the URL.

## What not to do

- **Don't add voices and expect them to appear.** Reload the integration.
- **Don't run the large Piper voices on a Pi Zero.** `low` and `medium` quality are the practical options; `high` needs real CPU.
- **Don't point the Piper integration at Whisper's port.**
- **Don't use `tts.piper_say`-era examples.** The service signature changed.

## Prevention

| Habit | Why |
|---|---|
| Reload the Wyoming integration after any Piper change | The documented requirement, and the commonest miss |
| Voices pre-downloaded into a mounted data directory | Works offline, no partial downloads |
| Manual Wyoming entries with explicit ports | Discovery is unreliable; this isn't |
| `internal_url` set correctly | Half of "TTS doesn't work" is the media player's fetch |

## FAQ

**Which voice quality should I use?**
`medium` is the sensible default. `low` is noticeably worse; `high` costs much more CPU for a modest gain.

**Can I use a custom-trained voice?**
Yes — place the `.onnx`/`.json` pair in the data directory and reference it by filename.

**Multiple voices at once?**
Yes, with the voice specified per call in `options`.

**Piper or cloud TTS?**
Piper is fully local and fast enough on modest hardware. Cloud voices sound better; Piper keeps working when your internet doesn't.
