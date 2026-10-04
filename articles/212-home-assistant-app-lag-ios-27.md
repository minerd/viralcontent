---
title: "Home Assistant App Slow on iOS 27? It's HTTP, Not Your Server"
slug: home-assistant-app-lag-ios-27
meta_description: "Dashboards that loaded instantly now crawl after iOS 27. The cause is a WebKit security process applied to plain-HTTP pages on LAN addresses — and there are two real fixes."
updated: October 2026
cluster: round 9 (tech) — GitHub issues and the HA community forum only
competition: LOW
---

# Home Assistant App Slow on iOS 27? It's HTTP, Not Your Server

Classic symptoms: you update an iPhone or iPad to **iOS 27**, and the Home Assistant companion app goes from instant to **several seconds per dashboard** — blank tile cards first, then icons, then text. Devices still on iOS 26 are fine. Your server is healthy, your LAN is healthy, re-registering doesn't help.

**It isn't your server, your Wi-Fi, or your dashboard.** It's how iOS 27 treats pages served over **plain HTTP**.

## What's actually happening

iOS 27 renders pages loaded over **http://** in a hardened WebKit process (`WebContent.EnhancedSecurity`). That process is deliberately slower — it gives up JIT-level performance for security hardening.

The important detail: WebKit **exempts loopback** from that treatment, but **not private LAN addresses**. So:

- `http://192.168.x.x:8123` → hardened process → slow, janky dashboards
- `https://...` → normal process → fast

That's why only the app is slow while Safari over your external HTTPS URL feels fine, and why nothing you change on the Home Assistant side makes any difference.

## Fix 1: use HTTPS (the real fix)

Serve Home Assistant over **HTTPS** and the problem disappears, because the hardened path doesn't apply. Common ways, in rough order of how much work they are:

- **Home Assistant Cloud (Nabu Casa)** — HTTPS with no configuration
- A **reverse proxy** (Caddy, NGINX Proxy Manager, Traefik) with a Let's Encrypt certificate on a real domain, plus **split-horizon DNS** so the same hostname resolves to your LAN IP at home
- **Tailscale / WireGuard** with an HTTPS endpoint
- A certificate on the HA instance itself and a local hostname

A plain self-signed certificate on an IP address is the fiddly option — iOS is strict about trust, and you'll be installing and trusting a profile on every device.

The split-horizon DNS version is worth the effort: one URL that works at home and away, fast on both.

## Fix 2: the app's built-in workaround

The companion app added a workaround for exactly this: when a configured server uses plain HTTP, it **disables the WebKit heuristic** before building its web view. It's on by default, with a toggle in the app's **Settings → General**.

So:

1. **Update the companion app** — this is the first thing to do
2. Confirm the workaround is enabled (and if you're debugging, try it off/on to see the difference)
3. Restart the app fully after updating

If you're still slow after updating, you're probably hitting one of the other issues below rather than this one.

## Other things that look the same

- **WebSocket reconnect/subscription races** on iOS 27 have their own reported slowdown; update the app and check the GitHub issues for your version
- **Heavy dashboards**: dozens of cards, big camera streams, custom cards doing work on every state change. Test with a minimal dashboard to isolate it
- **A genuinely busy server** — check the system health page and the recorder database size
- **Mixed content**: an HTTPS dashboard pulling an HTTP camera stream behaves badly

## How to confirm it's this bug in two minutes

1. Open the **same dashboard in Safari over HTTPS** (external URL or Nabu Casa). Fast?
2. Open it in **Safari over `http://lan-ip:8123`**. Slow?
3. If the answer is yes/yes, you have the HTTP hardening problem, not a Home Assistant problem.

## FAQ

**Will downgrading iOS fix it?**
Not a practical option, and not necessary — HTTPS or the updated app fixes it.

**Is HTTP on my own LAN really a problem?**
From iOS 27's point of view, yes: it can't distinguish your LAN from a hostile one, so it applies the hardened path. Moving to HTTPS is the durable answer regardless.

**Does this affect the Android app?**
No. This is a WebKit/iOS behaviour.

**My dashboard is slow in the browser too, over HTTPS.**
Then it's dashboard or server load, not this bug. Strip the dashboard back and add cards until it slows down.
