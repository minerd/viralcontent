---
title: "SeaweedFS: \"No More Writable Volumes\""
slug: seaweedfs-no-writable-volumes
meta_description: "The filer can't find writable volumes, or files exist on disk and report not found. Replication levels, volume limits and master registration."
updated: October 2026
cluster: round 14 (tech) — seaweedfs GitHub issues and wiki
competition: LOW
---

# SeaweedFS: "No More Writable Volumes"

```
failed to find writable volumes for collection "": No more writable volumes
```

This is the master telling the filer that **no volume satisfies the requested replication level**. It is almost never "the disk is full" — it is a mismatch between what you asked for and what the cluster can provide.

Start here:

```bash
weed shell -master=localhost:9333
> volume.list
> cluster.check
```

`volume.list` shows every volume, its size, its collection and whether it's read-only. Count the **data centres, racks and nodes** it reports, then compare against your replication setting.

## 1. Replication requires enough distinct nodes

SeaweedFS replication is `xyz`:

- **x** — copies in other data centres
- **y** — copies in other racks in the same data centre
- **z** — copies on other servers in the same rack

| Setting | Minimum distinct volume servers |
|---|---|
| `000` | 1 |
| `001` | 2 (same rack) |
| `010` | 2 racks |
| `100` | 2 data centres |
| `011` | 3 |

The commonest cause of this error on a small cluster: **`-defaultReplication=001` with a single volume server.** The master cannot place two copies on one node, so there is no writable volume and the message is exactly this.

```bash
weed master -mdir=/data/master -defaultReplication=000
```

Per-collection override:

```bash
> volume.configure.replication -collection=mybucket -replication=001
```

Set replication to what your node count supports. Adding nodes later and raising it is straightforward; running with a setting you can't satisfy means no writes at all.

## 2. Volume count limit reached

Each volume server allows a fixed number of volumes:

```bash
weed volume -dir=/data/vol1 -max=100 -mserver=localhost:9333 -port=8080
```

`-max` defaults low relative to what people expect. Once all allowed volumes exist and are full, no new volume can be created and you get the same message.

```bash
> volume.list
# look for: volume count vs max
```

Raise `-max`, or add a volume server. Note that each volume is a preallocated file of `-volumeSizeLimitMB` (default 30 GB in recent versions) if preallocation is on — so `-max=100` can reserve a great deal of disk immediately:

```bash
weed master -volumeSizeLimitMB=1024 -volumePreallocate=false
```

Turning preallocation off is usually right for homelab-scale deployments.

## 3. Disk space headroom

The master stops creating volumes when a server's free space drops below a threshold, which it does *before* the disk is actually full:

```bash
df -h /data/vol1
> volume.list
```

A server with 5% free is treated as unable to take new volumes. Free space or add capacity; there's no setting worth overriding here.

## 4. Volume server not registered with the master

If `volume.list` doesn't show a server you expect:

```bash
# on the volume server
journalctl -u weed-volume -n 50
curl -s http://localhost:9333/cluster/status | python3 -m json.tool
```

- **`-mserver`** must point at the master(s). A typo means the volume server runs happily and the master never knows it exists.
- **Network reachability both ways.** The master calls back to the volume server's **publicUrl**; if that's an address the master can't reach (a container-internal name, or a Docker bridge IP), registration appears to work and placement fails:

```bash
weed volume -mserver=master:9333 -ip=192.168.1.20 -publicUrl=192.168.1.20:8080 -port=8080
```

Setting `-ip` and `-publicUrl` explicitly is the fix for most container deployments, and it's the piece most compose files omit.

## 5. "Volume not found" with files present on disk

A separate and alarming symptom: the files are in the filesystem and the volume reports as missing. Documented causes:

- **The EC encoder couldn't mark volumes read-only**, leaving inconsistent state after volume server downtime.
- **Volume files present but not loaded** because the `.idx` index is missing or corrupt. The master knows the volume id; the server can't serve it.

```bash
ls -la /data/vol1/ | head
# each volume is id.dat + id.idx
```

A `.dat` without its `.idx` can often be rebuilt:

```bash
weed fix -dir=/data/vol1 -volumeId=7
```

Run that with the volume server **stopped**. It rebuilds the index from the data file. Back up the `.dat` first.

## 6. Filer shows a size, downloads give 0 bytes

Reported for S3 downloads: the filer reports the correct size and the volume server returns empty chunks. That's a volume-level problem — the filer's metadata is intact and the chunks aren't retrievable.

```bash
> volume.check.disk -v
> fs.meta.notify
```

Check whether the chunks' volumes are online and not read-only. If a volume went missing, the filer's metadata still describes files whose data is gone — which is why **filer metadata and volume data must be backed up together** to be useful.

## What not to do

- **Don't set replication higher than your node count supports.** It stops all writes.
- **Don't run `weed fix` with the volume server running.** It will corrupt the index it's rebuilding.
- **Don't fill volume servers past ~90%.** The master stops placing before you expect.
- **Don't back up the filer store alone.** Metadata without chunks restores nothing.

## Prevention

| Habit | Why |
|---|---|
| `-defaultReplication` matched to actual node count | Removes the dominant cause |
| `-ip` and `-publicUrl` set explicitly on volume servers | Registration and placement both depend on reachability |
| `volume.list` and `cluster.check` in your routine | Catches read-only and missing volumes early |
| Filer metadata and volume data backed up together | Either alone is useless |

## FAQ

**How do I grow the cluster?**
Add volume servers pointing at the same master. New volumes get placed on them; existing data stays put unless you rebalance (`volume.balance`).

**Is SeaweedFS the right choice over MinIO or Garage?**
It scales to very large object counts well. For a two-node homelab, simpler systems have fewer of these placement subtleties.

**Erasure coding instead of replication?**
Supported for cold data, with more nodes required and a different failure profile. Don't start there.

**Filer store options?**
LevelDB (single node), or Postgres/MySQL/Redis for multiple filers. The store choice determines whether you can run more than one filer.
