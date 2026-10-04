---
title: "Immich Machine Learning Container Keeps Restarting? Memory, Models and Stale Images"
slug: immich-machine-learning-restarting
meta_description: "immich-machine-learning in a restart loop after an upgrade. Why it's usually RAM or a half-pulled image, how to read the exit code, and how to run without ML temporarily."
updated: October 2026
cluster: round 11 (tech) — Immich GitHub issues only
competition: LOW
---

# Immich Machine Learning Container Keeps Restarting? Memory, Models and Stale Images

You upgrade Immich, and `immich_machine_learning` goes into a **restart loop**. The server and web UI work, photos upload, but search, faces and smart albums don't. Every search result for this is a GitHub issue for a specific version.

Three causes cover nearly all of them.

## 1. Out of memory (the most common)

The ML container loads vision and text models into RAM. On a NAS or a small VM it is routinely the first thing to be killed.

Check whether the kernel killed it:

```bash
docker inspect immich_machine_learning --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
dmesg -T | grep -i -e oom -e "killed process" | tail
```

**Exit code 137 or `OOMKilled: true` means memory**, full stop — not a bug in the release.

What to do:
- Give the host more RAM, or **add swap** (slow, but it stops the loop)
- Use **smaller models**: in the Immich admin settings, the CLIP model is configurable. The default multilingual models are much heavier than the small English ones
- Set a container **memory limit high enough** that it isn't killed mid-load, but low enough that it doesn't take the database down with it
- Don't run face detection and smart search jobs at full concurrency on a 4 GB box — lower job concurrency in admin settings

## 2. A half-upgraded image set

Immich expects **server and ML container on the same version**. A `docker compose up -d` that pulled one and not the other, or a cached old layer, produces a container that starts and immediately dies.

```bash
docker compose pull
docker compose up -d
docker image prune
```

If that doesn't take, force it:

```bash
docker compose down
docker pull ghcr.io/immich-app/immich-machine-learning:release
docker pull ghcr.io/immich-app/immich-server:release
docker compose up -d
```

The reported fix in several issues is exactly this — removing the containers and images so Docker genuinely fetches the current version. Check the versions agree:

```bash
docker compose exec immich_server /bin/sh -c 'echo $IMMICH_VERSION' 2>/dev/null
docker inspect immich_machine_learning --format '{{index .Config.Labels "org.opencontainers.image.version"}}'
```

## 3. The model cache

ML downloads models on first use into a cache volume. A **partial or corrupt download** makes the container crash every time it tries to load it.

Symptoms: the log mentions a model file, a tarball, or `onnx` right before exiting.

Fix: delete the model cache volume and let it re-download.

```bash
docker compose down
docker volume ls | grep model-cache
docker volume rm immich_model-cache      # name per your compose file
docker compose up -d
```

This costs a re-download, not your photos. The model cache is disposable by design — make sure it's a **named volume**, not a bind mount into something you back up.

## Read the log properly

```bash
docker compose logs --tail=200 immich_machine_learning
docker compose logs -f immich_machine_learning
```

| What you see | Cause |
|---|---|
| Exit 137 / OOMKilled | Memory |
| `ModuleNotFoundError`, version string mismatch | Mixed image versions |
| Error naming a model or `.onnx` file | Corrupt model cache |
| `CUDA`/`ROCm` errors | Hardware-acceleration image on a host without the runtime |
| Immediate exit, no log | Wrong image tag, or an arch mismatch (arm64 vs amd64) |

## Hardware acceleration gotcha

If you switched to the **CUDA / OpenVINO / ROCm** ML image, you also need the matching runtime and device passthrough. A `-cuda` tag on a host without the NVIDIA container toolkit crash-loops instantly. Go back to the plain `:release` tag to confirm the rest works, then add acceleration deliberately.

## Running without ML for now

Immich works without the ML container — you lose smart search, face recognition and CLIP-based features, but uploads, albums and browsing are fine.

Comment the service out, bring the stack up, and come back to ML when you have time. That's better than leaving a crash loop hammering the host while you work out the memory situation.

## Before your next upgrade

1. **Pin a version tag** rather than `release`, and bump it deliberately
2. **Read the release notes** — Immich moves fast and has had breaking changes
3. **Back up the database**, not the model cache
4. Watch `docker compose logs -f` on the first start after an upgrade

## FAQ

**Will my photos be affected?**
No. The ML container is stateless apart from its model cache.

**Why did it work before the upgrade?**
Usually a bigger default model, a new dependency, or mixed image versions — plus a host that was already close to its memory limit.

**How much RAM does it need?**
Depends on the model. The small CLIP models run in well under a gigabyte; the large multilingual ones need several.

**Is it safe to delete the model cache?**
Yes. It re-downloads.
