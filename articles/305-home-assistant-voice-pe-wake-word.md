---
title: "Home Assistant Voice PE: Wake Word Not Responding"
slug: home-assistant-voice-pe-wake-word
meta_description: "The ring lights up but nothing happens, or the wake word is ignored entirely. Which stage of the pipeline is failing and how to prove it."
updated: October 2026
cluster: round 13 (tech) — HA community and voice-pe GitHub
competition: LOW
---

# Home Assistant Voice PE: Wake Word Not Responding

The Voice Preview Edition runs wake-word detection **on the device**, then sends audio to Home Assistant for the rest. That split is the key to debugging: if the LED ring never reacts, the device isn't hearing you; if the ring reacts but nothing happens, the problem is in HA's pipeline.

## 1. Does the ring react at all?

Say the wake word and watch the ring.

**No reaction.** The device-side wake word isn't firing. Causes, in order:

- **Wrong wake word selected.** In **Settings → Devices → Voice PE**, check the *Wake word* entity. The device ships with `okay_nabu`; `hey_jarvis` and `alexa` are also available. Saying "Hey Nabu" when it's set to `okay_nabu` fails — the model expects "Okay, Nabu".
- **Microphone muted.** There's a physical mute switch on the back. When muted the ring shows a static red, which people read as an error state.
- **The device is on but not connected.** Check the device page in HA; an offline device still powers its LEDs.
- **Too far, or too noisy.** The two-microphone array is good but not magic. Under about 3 m in a quiet room is where it's reliable; across an open-plan kitchen with a dishwasher running it isn't.
- **Firmware stale.** Update the device from its HA device page; wake-word model improvements ship in firmware.

**Ring reacts, then goes dark with no response.** Continue to section 2.

## 2. The pipeline after the wake word

Open **Settings → Voice assistants** and look at the assistant assigned to this device. Then use **Developer tools → Assist → Debug** to see exactly which stage failed — this view names the failing stage, which saves all guessing.

The stages and their characteristic failures:

| Stage | Failure looks like | Usual cause |
|---|---|---|
| Speech-to-text | Ring listens, then error chime | Whisper add-on down, or no STT engine selected |
| Intent | "Sorry, I don't understand" | Entity not exposed to Assist, or aliases missing |
| Text-to-speech | Action happens, no spoken reply | Piper add-on down, or no TTS engine selected |

**STT:** if you run `faster-whisper` as an add-on, check it's started and which model. The `tiny-int8` model on a Pi is fast but mishears; `base` is the practical floor for English. A stopped Whisper add-on gives an immediate error chime and is the single most common cause here.

**Intent:** this is where most "it heard me but did nothing" ends up. Assist only controls entities you've **exposed**. Settings → Voice assistants → Expose. A light that works in the UI and not by voice is almost always unexposed, or named something the recogniser can't match ("Light 3" vs. an alias of "desk lamp").

**TTS:** Piper stopped, or the Voice PE's media player entity muted. Check the volume entity on the device — it's separate from the ring brightness and resets on some firmware updates.

## 3. The "it worked, now it doesn't" case

Three specific regressions worth checking:

- **Cloud vs. local assistant swapped.** If you had Nabu Casa cloud STT and the subscription lapsed, the pipeline silently has no engine.
- **A HA update reset the device's assistant assignment.** Re-select it on the device page.
- **The ESPHome device needs re-adoption.** After a major HA upgrade, the device can show as connected while its API encryption key no longer matches. The log line to look for, in the ESPHome integration, is a handshake failure.

```bash
# from the HA host, if you have SSH access
grep -i 'voice\|wake_word\|assist_pipeline' /config/home-assistant.log | tail -40
```

## What not to do

- **Don't factory-reset at the first sign of trouble.** It loses the Wi-Fi config and the HA pairing, and the cause is almost always in the pipeline configuration rather than the device.
- **Don't train a custom wake word to fix sensitivity.** The device's built-in models are considerably better than a quickly-trained custom one; distance and noise are the real variables.
- **Don't expose every entity to Assist.** More entities means more name collisions and worse recognition. Expose what you'll actually ask for.
- **Don't run Whisper's large models on a Raspberry Pi** and conclude voice is broken. It will time out.

## Prevention

| Habit | Why |
|---|---|
| Give entities short, distinct aliases | The single biggest accuracy improvement available |
| Keep Whisper/Piper add-ons on auto-start | Removes the most common post-reboot failure |
| Use the Assist debug view first, every time | Names the failing stage in seconds |
| Place the device away from appliances and hard corners | Reflections hurt the microphone array more than distance |

## FAQ

**Can I use a different wake word than the three built in?**
Yes, with microWakeWord models, but expect lower accuracy than the shipped ones.

**Does it work with no internet?**
Entirely, if your STT, TTS and conversation agent are all local add-ons. With cloud STT it does not.

**Can it answer general questions?**
Only if you assign an LLM conversation agent as a fallback in the pipeline. The default intent engine handles device control and little else.

**The ring flashes red briefly.**
That's the generic error state. The Assist debug view will say which stage produced it.
