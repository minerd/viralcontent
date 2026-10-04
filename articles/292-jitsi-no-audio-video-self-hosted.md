---
title: "Self-Hosted Jitsi With No Audio or Video? It's Port 10000/UDP"
slug: jitsi-no-audio-video-self-hosted
meta_description: "People can join a Jitsi meeting but see and hear nothing. The JVB UDP port, NAT harvesting addresses, TURN fallback and the two-vs-three participant clue."
updated: October 2026
cluster: round 12 (tech) — Jitsi community forum and GitHub issues
competition: LOW
---

# Self-Hosted Jitsi With No Audio or Video? It's Port 10000/UDP

Everyone joins the room, sees each other's names, and there's no media. In a self-hosted install this is nearly always **the videobridge's media port**.

## 1. Port 10000/UDP

**JVB (the videobridge) needs UDP 10000 reachable from the internet.** Signalling runs over 443 (which works, hence everyone joining), but media runs over UDP 10000 — and that's what's missing.

- Open **10000/UDP** in the host firewall **and** forward it on your router
- It is **UDP**, not TCP. This is the single most common mistake
- Cloud instances: open it in the **security group** too
- Docker: publish it (`- '10000:10000/udp'`)

Test from outside:
```bash
nc -zvu your.jitsi.domain 10000
```

## 2. The two-vs-three participant clue

A diagnostic worth knowing: with **two** participants, Jitsi can sometimes connect peer-to-peer and media works. Add a **third** and everything routes through JVB — and if JVB's media path is broken, media fails for everyone.

So "works with two people, breaks with three" means **JVB**, not your clients. (You can disable P2P to test with two.)

## 3. NAT: JVB must advertise the right addresses

Behind NAT, JVB has to tell clients its **public** address as well as its private one. In `/etc/jitsi/videobridge/sip-communicator.properties`:

```
org.ice4j.ice.harvest.NAT_HARVESTER_LOCAL_ADDRESS=10.0.0.5
org.ice4j.ice.harvest.NAT_HARVESTER_PUBLIC_ADDRESS=203.0.113.10
```

Without these, clients receive candidates they can't reach, ICE fails, and you get exactly this symptom. In the Docker setup the equivalents are `JVB_ADVERTISE_IPS` / `DOCKER_HOST_ADDRESS`.

A **dynamic public IP** that changed since install breaks this silently — re-check the value.

## 4. TURN fallback for restrictive networks

If it works for you and fails for a participant on a corporate or mobile network, UDP is being blocked at their end. Jitsi's answer is **TURN over TCP/443** (coturn, which the standard install sets up):

- Confirm coturn is running and reachable on **443/TCP**
- Check the TURN credentials and realm in the prosody/JVB config
- Without working TURN, UDP-blocked users will never get media

## 5. Read the right log

```bash
journalctl -u jitsi-videobridge2 -f
tail -f /var/log/jitsi/jvb.log
tail -f /var/log/jitsi/jicofo.log
tail -f /var/log/prosody/prosody.log
```

- `videobridgeNotAvailable` in the browser → JVB isn't registered with jicofo. That's a **prosody/JVB auth** problem (the `JVB_AUTH_PASSWORD` must match), not a port problem
- ICE failures in jvb.log → section 1 or 3
- Nothing in jvb.log when a call starts → JVB never got the conference; check jicofo

## 6. After an upgrade specifically

- Config files are **replaced** by package upgrades: your NAT harvester lines and auth passwords can be reverted. Diff them against your notes
- Component **passwords** must match across prosody, jicofo and JVB; an upgrade that regenerated one breaks registration
- Reported: previously working setups losing video/audio/sharing after an upgrade, with "the video server bridge has disconnected" — that's registration, not media

## 7. Client-side quick checks

- Browser **permissions** for camera/microphone; test on `meet.jit.si` to prove the browser works
- Reported: `config.startAudioOnly=true` in the URL getting audio working, which points at a video-only failure (bandwidth/codec)
- Clear browser cache; a stale `config.js` after an upgrade is real
- Safari and in-app browsers are the least reliable clients

## Prevention

1. **10000/UDP** open and forwarded, documented
2. **NAT harvester addresses** set, and re-checked when your public IP changes
3. **coturn working on 443** for restricted networks
4. Keep a copy of your **config files and component passwords** before upgrading
5. Test with **three participants**, not two, after any change

## FAQ

**Signalling works but no media. Why?**
They use different paths: 443/TCP for signalling, 10000/UDP for media.

**Works with two people, not three.**
P2P covered the two-person case. JVB's media path is broken.

**One participant has no media, everyone else is fine.**
Their network blocks UDP. You need working TURN on 443.

**My config reverted after an upgrade.**
Package upgrades replace config files. Keep your customisations noted and re-apply them.
