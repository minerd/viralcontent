---
title: "Music Assistant: Sonos Announcements Not Playing"
slug: music-assistant-sonos-announcements
meta_description: "No chime on Sonos groups, huge delays, or the track skipping afterwards. The 2.7 regressions, group behaviour, and what to roll back to."
updated: October 2026
cluster: round 14 (tech) — music-assistant/support GitHub issues
competition: LOW
---

# Music Assistant: Sonos Announcements Not Playing

Three distinct, documented behaviours. Identify yours precisely — the workarounds differ.

| Symptom | Where it appears |
|---|---|
| Nothing at all on a **Sonos speaker group**, not even the chime | MA 2.7.0+ |
| Chime plays, TTS is delayed 30 s or absent, sometimes repeats | MA 2.7.2 |
| Announcement plays, then the queue **skips the rest of the track** | Several versions |

## 1. Groups specifically

> **Beginning with MA 2.7.0 there are no announcements played when the target is a Sonos speaker group — not even the chime.** The same text sent to a single Sonos speaker works as expected.

That is the clearest diagnostic in this area: **test a single speaker.** If a single speaker announces and the group doesn't, you have this, and nothing in your configuration is wrong.

Workarounds while it's outstanding:

- **Target the group's coordinator** rather than the group. Announcements to the coordinator propagate on some firmware combinations.
- **Loop over the members** in your automation:

```yaml
action:
  - repeat:
      for_each:
        - media_player.kitchen
        - media_player.living_room
      sequence:
        - action: music_assistant.play_announcement
          target:
            entity_id: "{{ repeat.item }}"
          data:
            url: "media-source://tts/..."
```

You lose synchronisation between rooms, which for a doorbell announcement is usually acceptable.

- **Ungroup, announce, regroup** — reliable, clumsy, and it interrupts whatever was playing.

## 2. Delays and repeats on 2.7.2

> **After upgrading to 2.7.2, announcements on Sonos are broken: not played, or played with a very large delay (30 s), sometimes multiple times.**

And the documented remedy:

> **Reverting to 2.6.3 (backup restore) resolves the issue without any further changes.**

So if your announcements worked and stopped at a specific upgrade, roll back rather than reconfigure. For the Home Assistant add-on:

```
Settings → Add-ons → Music Assistant → ⋮ → Rebuild / or restore a backup
```

Take a Home Assistant backup first. For the Docker deployment, pin the tag:

```yaml
services:
  music-assistant:
    image: ghcr.io/music-assistant/server:2.6.3
```

Pinning is the right posture generally for a component in an automation path — announcements are the kind of thing you notice only when the doorbell doesn't work.

## 3. The track-skipping behaviour

> **After the announcement has played, MA will not resume the currently playing track — instead it starts the next track from the queue, so the remaining part of that track is skipped.**

This is a queue-restoration gap rather than a Sonos problem. Options:

- Accept it for short announcements.
- Announce only when nothing is playing, by guarding the automation:

```yaml
condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: media_player.kitchen
        state: playing
```

- Use Sonos's own `sonos.play_queue`/snapshot-restore services via the Sonos integration instead of Music Assistant for announcements, if you only need TTS to a Sonos speaker. The Sonos integration's snapshot and restore handles mid-track resumption properly.

That last point is worth taking seriously: **if your only requirement is TTS to Sonos, the Sonos integration is the simpler path.** Music Assistant's value is multi-platform playback and library management; announcements are the weakest part of its Sonos support.

## 4. `tts.speak` into Music Assistant

A separate documented issue: `tts.speak` targeting a Music Assistant player breaking in some circumstances. If you're chaining `tts.speak` → MA → Sonos, test the MA announcement service directly:

```yaml
action: music_assistant.play_announcement
target:
  entity_id: media_player.kitchen
data:
  url: "media-source://tts/tts.piper?message=test"
  use_pre_announce: true
  announce_volume: 40
```

If the direct call works and `tts.speak` doesn't, the problem is in that integration path, not in MA's Sonos support — and using `play_announcement` directly is the fix.

## 5. Check the log, not the UI

```bash
# HA add-on
Settings → Add-ons → Music Assistant → Log
# Docker
docker logs music-assistant --tail 100 | grep -iE 'announce|sonos|error'
```

What to look for:

- An announcement **queued** with no playback attempt → the group case (section 1)
- A playback attempt with a Sonos SOAP error → firmware or network
- Nothing logged at all → the service call isn't reaching MA; check the automation

## 6. Things that aren't MA's fault

- **Sonos firmware updates** change local control behaviour periodically. A Sonos app update that re-registers speakers can change their IPs and identifiers.
- **Sonos speakers on a different VLAN** from Music Assistant need multicast reflection; announcements use the same discovery path as everything else.
- **Volume.** `announce_volume` applies and then restores; a speaker muted at the hardware level plays nothing silently.

## What not to do

- **Don't rebuild your automations** before testing a single speaker versus a group. That one test identifies the known issue.
- **Don't run an unpinned Music Assistant in a safety-adjacent automation.** Pin the version.
- **Don't fight the skip-track behaviour with scripts.** Guard the condition or use the Sonos integration.
- **Don't update Sonos and Music Assistant on the same day.** You lose the ability to attribute the change.

## Prevention

| Habit | Why |
|---|---|
| Pinned MA version, with the working one recorded | Announcement regressions have shipped repeatedly |
| Single-speaker test as the first diagnostic | Separates the known group bug from everything else |
| Home Assistant backup before MA upgrades | Rollback is the documented fix |
| Sonos integration for plain TTS-to-Sonos | Fewer moving parts for the simple case |

## FAQ

**Do announcements work on other player types?**
Chromecast, Snapcast and ESPHome media players generally behave better. Sonos's local API is the awkward one.

**Can I pre-announce with a custom chime?**
Yes — `use_pre_announce` and a custom sound in MA's settings.

**Volume restores to the wrong level.**
MA sets and restores; an interrupted announcement can leave the announce volume applied. Re-set it manually.

**Multiple simultaneous announcements?**
They queue. A flood of doorbell events produces a backlog that plays out afterwards — rate-limit in your automation.
