---
title: "Audiobookshelf Progress Not Syncing Between Devices? Downloads Are the Culprit"
slug: audiobookshelf-progress-not-syncing
meta_description: "Listening position doesn't carry across phone, car and web in Audiobookshelf. Why downloaded items keep progress local, the Bluetooth gap, and how to force a sync."
updated: October 2026
cluster: round 10 (tech) — GitHub issues and discussions only
competition: LOW
---

# Audiobookshelf Progress Not Syncing Between Devices? Downloads Are the Culprit

You listen on your phone in the car, open the web player at your desk, and it's half an hour behind. Or the app briefly shows the right position, then jumps back to an older one.

**The pattern behind most of this: downloaded items keep their progress locally, and local progress doesn't reliably push back to the server.**

## 1. Downloaded vs streamed items

This is the core issue, documented in the project's own issue tracker:

- When a book is **downloaded** to the device, playback progress is saved **to the local item**
- Reconnecting shows the server-synced position briefly, then **jumps to the local position**
- That local progress **does not** sync up to the server, so other devices never see it

Practical consequences:
- If you want progress to follow you across devices, **stream** rather than download
- If you must download (no signal, car use), accept that the **device you downloaded on is the source of truth** until you deal with the local item
- Reported workaround: use **"delete local item"** after finishing, which pushes/clears the local state so the server position takes over

Decide per use case rather than fighting it: download for a commute on one device, stream when you switch around.

## 2. The race when you switch devices

Open the app and it continues from **its own last local position** instead of fetching the server's. If the server was ahead, you lose your place.

Before listening on a device you haven't used in a while:
- Open the app and let it **finish connecting** to the server before pressing play
- Pull-to-refresh the item / library
- Check the item's position matches what you expect **before** starting playback, because playing immediately writes the stale position forward

## 3. Bluetooth and the car

Specifically reported for podcasts and car use: progress played **over Bluetooth** doesn't sync correctly to the server, and when you open the app after disconnecting, it shows a lost connection — then syncs some minutes later once the app has been open and reconnected.

What helps:
- **Leave the app open and in the foreground** for a minute after you get home, on Wi-Fi, so it can reconnect and flush
- Don't force-quit the app straight after a drive — that's when pending progress is lost
- Treat the car session as "will sync when the app next talks to the server", not instantly

## 4. Connectivity and background limits

- On **iOS**, background execution is limited; sync happens when the app is foregrounded or in a granted background window
- Battery optimisation on **Android** can kill the app's background sync — exclude Audiobookshelf from battery optimisation
- **Reverse proxy timeouts** can break the sync calls while leaving streaming working. Check your proxy's read/send timeouts and that WebSockets pass through
- A **self-signed certificate** the app silently refuses on some endpoints

## 5. One account, multiple listeners

Progress is **per user**. Two people sharing one account overwrite each other constantly, and it looks exactly like a sync bug.

Give each listener their own user. (Shared progress across users is an open feature request, not current behaviour.)

## Forcing a sync

In rough order of disruption:

1. **Foreground the app on Wi-Fi** and wait
2. **Pull-to-refresh** the library / item
3. Open the **web player** and check the server-side position — that tells you which side is behind
4. **Log out and back in** on the lagging device
5. **Delete the local (downloaded) item** once you're sure the server has the position you want
6. Clear the app's cache/data as a last resort (you'll re-download everything)

Always check the web player first. It shows the server's truth, which turns a guessing game into a one-way problem.

## FAQ

**Should I download or stream?**
Stream if cross-device position matters. Download for offline listening and accept local progress.

**Why does the app jump backwards after showing the right position?**
It loaded the server position, then the local downloaded item's position overrode it.

**Do podcasts behave differently?**
Yes — podcast progress sync has its own reported problems, especially over Bluetooth.

**Can two people share one account and both keep their place?**
No. Create separate users.
