---
title: "Dockge: \"This stack is not managed by Dockge\" (and Missing Stacks)"
slug: dockge-stack-not-managed
meta_description: "Stacks vanish from the list, show as unmanaged, or won't start. The stacks-path rule that must match on both sides of the colon."
updated: October 2026
cluster: round 14 (tech) — Dockge GitHub issues and discussions
competition: LOW
---

# Dockge: "This stack is not managed by Dockge" (and Missing Stacks)

Dockge has one rule that explains almost every one of these reports:

> **The host path and the container path of the stacks directory must be identical.**

```yaml
services:
  dockge:
    image: louislam/dockge:1
    ports:
      - 5001:5001
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./data:/app/data
      - /opt/stacks:/opt/stacks        # ← same on both sides
    environment:
      - DOCKGE_STACKS_DIR=/opt/stacks
```

`/opt/stacks:/opt/stacks` is correct. `/docker:/opt/stacks` is not, even though Docker accepts it happily. The reason is that Dockge runs `docker compose` commands **against the host's Docker daemon**, so the paths inside your compose files are interpreted by the host, not by the Dockge container. If the two differ, Dockge writes a file to a path the daemon then can't find.

## 1. Check the three places the path appears

```bash
docker inspect dockge --format '{{json .Mounts}}' | python3 -m json.tool
docker exec dockge sh -c 'echo $DOCKGE_STACKS_DIR; ls -la $DOCKGE_STACKS_DIR'
```

All three must agree: the left side of the volume, the right side, and `DOCKGE_STACKS_DIR`. Relative paths (`./stacks:/opt/stacks`) are a common cause — use absolute paths only.

## 2. "Not managed by Dockge"

This appears for a container that is running but whose compose file isn't in the stacks directory. Dockge is a compose-file editor, not a container manager: it owns what lives under `DOCKGE_STACKS_DIR` and merely observes everything else.

To bring an existing stack under Dockge:

```bash
mkdir -p /opt/stacks/myapp
mv /wherever/docker-compose.yml /opt/stacks/myapp/compose.yaml
cd /opt/stacks/myapp && docker compose up -d
```

The directory name becomes the stack name, and it must match the compose project name — otherwise Dockge sees a compose file with no running containers, and separately a set of containers with no file.

```bash
# find the project name a running container belongs to
docker inspect myapp-web-1 --format '{{index .Config.Labels "com.docker.compose.project"}}'
```

If that returns `wherever` and your directory is `myapp`, either rename the directory or take the stack down and up again from the new location.

## 3. Stacks disappeared from the list

Three causes, in order:

- **The volume was remounted or the container recreated with a different path.** Dockge reads the directory live; nothing is stored in its database about stack *contents*.
- **The file is named something Dockge doesn't read.** It looks for `compose.yaml`; `docker-compose.yml` works in recent versions but `docker-compose.yaml.bak` or a nested subdirectory does not.
- **Dockge updated itself and didn't come back cleanly.** Updating Dockge *from inside Dockge* restarts the container mid-operation. The documented fix is to run the update from the host:

```bash
cd /opt/stacks/dockge
docker compose pull && docker compose up -d
```

Keep Dockge's own compose file in the stacks directory, but update it from a shell, not from its own UI.

## 4. Stack won't start

Read the actual output — Dockge streams `docker compose up` to the terminal pane, and the error is usually ordinary:

- **`Bind for 0.0.0.0:5001 failed: port is already allocated`** — something else has the port. Change the host side only.
- **`The container name "/x" is already in use`** — a leftover container from a previous name. `docker rm x` and retry.
- **`no such file or directory` on a bind mount** — the host path doesn't exist. Dockge won't create it for you.
- **Environment variables empty.** Dockge writes a `.env` next to the compose file. Variables referenced as `${VAR}` are resolved by the host's compose, so the `.env` must be in the same directory as the compose file, not in Dockge's data volume.

## What not to do

- **Don't use a different path on each side of the colon.** It is the single cause of most Dockge problems and nothing downstream works around it.
- **Don't update Dockge from its own UI.** Do it from a shell.
- **Don't edit compose files on disk and in the UI at the same time.** Dockge writes the whole file on save and will overwrite your shell edit.
- **Don't expect Dockge to manage containers started elsewhere.** Move the compose file in first.

## Prevention

| Habit | Why |
|---|---|
| `/opt/stacks:/opt/stacks` absolute and identical | Removes the dominant failure class |
| One directory per stack, named as the project | Keeps file and containers associated |
| Update Dockge from a shell | Avoids the self-restart problem |
| Back up `/opt/stacks` | It is your entire infrastructure as text |

## FAQ

**Dockge or Portainer?**
Dockge edits compose files you can also use without it — your setup stays portable. Portainer manages more, with its own state.

**Can it manage a remote host?**
Recent versions support agents. The same path rule applies on each host.

**Does it support compose profiles and extends?**
It passes the file to `docker compose`, so whatever your compose version supports works. The UI editor won't understand it, but execution will.

**Terminal pane shows nothing.**
Websocket upgrade missing at your reverse proxy. Add `Upgrade`/`Connection` headers.
