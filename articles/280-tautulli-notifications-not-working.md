---
title: "Tautulli Notifications Not Triggering? Conditions, Not Agents"
slug: tautulli-notifications-not-working
meta_description: "Test notifications work but real events don't fire. Playback-stop filtering, 'Not notifying again', recently-added timing and the force-refresh fix."
updated: October 2026
cluster: round 12 (tech) — Tautulli GitHub issues and docs
competition: LOW
---

# Tautulli Notifications Not Triggering? Conditions, Not Agents

If the **Test** button delivers, your notification agent is fine. The problem is in **triggers and conditions** — which is where almost all of these live.

## 1. Force-refresh the settings page

Documented first step, and it sounds too simple to matter: do a **hard refresh** (Ctrl+F5, or Option+Reload on Safari) of the Tautulli settings page, then re-save and test. A stale frontend can display a configuration the server doesn't actually hold.

Do this before debugging anything else; it costs five seconds.

## 2. Playback Stop is filtered on purpose

Tautulli deliberately **suppresses Playback Stop notifications once the watched threshold is passed**, so you don't get both a "watched" and a "stopped" notification at the end of every stream.

If you specifically want a stop notification at the end of playback:
- Use the **Watched** trigger instead, or
- Lower the watch-completed threshold in settings, or
- Add your own condition logic rather than fighting the default

This is the single most common "my notification doesn't fire" case.

## 3. "Not notifying again" in the log

Tautulli logs this when it has already notified for that item/session. Causes:

- **Recently Added** notifications fire once per item. A re-scan or a metadata refresh doesn't make it new again
- The item was **added while Tautulli was down**, and the recently-added window has passed
- Your `notify_recently_added_delay` hasn't elapsed — Plex often reports an item before its metadata is complete, and Tautulli waits deliberately. Too short a delay means notifications with missing artwork; too long means they look late

Check **Settings → Notifications → Recently Added** for both the delay and the upgrade behaviour.

## 4. Conditions are doing exactly what you wrote

Open the notification agent → **Conditions** tab. Every condition must pass.

Classic self-inflicted ones:
- `Library Name` **is** something that doesn't match exactly (case, trailing space)
- `Media Type` set to `movie` while you're testing with an episode
- A `User` condition that doesn't include the account actually streaming
- Conditions combined with **and** when you meant **or**

The notification log (**Settings → Notifications → Notification Logs**, plus the main logs at debug level) shows which condition rejected the event. That removes all guesswork.

## 5. Version regressions

Reported for specific releases: notifications failing with thread exceptions in `NotificationHandler`, including date-format parsing problems that broke Recently Added.

- Check **Settings → Help & Info** for your version
- Look at the **GitHub issues** for that version plus "notification"
- Update, or roll back if an update caused it
- Tautulli's own logs print the traceback — that's the thing to search for

## 6. Plex-side prerequisites

- Tautulli needs **webhooks/activity** from Plex; if the connection drops, nothing triggers. Check the server status in Tautulli's header
- **Plex remote access** or a changed server URL/token after a Plex update
- Library sections **not monitored** in Tautulli's settings
- For a brand-new library, Tautulli needs to have **scanned** it

## Diagnosing in order

1. **Hard refresh**, re-save, test
2. **Notification Logs** — did the event arrive and get rejected, or never arrive?
3. If never arrived: **Plex connection** and monitored libraries
4. If rejected: **conditions** and the stop/watched filtering
5. If a traceback: **version issue**

## Prevention

1. Keep notifications **simple**: fewer conditions, clearer triggers
2. Use **Watched** rather than Playback Stop for end-of-stream alerts
3. Note your **recently-added delay** and why you chose it
4. **Pin the image tag**
5. Keep one **test notification** agent you can fire safely

## FAQ

**Why do I get no notification when a stream ends?**
Playback Stop is filtered after the watched threshold. Use the Watched trigger.

**What does "Not notifying again" mean?**
Tautulli already notified for that item. Re-scans don't reset it.

**Test works but nothing real fires.**
Conditions, triggers, or the Plex event never arriving. The notification logs tell you which.

**Should I raise the recently-added delay?**
If notifications arrive without artwork or metadata, yes — a minute or two is common.
