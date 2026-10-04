---
title: "Crafty Controller: Minecraft Server Won't Start"
slug: crafty-controller-server-wont-start
meta_description: "The server exits immediately, or Java errors. The Java version per server, the files Crafty expects to exist, and reading the real console output."
updated: October 2026
cluster: round 14 (tech) — Crafty GitLab issues and binhex documentation
competition: LOW
---

# Crafty Controller: Minecraft Server Won't Start

The console pane in Crafty shows the server's actual output. Read it before changing anything — Minecraft's own error messages are specific, and Crafty is rarely the problem.

```
Dashboard → the server → Terminal
```

## 1. The Java version, per server

Minecraft's Java requirement has moved repeatedly, and **Crafty lets you set the Java path per server** precisely because one install isn't enough:

| Minecraft | Java |
|---|---|
| 1.8 – 1.16 | 8 |
| 1.17 | 16 |
| 1.18 – 1.20.4 | 17 |
| 1.20.5+ | 21 |

```
Dashboard → Edit server → Java version / Executable path
```

In the common Docker images the paths look like:

```
/usr/lib/jvm/java-8-openjdk/bin/java
/usr/lib/jvm/java-17-openjdk/bin/java
/usr/lib/jvm/java-21-openjdk/bin/java
```

```bash
docker exec crafty sh -c 'ls -d /usr/lib/jvm/*'
docker exec crafty sh -c '/usr/lib/jvm/java-21-openjdk/bin/java -version'
```

The characteristic error for a mismatch is:

```
java.lang.UnsupportedClassVersionError: ... has been compiled by a more recent version
of the Java Runtime (class file version 65.0), this version of the Java Runtime only
recognizes class file versions up to 52.0
```

Class file 52 = Java 8, 61 = 17, 65 = 21. The number tells you exactly which runtime the jar needs.

PaperMC in particular tracks requirements tightly; a Paper build for 1.21 will refuse Java 17 outright.

## 2. The files Crafty expects to exist

A documented setup gap: a newly-created or imported server can fail because expected files aren't there. Specifically:

- **`eula.txt` containing `eula=true`.** Minecraft writes `eula=false` on first run and exits. Crafty exposes an accept-EULA control; if you imported a server, create it yourself:

```bash
docker exec crafty sh -c 'echo "eula=true" > /crafty/servers/<uuid>/eula.txt'
```

- **`server.properties`** — absent, the server generates one and restarts, which can look like a crash loop.
- **A `logs/` directory with a `latest.log`**, even empty. Crafty tails this file to populate its console; a missing path has been reported as a startup problem.

```bash
docker exec crafty sh -c 'cd /crafty/servers/<uuid> && mkdir -p logs && touch logs/latest.log'
```

Check ownership afterwards — files created as root inside the container may not be writable by the server process.

## 3. Memory

```
Error occurred during initialization of VM
Could not reserve enough space for 4194304KB object heap
```

The JVM asked for more than the container or host can give.

```
Dashboard → Edit server → Memory (min/max)
```

- The container's memory limit must exceed the JVM's `-Xmx` plus overhead. A 2 GB container with `-Xmx2G` will fail or be OOM-killed.
- On a Pi or a small VPS, 2–3 GB max heap for a vanilla server with a few players is realistic; modpacks need far more.

```bash
docker stats --no-stream crafty
dmesg -T | grep -iE 'oom|killed process' | tail
```

## 4. Port and address

```
java.net.BindException: Address already in use
```

- Two servers configured on 25565.
- The port not published from the container:

```yaml
services:
  crafty:
    ports:
      - "8443:8443"
      - "8123:8123"
      - "19132:19132/udp"
      - "25500-25600:25500-25600"
```

Publishing a **range** is the usual pattern, because Crafty assigns ports to servers within it. A server configured outside the published range starts and is unreachable — which reads as "won't start" to players.

## 5. Crafty itself not starting

Distinct from a server failing:

```bash
docker logs crafty --tail 100
```

- **Permissions on the Crafty data volume.** It runs as a non-root user; a root-owned volume fails at startup.
- **Port 8443 taken.**
- **A corrupt `crafty.sqlite`** after an unclean shutdown. Crafty keeps backups of its own database in its data directory; restoring one is faster than rebuilding server definitions.

```bash
docker exec crafty sh -c 'ls -la /crafty/app/config/db/'
```

## 6. Imported server starts and immediately stops

Check the console for the real reason, which is usually one of:

- **A modpack expecting a specific forge/fabric installer step** that wasn't run. Install the loader first, then import.
- **World version newer than the server jar.** Minecraft refuses to downgrade a world; the error names the data version.
- **A broken mod.** The stack trace names the mod's package. Remove it and start again.

## What not to do

- **Don't set the Java path globally** and expect it to suit every server. Set it per server.
- **Don't run with `-Xmx` equal to the container limit.** Leave headroom for the JVM's non-heap memory.
- **Don't accept the EULA by editing the jar or a config you don't understand.** The file is one line.
- **Don't debug from Crafty's UI alone.** The server's console output is the primary source.

## Prevention

| Habit | Why |
|---|---|
| Java version recorded per server, matched to its Minecraft version | The dominant cause of startup failures |
| A published port range covering what Crafty assigns | Prevents unreachable-but-running servers |
| Memory limit > `-Xmx` + 1 GB | Avoids OOM kills mid-session |
| Scheduled world backups through Crafty | Worlds are the irreplaceable part |

## FAQ

**Can it manage Bedrock servers?**
Yes, and they use UDP — publish `19132/udp`.

**Does it support modpack installers?**
It can run server jars and scripts; modpack-specific installers are usually a manual first step.

**Backups fill the disk.**
Set a retention count per server; the default keeps more than you'd expect.

**Players can connect locally but not remotely.**
Port forwarding and the published range, not Crafty. Confirm from outside with `nc -zv your.ip 25565`.
