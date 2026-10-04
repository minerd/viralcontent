---
title: "Grocy Barcode Scanner Not Working? The Camera Needs HTTPS"
slug: grocy-barcode-scanner-not-working
meta_description: "Camera-based barcode scanning in Grocy only works over HTTPS. Why the browser blocks it, how to get a certificate on a LAN instance, and the manual-entry fallback."
updated: October 2026
cluster: round 12 (tech) — Grocy GitHub issues and HA community
competition: LOW
---

# Grocy Barcode Scanner Not Working? The Camera Needs HTTPS

You tap the barcode button, a window opens, and nothing happens — or the browser never asks for camera permission at all.

**The answer is almost always HTTPS.** Browsers treat the camera as a powerful feature and only expose it on **secure origins**. Over plain `http://grocy.local:9283` the API simply isn't available, so Grocy's scanner can't start and there's no permission prompt to accept.

## Confirm it in ten seconds

Open the browser console on the Grocy page and run:

```js
navigator.mediaDevices
```

- `undefined` → insecure origin. That's your problem
- An object → the API exists; continue to the other causes below

(`localhost` is treated as secure, which is why it works when you test on the machine itself and fails from your phone.)

## Fixing it

**Option 1 — reverse proxy with a real certificate (best)**
Put Grocy behind Caddy, nginx or Traefik with a Let's Encrypt certificate on a real domain. With **split-horizon DNS** the same hostname works at home and away. Caddy makes this three lines:

```
grocy.example.com {
    reverse_proxy grocy:80
}
```

**Option 2 — Cloudflare Tunnel**
Also serves HTTPS, with no inbound ports, and is a documented working route for exactly this.

**Option 3 — Tailscale / WireGuard with HTTPS**
Tailscale can issue certificates for your tailnet names, which gives you a secure origin without exposing anything.

**Option 4 — self-signed certificate**
Workable but fiddly: the certificate must be **trusted on every device**, including installing a profile on phones. Self-signed on an IP address is the worst case; use a hostname.

**Home Assistant users:** if you run the Grocy add-on, access it through HA's own HTTPS URL (Nabu Casa or your own certificate) rather than the direct port.

## Other causes, once HTTPS is sorted

- **Camera permission denied** for the site: check the browser's site settings and clear a previous "block"
- **iOS Safari** requires a user gesture and will not use the camera in some in-app browsers — open Grocy in Safari proper
- Another app holding the camera
- **Scanner library**: newer Grocy replaced Quagga2 with **ZXing**, which performs better and supports 2D codes (QR/DataMatrix). If you're on an old version with poor detection, updating is the fix
- Poor **lighting or focus** — ZXing is better but not magic; fill the frame with the barcode
- Barcode **type not supported** by the configured decoders

## When scanning still isn't practical

- **Type the barcode** manually — Grocy looks products up the same way
- Use a **USB/Bluetooth barcode scanner** as a keyboard-wedge device; it types into the focused field and needs no camera permission at all. For stock-taking this is faster than a phone anyway
- Use **Grocy's companion apps** on Android, which use the native camera rather than the browser API
- Check your **barcode lookup plugin** separately: a working scanner with no product data is a plugin or configuration problem, not a camera one

## Prevention

1. Serve **everything self-hosted over HTTPS** — this isn't the last app that will need it
2. Use a **real hostname** with split-horizon DNS rather than IPs
3. Keep Grocy **updated** for the ZXing scanner
4. Keep a **hardware scanner** around if you do big stock-takes
5. Test the camera on the **device you'll actually use**, not just your desktop

## FAQ

**Why does it work on my laptop but not my phone?**
`localhost` counts as secure; your phone reaches it over plain HTTP, which doesn't.

**Is a self-signed certificate enough?**
Only if every device trusts it. A real certificate is less work overall.

**Does it support QR codes?**
With the ZXing-based scanner in newer versions, yes.

**Can I avoid the camera entirely?**
Yes — manual entry, a USB barcode scanner, or the native mobile app.
