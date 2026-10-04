---
title: "LM Studio Keeps Unloading Your Model? It's Idle TTL, Not a Bug"
slug: lm-studio-unloading-model
meta_description: "Models disappearing from memory in LM Studio are usually evicted by Idle TTL or the keep-only-last-JIT setting. Where those settings live and when it really is VRAM."
updated: October 2026
cluster: round 10 (tech) — GitHub bug-tracker issues and the docs, nothing joining them up
competition: LOW
---

# LM Studio Keeps Unloading Your Model? It's Idle TTL, Not a Bug

You load a model, use it, come back twenty minutes later — and it's unloaded. Or you're running LM Studio as a local server and the first request after a pause takes forever because the model has to load again.

**That's usually a setting doing exactly what it was told.** LM Studio documents the mechanism; nobody connects the symptom to the setting, which is why people file bugs.

## 1. Idle TTL — the main cause

**Idle TTL** is how long a model may sit in memory with **no requests** before it's unloaded. When the TTL expires, the model is evicted.

Where to change it:
- In the app's **server / developer settings**, per loaded model
- Via the API: a **TTL field** on the load/request call
- Via the **`lms` CLI** when loading a model

If you want a model to stay resident, set a long TTL or disable it. If you're on a laptop and want RAM back, a short TTL is the feature working as intended.

## 2. "Only keep last JIT-loaded model"

**JIT loading** loads a model on demand when a request names it. Alongside it there's a setting that keeps **only the most recently JIT-loaded model** in memory, so loading a second model evicts the first.

Symptoms: you serve two models from one LM Studio instance, and each request to model B kicks out model A. Turn that option off if you have the memory for both — and size your expectations: two 7B models at a chunky quant will not fit where one did.

There's also a reported bug where a **new JIT load cuts off a model that's still generating** — relevant if several clients hit the same server. If that's your situation, pre-load models explicitly rather than relying on JIT.

## 3. Genuine memory pressure

If the OS is short on RAM/VRAM, things get evicted whatever your settings say:

- **Model too large for VRAM** → partial offload, then eviction or crashes under load
- **Other GPU consumers**: a browser with hardware acceleration, a game, another local model, Docker with GPU access
- **macOS unified memory**: a large model plus a big context plus everything else, and the system starts reclaiming
- **Context length** is the hidden multiplier — KV cache grows with it. A model that loads fine at 4k context can be evicted at 32k

Check: GPU VRAM used vs total while loaded, system RAM, and whether the eviction correlates with a long conversation rather than with idle time. **Idle eviction = TTL. Eviction under load = memory.**

## 4. When it's the server, not the app

If you're calling LM Studio's OpenAI-compatible endpoint:

- Your client's **request timeout** may be shorter than the cold-load time, so it looks like the model never comes back
- **Keep-alive**: an idle HTTP connection closing isn't the same as the model unloading, but it reads the same way from the client
- Pre-load the model at startup (`lms load`) and set a long TTL for anything serving traffic

## Decision table

| What you see | Change this |
|---|---|
| Unloads after a quiet period | **Idle TTL** — raise or disable |
| Loading model B evicts model A | **Only keep last JIT loaded model** — off |
| Unloads under heavy use / long chats | **Memory** — smaller quant, shorter context, less GPU offload |
| First request after a pause is very slow | Pre-load + long TTL; raise client timeout |
| Unloads mid-generation with several clients | Known JIT behaviour — pre-load instead of JIT |

## What not to do

- Don't reinstall. Nothing is corrupt
- Don't assume a bigger quant will "fix stability" — it increases eviction pressure
- Don't disable TTL globally on a 16 GB laptop and then wonder why everything else swaps

## FAQ

**What's the default Idle TTL?**
It's a documented default measured in minutes (an hour by default in recent versions) and it's configurable per model and per request.

**Does unloading lose my conversation?**
No. Chat history stays; the model is just reloaded on the next message, with a delay.

**Can I keep two models loaded at once?**
Yes, if memory allows — turn off the keep-only-last-JIT option.

**Is eviction bad for the model?**
No. It's purely a memory-management behaviour; the cost is load time.
