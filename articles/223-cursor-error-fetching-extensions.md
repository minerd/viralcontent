---
title: "Cursor 'Error While Fetching Extensions. XHR Failed'? What's Blocking It"
slug: cursor-error-fetching-extensions
meta_description: "Cursor can't reach the extension marketplace: firewalls, VPNs, corporate TLS inspection and rate limiting. The checks in order, plus installing a VSIX by hand."
updated: October 2026
cluster: round 10 (tech) — Cursor community forum threads only
competition: LOW
---

# Cursor 'Error While Fetching Extensions. XHR Failed'? What's Blocking It

Open the Extensions panel in Cursor and you get **"Error while fetching extensions. XHR failed"** — search returns nothing, installs fail. Every result for this is a thread on Cursor's own forum.

**The editor can't complete an HTTPS request to the extension service.** That's a network problem in almost every case, and the list of suspects is short.

## 1. Rate limiting (try this first, it's free)

Searching repeatedly, or typing a query letter by letter, triggers a **server-side rate limit**. The reported trick that works for most people:

> Copy the extension name, **clear the search box completely**, then paste it in one go and press Enter.

One request instead of fifteen. If that works, nothing is wrong with your setup.

## 2. Firewall, antivirus and endpoint protection

The most common real cause. Security software intercepts or blocks the editor's outbound requests. **McAfee** blocking `cursor-cdn.com` is specifically reported.

- Add the **Cursor executable** to your firewall's allowed applications (Windows Defender Firewall → Allow an app)
- In third-party AV, add Cursor to **web/HTTPS scanning** exclusions, not just file scanning
- Temporarily **pause** the AV to confirm the diagnosis — then re-enable it and add a proper exception rather than leaving it off

## 3. VPN — off, or on

Both directions fix it for different people:

- **On a VPN?** Turn it off. Some exits are blocked or rate-limited
- **Not on one?** Turn one on. If your ISP's DNS or a transparent proxy is the problem, tunnelling past it works
- **Split tunnelling**: exclude Cursor, or include it, depending on which side is broken

## 4. Corporate networks: Zscaler, proxies and TLS inspection

On a work machine this is nearly always it. TLS-inspecting proxies re-sign traffic with a corporate CA, and the editor rejects the certificate.

- Make sure the **corporate root CA** is in the system trust store **and** that Cursor is using the system store
- Set `"http.proxy"` in settings, and `"http.proxySupport"` appropriately
- As a diagnostic only, `"http.proxyStrictSSL": false` tells you whether certificate validation is the blocker. Don't leave it off
- Ask whether `marketplace.visualstudio.com`, `*.vsassets.io`, `*.gallerycdn.vsassets.io` and `cursor-cdn.com` are allowed through
- Try a **personal hotspot** for sixty seconds. If it works there, the conversation is with IT, not with Cursor

## 5. DNS and local blocking

- A **Pi-hole/AdGuard** blocklist entry for a CDN domain breaks extension fetching while the rest of the internet is fine. Watch the query log while you click Extensions
- Switch DNS to **1.1.1.1 / 8.8.8.8** as a test
- Flush the resolver cache (`ipconfig /flushdns`, `sudo dscacheutil -flushcache`)
- Check `hosts` for stale entries

## 6. The editor itself

- **Update Cursor.** Endpoints and the bundled VS Code base change
- **Restart** fully, not just reload the window
- **Unsupported OS**: Windows 7 and other EOL systems are out of support upstream; extension fetching is one of the first things to break
- A corrupt extensions directory: back up and move `~/.cursor/extensions` aside, then restart

## Workaround: install from a VSIX

You don't need the marketplace panel:

1. Download the extension's **`.vsix`** from the Visual Studio Marketplace page (Download Extension link) on any machine that can reach it
2. In Cursor: **Extensions panel → … menu → Install from VSIX…**, or `cursor --install-extension path/to/file.vsix`
3. Note that updates won't come automatically — you'll re-download when you want a newer version

This is also how you work on an air-gapped machine.

## FAQ

**Is this a Cursor outage?**
Sometimes, but check the local causes first: firewall, VPN, proxy and rate limiting account for most reports.

**Why do Anysphere's own extensions fail too?**
Same transport. If the fetch path is blocked, everything in the panel fails together.

**Does VS Code work while Cursor doesn't?**
That points at a per-application firewall rule or a missing exception for the Cursor executable.

**Can I use VS Code extensions in Cursor?**
Yes — including via VSIX, which is the practical answer while the panel is broken.
