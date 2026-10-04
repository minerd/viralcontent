---
title: "Frigate Semantic Search Returning Nothing? Reindex and Check the Memory"
slug: frigate-semantic-search-not-working
meta_description: "Semantic search that finds nothing, stops working, or never downloads its models. The reindex requirement, RAM and shm sizing, and the duplicate config-file trap."
updated: October 2026
cluster: round 12 (tech) — Frigate GitHub discussions only
competition: LOW
---

# Frigate Semantic Search Returning Nothing? Reindex and Check the Memory

Three different problems get reported as "semantic search doesn't work". They need different fixes.

## 1. You just enabled it — it doesn't index the past

Frigate **does not automatically index older tracked objects**. Enable semantic search and only *new* objects get embeddings, so searching for something from last week returns nothing.

```yaml
semantic_search:
  enabled: true
  reindex: true      # one-off: rebuild embeddings for existing objects
```

Start Frigate, let the reindex run (watch the log — it can take hours on a large database), then **set `reindex` back to false** so it doesn't redo the work on every restart.

This is the single most common cause, and it's documented behaviour rather than a bug.

## 2. It stopped working / models won't download

Semantic search runs an **AI model locally**. Reported symptoms when resources run out: it stops working entirely, model downloads never complete, and reindexing fails to start.

Resource reality from the reports:
- **16 GB RAM** and a dedicated GPU is the comfortable target
- One documented fix: going from **8 GB to 16 GB RAM** and raising **shm from 2 GB to 8 GB**
- A **Raspberry Pi** will not run it reliably — that's explicit in the project's guidance

```yaml
services:
  frigate:
    shm_size: "512mb"    # raise this; bigger for more cameras + semantic search
    deploy:
      resources:
        limits:
          memory: 8G
```

Also check the model cache:
```bash
docker exec frigate ls -la /config/model_cache/
```
Models live there. A **partial download** blocks everything — delete the incomplete model directory and let it re-download. If you restored models from a backup, confirm the **directory structure** matches what Frigate expects.

## 3. Zero inferences per second

If the embedding metrics show **0 inferences/s** across the board, the models aren't loading or running at all:

```bash
docker compose logs frigate | grep -i -e embed -e semantic -e model
```

Look for load failures, CUDA/ONNX errors, or out-of-memory kills. An exit code 137 anywhere in the stack means memory, full stop.

## 4. The duplicate config file trap

A genuinely maddening one, worth checking early: if you have **both `config.yml` and `config.yaml`**, the UI may edit one while Frigate loads the other. You enable semantic search, the UI shows it enabled, and the running instance never had it.

```bash
docker exec frigate ls -la /config/config.y*
```

Delete or rename the one you don't use. Then confirm from the running config in the UI's config editor.

## 5. Expectations

Even working perfectly, semantic search is **similarity-based**:

- It searches **descriptions and visual embeddings** of tracked objects, not raw video
- Objects must have been **tracked and saved** — nothing was detected, nothing to search
- Generative AI descriptions (if enabled) improve text search a lot, and need their own provider configured
- Searching for something your detector never classified won't work

## Order of operations

1. Confirm **one** config file, and that semantic search is enabled in the running config
2. Check **RAM and shm**; look for OOM kills
3. Check the **model cache** downloaded completely
4. Look at **inferences/s** in the metrics
5. Run a **reindex** for historical objects
6. Then judge the search quality

## Prevention

1. Enable it on hardware that can run it — **16 GB and a GPU** if you want it to be pleasant
2. Raise **shm_size** when you add cameras or features
3. Keep **one config file**
4. Run the **reindex once**, then disable the flag
5. **Pin the Frigate version**; these features move fast

## FAQ

**Why does it find nothing from before I enabled it?**
Old objects aren't indexed automatically. Run a one-off reindex.

**Will it run on a Pi?**
Not reliably. It's a local AI model.

**Model download never finishes.**
Delete the partial model cache and retry; check disk space and network.

**The UI says it's enabled but nothing happens.**
Check for duplicate `config.yml`/`config.yaml` files.
