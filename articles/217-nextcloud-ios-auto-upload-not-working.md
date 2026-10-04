---
title: "Nextcloud Auto Upload Not Working on iPhone? The iOS Rules You're Fighting"
slug: nextcloud-ios-auto-upload-not-working
meta_description: "Nextcloud auto upload stops on iOS because of background limits, settings reset by app updates, and one corrupt photo stalling the queue. What actually keeps it running."
updated: October 2026
cluster: round 10 (tech) — GitHub issues and help.nextcloud threads only
competition: LOW
---

# Nextcloud Auto Upload Not Working on iPhone? The iOS Rules You're Fighting

Auto upload worked for a month, then quietly stopped. Or it uploads only when you open the app. Or it uploads new photos but never the 4,000 already on the phone.

All three have the same root: **iOS does not let third-party apps upload in the background the way you assume it does.** Nextcloud's iOS app is working within limits Apple's own Photos app doesn't have.

Work through this in order.

## 1. Background App Refresh — and what it really buys you

**Settings → General → Background App Refresh → on**, and **on for Nextcloud**. Also check Low Power Mode is off, because it suspends background refresh entirely.

But understand the ceiling: iOS grants background time **opportunistically**, in short windows, based on how often you use the app, battery level, and whether you're on Wi-Fi and charging. There is no "upload continuously in the background" mode available to the app. Expect bursts, not a stream.

The practical consequence: **plug the phone in, connect to Wi-Fi, open Nextcloud, and leave it open and untouched** on the screen for a while. That's when the queue actually drains. Locking the phone mid-upload is what most people do, and it's why it never finishes.

## 2. Your settings were reset by an app update

This has happened across multiple versions: an app update **resets auto-upload preferences** and nobody notices because the toggle looks fine.

Go into **Settings → Auto upload** in the app and re-check every value:
- Auto upload **on**
- The **target folder** (did it revert to a default?)
- **Upload photos** / **Upload videos** both on if you want both
- **Only on Wi-Fi** — if on, confirm you actually are on Wi-Fi
- **Create subfolders**, filename behaviour, HEIC conversion

Toggle auto upload **off and on again** after any app update. It re-registers the observer.

## 3. The backlog needs "upload all existing"

Auto upload means *from now on*. Photos taken before you enabled it are not in scope unless you explicitly trigger the bulk option in the app (it's a separate action, and it's slow).

For a large existing library, the realistic route is the **desktop client** with the photos imported to a computer once, then let auto upload handle everything new.

## 4. One bad file stalls the whole queue

A recurring report: uploads stop partway through and never resume. The cause is often a **single media item the app can't read** — a partially-downloaded iCloud asset, a corrupt video, a shared-album item, or something in a format the uploader chokes on.

- Check the app's **upload/activity list** for a file stuck at the top
- **Remove or skip** that item (deleting the problem file from the camera roll has fixed it for people)
- Then restart the upload

## 5. iCloud Photos "Optimise iPhone Storage" is a trap

If your library is optimised, full-resolution originals live in iCloud and the phone holds thumbnails. The app has to **download each original before it can upload it** — over the network, within a background window. Large libraries never finish this way.

For a big backfill: **Settings → Photos → Download and Keep Originals** (if you have the space), or do the backfill from a computer.

## 6. Permissions and keep-awake details

- **Settings → Nextcloud → Photos: Full Access** (not "Limited" — limited access silently hides most of the library)
- **Local Network** permission on, if you reach your server by LAN address
- **Auto-Lock** set longer while doing a big upload: Settings → Display & Brightness → Auto-Lock
- Keep the phone **unlocked, charging, on Wi-Fi** for the big runs

## 7. Server-side causes that look like client bugs

- **Maintenance mode** on the server rejects uploads; the client reports a generic failure
- **Quota full** — check your user quota, not the disk
- **Reverse proxy upload limits** (`client_max_body_size` in nginx, equivalent in Caddy/Traefik) — videos fail while photos succeed, which is the signature of a size limit
- **PHP limits** (`upload_max_filesize`, `post_max_size`, timeouts) on the server
- **Cloudflare proxy** in front of Nextcloud has a request size limit on free plans; large videos die there
- A **token/session expiry** loop — sign out of the app and back in with a fresh app password

## What not to do

- Don't uninstall the app to "reset" it before checking the above — you lose the local upload state and any queued items
- Don't rely on auto upload as your only backup. Until a photo appears on the server, it exists in one place

## FAQ

**Does Nextcloud auto upload work when the app is closed?**
Only within the short background windows iOS grants. For reliable progress, open the app on Wi-Fi and power.

**Why does it only upload when I open the app?**
That's the expected iOS behaviour for third-party apps, amplified if Background App Refresh or Low Power Mode is working against you.

**Why did it stop after an app update?**
Auto-upload settings have been reset by updates more than once. Re-check them and toggle the feature off and on.

**Large videos fail but photos work. Why?**
Almost always an upload size limit on the reverse proxy, PHP, or a CDN in front of the server.
