---
title: "TVHeadend EPG Empty: Grabbers, Channel Mapping and OTA"
slug: tvheadend-epg-empty
meta_description: "No programme data at all, or data in the UI that clients don't see. Which grabber to use, why channel names must match, and the EIT scan requirement."
updated: October 2026
cluster: round 13 (tech) — TVHeadend forum and GitHub
competition: LOW
---

# TVHeadend EPG Empty: Grabbers, Channel Mapping and OTA

An empty guide has exactly three possible causes: no data is being fetched, data is fetched but isn't matched to your channels, or data exists and your client isn't reading it. The **EPG Grabber Channels** tab tells you which — check it before anything else.

**Configuration → Channel/EPG → EPG Grabber Channels.** If this list is empty, no data arrived. If it has entries but none are mapped to a channel, that's the matching problem.

## 1. Pick one grabber and configure it properly

**Over-the-air (EIT/OTA)** — for DVB-T/T2, DVB-S/S2, DVB-C where the broadcaster sends EPG:

- **Configuration → Channel/EPG → EPG Grabber Modules** → enable **EIT: DVB Grabber** (and **UK: Freesat/Freeview** variants if relevant to your region).
- OTA EPG only arrives **while a tuner is parked on a multiplex**. With all tuners idle, nothing is collected. Set **Configuration → DVB Inputs → Networks → (network) → "Idle scan muxes"** on, or schedule a periodic mux scan.
- OTA typically provides only "now and next" plus a few days, depending on broadcaster. A thin guide from OTA is normal, not broken.

**XMLTV (external grabber)** — for IPTV, or where you want a longer, richer guide:

```bash
# the socket TVHeadend watches
/home/hts/.hts/tvheadend/epggrab/xmltv.sock
```

Push a file into it:

```bash
cat guide.xml | socat - UNIX-CONNECT:/home/hts/.hts/tvheadend/epggrab/xmltv.sock
```

Then enable **"XMLTV: External XMLTV"** in EPG Grabber Modules. The internal grabbers (`tv_grab_*`) are the older path and need the scripts installed in the container, which most images don't include — the socket approach is the one that works reliably in Docker.

Don't enable both OTA and XMLTV for the same channels unless you've set grabber priorities; conflicting data produces a guide that looks randomly wrong.

## 2. Channel names must match, or be mapped

This is where most empty guides actually come from. TVHeadend matches an EPG source channel to one of your channels by name or by an explicit mapping. Mismatches are silent.

In **EPG Grabber Channels**, each entry has a **Channels** field. Set it to your channel. Doing this by hand for 200 channels is painful, so:

- Make your channel names **exactly** match the XMLTV `display-name`, and TVHeadend matches automatically.
- Or, in your M3U, set `tvg-id` to the XMLTV channel id and let the playlist carry the mapping.

```
#EXTINF:-1 tvg-id="BBCOne.uk" tvg-name="BBC One" ,BBC One
```

Trailing spaces, "HD" suffixes and case differences all break automatic matching. If one channel has a guide and its neighbour doesn't, the name is the first thing to check.

## 3. Data in the UI but not in your client

- **Plex/Jellyfin via HTSP or HDHomeRun** read the guide from TVHeadend. If the UI's Electronic Program Guide tab has data and the client doesn't, the client is caching. Remove and re-add the guide source.
- **The client's channel numbers changed.** Re-mapping channels in TVHeadend renumbers them, and clients key on numbers. Re-run the client's channel scan after any channel change.
- **User permissions.** A TVHeadend user without EPG access rights gets channels and no guide. Check **Configuration → Users → Access Entries**: the streaming profile and the rights for that user/network.
- **Anonymous access.** If the client connects with no credentials and your access entry requires them, some clients fall back to a limited view rather than erroring.

## 4. Grabber runs but fetches nothing

```bash
# container log
docker logs tvheadend --tail 100 | grep -iE 'epggrab|xmltv|eit'
```

- **File permissions on the socket.** The process writing to it must be able to; `hts` owns the socket.
- **Cron pushing the XML at the wrong time** or to a path that doesn't exist after a container recreate. Put the socket path on a persistent volume.
- **XMLTV file invalid.** Validate it before pushing; TVHeadend logs a parse error and keeps the previous data, so a broken feed looks like a stale guide rather than an error.
- **Internal grabber selected but not installed.** Enabling `tv_grab_zz_sdjson` without the script present logs a failure every interval.

## What not to do

- **Don't enable every grabber module.** Multiple sources for the same channel without priorities produce incorrect listings that are hard to attribute.
- **Don't rename channels after clients are set up** unless you plan to re-scan them. Numbering changes break recordings.
- **Don't rely on OTA alone for a 7-day guide** if your broadcaster only sends two days. That's a broadcast limitation.
- **Don't clear the EPG database to fix matching.** The mapping is what's wrong, and you'll just wait for a re-fetch of the same unmatched data.

## Prevention

| Habit | Why |
|---|---|
| One grabber per channel set, with explicit priorities | Makes wrong listings attributable |
| `tvg-id` in playlists matching XMLTV ids | Automatic mapping, no manual work |
| Socket path on a persistent volume | Survives container recreation |
| Idle mux scanning on for OTA setups | Without it, OTA EPG is permanently thin |

## FAQ

**How far ahead should the guide go?**
XMLTV sources commonly give 7–14 days. OTA is usually 1–7 depending on broadcaster.

**Can I edit a single programme's data?**
No. Fix it at the source and re-push.

**Recordings fire at the wrong time.**
Check the timezone in the container and that your XMLTV times include offsets. A naive timestamp is interpreted as local, which breaks around DST changes.

**The guide disappears after a restart.**
EPG data lives in `epgdb.v3` in the config directory. If that's not on a persistent volume, every restart starts empty.
