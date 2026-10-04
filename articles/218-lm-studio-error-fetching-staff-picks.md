---
title: "LM Studio 'Error Fetching Staff Picks'? Load Models the Manual Way"
slug: lm-studio-error-fetching-staff-picks
meta_description: "LM Studio can't reach its model catalogue: what the staff-picks error means, the network causes behind it, and how to import a GGUF by hand so you can keep working."
updated: October 2026
cluster: round 10 (tech) — one GitHub issue; the rest of the SERP is unrelated
competition: LOW
---

# LM Studio 'Error Fetching Staff Picks'? Load Models the Manual Way

You open LM Studio, the Discover tab shows **"Error fetching staff picks"**, and model search returns nothing. Search the web for it and you get Wikipedia pages and Etsy threads — there's essentially one GitHub issue about it.

**The error means the app can't reach its model catalogue.** The app itself is fine; the network path to the catalogue and to Hugging Face isn't. Your locally installed models still run.

## Why it happens

LM Studio's Discover tab queries LM Studio's own catalogue service and **Hugging Face** for model metadata. Anything between you and those endpoints breaks that call:

- **Corporate network / proxy** that intercepts TLS, or a proxy LM Studio isn't configured for
- **VPN** (some exits are blocked or rate-limited by Hugging Face)
- **Firewall, antivirus or endpoint protection** blocking the app's outbound requests
- **DNS-level blocking** — a Pi-hole/AdGuard list, or a DoH resolver the app doesn't use
- **Country/region restrictions** on Hugging Face
- A **server-side outage** or rate limit on their end
- An **old app version** calling an endpoint that moved

## Work through it in order

1. **Check your own connectivity to the sources.** Open `huggingface.co` in a browser on the same machine. If that fails too, it's the network, not the app.
2. **Turn a VPN off — or on.** Both directions fix it for different people. If your exit IP is rate-limited by Hugging Face, switching regions is the fastest test.
3. **Restart the app**, then the machine. Transient DNS and socket state cause one-off failures.
4. **Update LM Studio.** The reported case was on a specific version; catalogue endpoints change.
5. **Allow it through your firewall/AV** explicitly, by executable. On corporate machines, endpoint protection is the single most likely culprit.
6. **Check your DNS filter.** A blocklist entry for a CDN domain can break model metadata while leaving the rest of the internet intact. Look at your Pi-hole/AdGuard query log while you click Discover — the blocked request will be right there.
7. **Proxy settings:** if your network requires one, make sure the app's environment has `HTTPS_PROXY` set, and that the proxy's CA is trusted by the system.

## The workaround that always works: import a GGUF by hand

You do not need the Discover tab to use LM Studio.

1. Download a **`.gguf`** file from Hugging Face in a browser (the model's Files tab) — pick a quantisation that fits your RAM/VRAM
2. Find LM Studio's **models directory** (shown in My Models → the folder path; it's configurable in settings)
3. Create the expected folder structure: **`<publisher>/<model-name>/<file>.gguf`**
4. Restart LM Studio, or hit refresh in **My Models**
5. The model appears and loads normally

This is also the better route on a machine with no direct internet access: download on another machine, copy the file across.

The **`lms` CLI** is another path if the GUI's catalogue is unreachable but the machine has general connectivity.

## Related errors, different causes

| Error | Likely cause |
|---|---|
| **Error fetching staff picks** / search empty | Network path to the catalogue — this article |
| **Failed to load model** (exit code) | RAM/VRAM, a bad download, or an unsupported quant — not a network issue |
| **Error surveying hardware** | GPU driver or runtime detection problem |
| Model **unloads itself** after a while | Idle TTL / auto-evict setting, not an error |

## FAQ

**Can I still use models I've already downloaded?**
Yes. The error only affects browsing and downloading new ones.

**Is my installation broken?**
No. Nothing local is wrong; the app can't reach a remote service.

**How do I know what folder structure to use?**
Mirror what existing models look like in your models directory: a publisher folder, a model folder, then the `.gguf` file.

**Does this happen because Hugging Face is down?**
Sometimes. Check their status before rebuilding your network config.
