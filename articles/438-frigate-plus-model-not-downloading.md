---
title: "Frigate+ Model Not Downloading"
slug: frigate-plus-model-not-downloading
meta_description: "The model never arrives, or stops being found after an upgrade. The model cache, the config directory mapping, and the segfault during download."
updated: October 2026
cluster: round 14 (tech) — blakeblackshear/frigate discussions and docs
competition: LOW
---

# Frigate+ Model Not Downloading

Frigate downloads a model **once** and caches it. That single fact explains most of these: a corrupt or partial file in the cache means Frigate sees a model present and never retries.

```bash
docker exec frigate ls -la /config/model_cache/
```

## 1. Clear the cache and restart

```bash
docker exec frigate sh -c 'rm -rf /config/model_cache/*'
docker restart frigate
docker logs -f frigate | grep -iE 'model|download|frigate\+'
```

> **Frigate will only attempt to download a model if it does not exist in the cache.** A corrupted file prevents a successful download.

That's the documented behaviour, and clearing the cache is the first action — not reconfiguring, not re-generating the API key.

## 2. The config directory must be mapped as a directory

A documented requirement with a subtle failure mode:

> **Ensure your Docker Compose maps the entire config directory, not individual files.**

```yaml
services:
  frigate:
    volumes:
      - ./config:/config                    # correct
      # - ./config/config.yml:/config/config.yml   ← wrong
```

Mapping just `config.yml` means `/config` is inside the container's writable layer. The model downloads, works until the container is recreated, and then vanishes — reported as "model not found after upgrade".

You may also need to create the cache directory yourself:

```bash
mkdir -p ./config/model_cache
```

and it must be writable by the container's user.

## 3. Credentials and the plus model id

```yaml
model:
  path: plus://a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

```yaml
    environment:
      - PLUS_API_KEY=your-frigate-plus-key
```

Points that matter:

- The `plus://` id is the **model id** from your Frigate+ account, not the model name.
- `PLUS_API_KEY` must be set as an environment variable or in the secrets file — not inline in `config.yml` where it would be committed somewhere eventually.
- **Internet access is required.** Using Frigate+ needs the container to reach Frigate's servers; an air-gapped instance cannot use `plus://` models at all.

```bash
docker exec frigate sh -c 'curl -s -o /dev/null -w "%{http_code}\n" https://api.frigate.video/'
```

## 4. Download starts and the process dies

```
Segmentation fault
```

> **The segmentation fault during model download is a known issue that can occur in certain environments, particularly with CPU instruction compatibility problems or network/SSL issues during download.**

Two directions:

- **Older CPU without AVX.** Some of Frigate's dependencies assume modern instruction sets. Check:

```bash
grep -o -m1 -E 'avx[0-9_]*' /proc/cpuinfo | sort -u
```

No AVX on the host means some model paths will not run, regardless of download success. Use the Coral/EdgeTPU detector path instead of a CPU or OpenVINO model.

- **SSL interception.** A corporate or Pi-hole-style TLS proxy breaks the download mid-stream. Confirm the container can fetch over TLS cleanly (the curl above).

## 5. Semantic search models are a different download

Worth separating, because the symptom text is almost identical and people conflate them:

```
Unable to download model for semantic search
```

Semantic search downloads **CLIP-family models from Hugging Face**, not from Frigate+. Causes:

- **Hugging Face unreachable or slow.** Extended download times mean network, not configuration:

```bash
docker exec frigate sh -c 'curl -s -o /dev/null -w "%{http_code} %{time_total}\n" https://huggingface.co/'
```

- **Model cache again** — same directory, same clearing procedure.
- **Memory.** These models are larger; a container with little RAM fails during load rather than download.

So: `plus://` problems are Frigate's API; semantic search problems are Hugging Face. Check which one the log actually names.

## 6. Model downloads, detection doesn't improve

Not a download problem:

- **The detector must match the model type.** A Frigate+ model built for EdgeTPU won't run on an OpenVINO detector and vice versa. The model id encodes the target; pick the right export when you generate it.
- **`model` block overrides.** If you set `width`, `height` or `labelmap` manually, they can conflict with the plus model's own metadata. Remove manual overrides when using `plus://`.

```yaml
detectors:
  coral:
    type: edgetpu
    device: pci:0

model:
  path: plus://a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

That's the whole configuration — no dimensions, no labelmap.

## What not to do

- **Don't map individual config files.** Map the directory.
- **Don't re-generate your API key** to fix a download. The cache is the usual culprit.
- **Don't set manual model dimensions with a plus model.** Its metadata carries them.
- **Don't expect Frigate+ to work offline.** It's a hosted service by design.

## Prevention

| Habit | Why |
|---|---|
| `./config:/config` as a directory mapping | Cache survives container recreation |
| Clear `model_cache` as step one of any model problem | Fixes the partial-download case |
| Export the plus model for your actual detector | A mismatched export never runs |
| Note which service the error names | Frigate+ and Hugging Face failures read alike |

## FAQ

**Is Frigate+ required for good detection?**
No. The bundled models are decent; Frigate+ models trained on your own cameras are better, particularly for false positives.

**How often should I retrain?**
After submitting a batch of corrections — a few hundred labelled images makes a visible difference.

**Can I use a plus model and semantic search together?**
Yes; they're independent features with independent downloads.

**Model works, labels are wrong.**
A leftover `labelmap` override in config. Remove it.
