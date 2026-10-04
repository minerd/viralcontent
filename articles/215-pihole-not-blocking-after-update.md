---
title: "Pi-hole Stopped Blocking Ads After an Update? Work Through These in Order"
slug: pihole-not-blocking-after-update
meta_description: "Pi-hole showing queries but no blocks after an update usually means FTL isn't running, adlists are empty after a migration, or clients are bypassing DNS over IPv6 or in-browser."
updated: October 2026
cluster: round 9 (tech) — Pi-hole discourse threads only
competition: LOW
---

# Pi-hole Stopped Blocking Ads After an Update? Work Through These in Order

The pattern after any significant Pi-hole update: the admin page loads, queries appear in the log, and **nothing gets blocked**. Almost always one of six things.

## 1. Is FTL actually running?

`pihole-FTL` is the DNS engine. If it isn't up, Pi-hole answers nothing and your devices quietly fall back to another DNS server.

```
pidof pihole-FTL
sudo service pihole-FTL status
sudo service pihole-FTL restart
```

Also run the built-in checks:
```
pihole status
pihole -d        # debug log, generates a token you can share on the forum
```

## 2. Are there any adlists left?

Major version migrations have reset or failed to carry over lists and group assignments. **No adlists = no blocking**, and the dashboard looks perfectly healthy.

- Admin → **Lists**: are there enabled adlists?
- Admin → **Groups / Group management**: are lists and clients assigned to a group that's enabled?
- Then rebuild the gravity database:
```
pihole -g
```
Check the gravity count on the dashboard afterwards — "Domains on Adlists: 0" is your answer.

## 3. Are clients actually using Pi-hole?

The most common real-world cause, update or not. Test from a client:

```
nslookup doubleclick.net        # should return your Pi-hole's answer / 0.0.0.0
nslookup doubleclick.net 1.1.1.1
```
If the first returns a real ad-network address, the client isn't using Pi-hole at all.

Then check:
- Your **router's DHCP** still hands out the Pi-hole as the **only** DNS server. A router firmware update or factory default can silently restore the ISP's DNS as a secondary — and clients will use it
- Any **secondary DNS entry** (8.8.8.8 as a backup defeats the whole thing)
- Devices with **static DNS** set by hand
- A **VPN** on the client, which carries its own DNS

## 4. IPv6 is bypassing it

If your router advertises **its own IPv6 address** as a DNS server, clients happily resolve over IPv6 and never touch Pi-hole. This breaks blocking in a way that looks exactly like "Pi-hole stopped working".

Options:
- Configure the router to advertise the **Pi-hole's IPv6 address** instead (and make sure Pi-hole is listening on it)
- Or disable IPv6 RDNSS advertisement
- Or disable IPv6 on the LAN if you don't need it

## 5. The browser is doing its own DNS

Chrome, Edge and Firefox can use **DNS-over-HTTPS** to a provider of their own, which routes around your network DNS entirely.

- Firefox: Settings → Privacy & Security → **DNS over HTTPS** → Off (or set to your own resolver)
- Chrome/Edge: Settings → Privacy → Security → **Use secure DNS** → off, or "with your current service provider"
- Apple devices can also use **iCloud Private Relay** and configured DoH profiles — both bypass Pi-hole

## 6. The thing you're seeing isn't DNS-blockable

Not every ad can be stopped at DNS:
- **YouTube ads** come from the same hostnames as the video
- First-party ads on big platforms (Facebook, Instagram, Twitch) serve from the same domain as the content
- Apps with hardcoded IPs skip DNS

If blocking "stopped working" only on one site or app, this may be it — and no update changed anything.

## Quick diagnosis table

| Symptom | Check |
|---|---|
| No queries in the log at all | Clients aren't using Pi-hole (router DHCP / static DNS) |
| Queries logged, zero blocked | Empty adlists / gravity not built / group assignment |
| Admin page down, DNS down | FTL not running |
| Some devices blocked, others not | Secondary DNS, IPv6, VPN, or browser DoH |
| Only one site unblocked | Not DNS-blockable |

## FAQ

**Does updating Pi-hole wipe my blocklists?**
It shouldn't, but major version migrations have left people with empty or unassigned lists. Check Lists and Groups and run `pihole -g`.

**Should I set a secondary DNS server on my router?**
No — clients will use it and bypass blocking. If you want redundancy, run a second Pi-hole.

**Why is one laptop still seeing ads?**
Static DNS, a VPN, or browser DNS-over-HTTPS. Test with `nslookup` on that machine.

**Is `pihole -d` safe to share?**
It generates a debug token for the forum. Review what you post; it contains network details.
