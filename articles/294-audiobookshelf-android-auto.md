---
title: "Audiobookshelf Not Working in Android Auto? Open the App on the Phone First"
slug: audiobookshelf-android-auto
meta_description: "Blank screens, a stuck Downloads tab, or missing Continue and Currently Listening. What's a known bug, what's the connection order, and the launcher setting people miss."
updated: October 2026
cluster: round 12 (tech) — Audiobookshelf app GitHub issues only
competition: LOW
---

# Audiobookshelf Not Working in Android Auto? Open the App on the Phone First

Several distinct Android Auto problems are reported, and some of them are known bugs rather than anything you configured wrong.

## 1. Open the app on the phone before you plug in

Documented behaviour: if you connect to Android Auto **without opening Audiobookshelf on the phone first**, you get an empty Downloads screen instead of your library, because the app hasn't connected to the server yet.

The working routine:
1. Open Audiobookshelf **on the phone** (background is fine)
2. Confirm it has connected to the server
3. Then connect to the car

Several people report only downloaded podcasts being visible otherwise, with no way to stream from the server.

## 2. The app isn't in the Android Auto launcher

Reported fix for the app not showing at all: add it via **phone Settings → Apps → Android Auto → Customise launcher**, and make sure Audiobookshelf is enabled there.

While you're in Android Auto settings:
- **Developer settings → Unknown sources** must be on if you installed from a source other than the Play Store (F-Droid, a GitHub APK)
- Some ROMs reset these after an Android update

## 3. Stuck on the Downloads screen

Documented bug: the app sometimes opens in Android Auto **stuck on Downloads with no way to navigate back**, and you have to pick something on the phone to get out.

Workarounds while it's unfixed:
- Start playback **on the phone** before driving; the car then shows Now Playing
- Keep a couple of **downloaded** items so the Downloads tab is at least usable
- Update the app — these navigation bugs get fixed, then sometimes return

## 4. "Continue" and "Currently Listening" tabs disappeared

Also a reported regression after an app update: those tabs vanish and only Browse and Downloads remain.

- Check the app's **GitHub issues** for your version
- **Roll back** the app version if those tabs matter to you (keep an APK of a version that worked)
- Report it with your version number — the maintainer is responsive and these get fixed

## 5. Progress sync and downloads

Worth knowing because it compounds the confusion in a car:

- **Downloaded** items keep progress **locally**, and local progress doesn't reliably sync back to the server. Listen on one device, or stream
- Podcast progress over **Bluetooth** has its own reported sync problems; the app needs to be foregrounded on Wi-Fi afterwards to flush
- **Don't force-quit** the app after a drive — that's when pending progress is lost

## 6. Connection basics

- Server reachable from the phone's **mobile data**, not just home Wi-Fi, if you want streaming in the car (that means a public hostname or a VPN like Tailscale)
- **Self-signed certificates** often fail silently in the Android Auto context
- **Battery optimisation**: exclude Audiobookshelf, or Android kills it mid-drive
- Server and app **versions in step**

## 7. Android Auto itself

Before blaming Audiobookshelf:
- Does **another media app** work in the car right now?
- Update **Android Auto** and Google Play Services
- Clear Android Auto's cache, re-pair the phone
- Try a **different USB cable** (a data cable, short, ideally the one that came with the phone) — wired Android Auto is very cable-sensitive

If no media app works, it's Android Auto.

## Prevention

1. Routine: **open the app, then connect**
2. Audiobookshelf enabled in the **Android Auto launcher**
3. **Battery optimisation off** for the app
4. Keep an **APK of a known-good version**
5. Stream rather than download if you move between devices

## FAQ

**Why do I only see Downloads?**
The app hadn't connected to the server before Android Auto started. Open it on the phone first.

**Can I get my place back after listening in the car?**
Leave the app open on Wi-Fi for a minute afterwards so it can sync — and don't force-quit it.

**The tabs I used are gone.**
A reported app regression. Check the issues, roll back if needed.

**Nothing shows in the launcher.**
Enable it in Android Auto's Customise launcher, and allow unknown sources if you sideloaded the app.
