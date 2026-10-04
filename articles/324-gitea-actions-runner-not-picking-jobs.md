---
title: "Gitea Actions Runner Registered But Not Picking Up Jobs"
slug: gitea-actions-runner-not-picking-jobs
meta_description: "The runner shows online in Gitea and workflows stay queued forever. Labels, the enabled flag, and the Docker socket requirement."
updated: October 2026
cluster: round 13 (tech) — Gitea and act_runner GitHub issues
competition: LOW
---

# Gitea Actions Runner Registered But Not Picking Up Jobs

A runner that appears **online** in Gitea's admin UI while jobs sit at "Waiting" is nearly always a **label mismatch**. That's the first thing to check, and it's a two-minute fix.

## 1. Labels must match `runs-on`

The runner registers with a set of labels. A job requests one via `runs-on`. If no online runner carries that label, the job queues indefinitely with no error — because from Gitea's point of view, a suitable runner might appear later.

Check what your runner registered:

```bash
cat /path/to/act_runner/.runner
```

```json
{
  "labels": ["ubuntu-latest:docker://gitea/runner-images:ubuntu-latest"]
}
```

And what your workflow asks for:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
```

`ubuntu-latest` matches the label `ubuntu-latest:docker://...` — the part before the first colon is the label name; the rest is how to run it. A workflow using `runs-on: ubuntu-22.04` against a runner registered only with `ubuntu-latest` will never run.

To change labels you must re-register, or edit the config and restart:

```yaml
# config.yaml
runner:
  labels:
    - "ubuntu-latest:docker://gitea/runner-images:ubuntu-latest"
    - "ubuntu-22.04:docker://gitea/runner-images:ubuntu-latest"
    - "self-hosted:host"
```

The `:host` suffix means "run directly on the host, no container" — useful, but then the host must have whatever the workflow needs (node, git, etc.) installed.

Labels can also be edited per-runner in Gitea's admin UI in recent versions, which avoids re-registration.

## 2. Actions must be enabled — in three places

```ini
; app.ini
[actions]
ENABLED = true
DEFAULT_ACTIONS_URL = github
```

Then:

- **Per repository**: Settings → Actions must be enabled. Repositories created before you turned Actions on may have it off.
- **Per organisation**: an org can disable Actions for all its repos.

A disabled repo shows no Actions tab at all, which is the giveaway. A repo with the tab but queued jobs is the label case.

## 3. The runner needs Docker (usually)

With `docker://` labels, the runner starts a container per job. It needs the socket:

```yaml
services:
  act_runner:
    image: gitea/act_runner:latest
    environment:
      GITEA_INSTANCE_URL: https://gitea.example.com
      GITEA_RUNNER_REGISTRATION_TOKEN: xxxx
      GITEA_RUNNER_NAME: runner-1
    volumes:
      - ./data:/data
      - /var/run/docker.sock:/var/run/docker.sock
```

Failures here:

- **Socket not mounted** — the runner registers, goes online, accepts a job and immediately fails with a Docker connection error. Check the runner's own log, not Gitea's UI.
- **Socket permissions** — the runner's user isn't in the `docker` group. Inside the official image it runs as root, so this bites mainly on host installs.
- **Can't pull the image** — the `gitea/runner-images` pull fails on a network-restricted host. Pre-pull it or point the label at a local image.

Note the security implication: mounting the Docker socket gives the runner (and anything a workflow runs) root on the host. For anything with untrusted contributors, use a dedicated host or rootless setup.

## 4. Network: the runner must reach Gitea, as Gitea's URL

```bash
docker exec act_runner wget -qO- https://gitea.example.com/api/v1/version
```

Specific traps:

- **`GITEA_INSTANCE_URL` using `localhost`.** That's the runner's own container. Use the LAN IP or the external hostname.
- **`ROOT_URL` in app.ini differing from the URL the runner uses.** Gitea hands the runner URLs built from `ROOT_URL`; if that's wrong, the runner fetches from an address it can't reach, and job logs show artifact/checkout failures rather than registration problems.
- **Self-signed certificate.** The runner validates TLS. Either install the CA in the runner container or use `insecure: true` in config.yaml for a lab.

## 5. Reading the right log

Gitea's UI shows job state; the runner's log shows why it did or didn't take one.

```bash
docker logs act_runner --tail 100
```

What to look for:

- `runner: successfully pinged the Gitea instance server` — registration and connectivity are fine
- Repeated `fetch task` with nothing returned — connected, no matching job. Label mismatch.
- `received task` followed by an error — it's taking jobs and failing. Docker or workflow problem, not queueing.

That distinction tells you whether to look at labels or at the job itself.

## What not to do

- **Don't re-register repeatedly.** Each registration adds a runner entry; you end up with a list of offline ghosts and the same label problem.
- **Don't copy a GitHub Actions workflow unchanged** and expect every action to work. Gitea resolves actions from `DEFAULT_ACTIONS_URL`; actions depending on GitHub API specifics or on the GitHub-hosted runner image's preinstalled tooling will fail.
- **Don't mount the Docker socket on a public instance with open registration.** That's a direct path to host root for anyone who can push a workflow.
- **Don't debug in Gitea's UI only.** The runner log is where the answer is.

## Prevention

| Habit | Why |
|---|---|
| Register with several common labels at once | `ubuntu-latest`, `ubuntu-22.04`, `self-hosted` covers most copied workflows |
| Keep `ROOT_URL` and `GITEA_INSTANCE_URL` consistent and externally valid | Prevents checkout and artifact failures |
| One runner per trust level | Workflow code runs with the runner's privileges |
| Pre-pull runner images | Makes first runs fast and offline-tolerant |

## FAQ

**Can I use GitHub's marketplace actions?**
Many work. Those calling GitHub's API or expecting GitHub-specific environment variables don't.

**Jobs run but `actions/checkout` fails.**
`ROOT_URL` or network. The runner fetches the repo over HTTP(S) from the URL Gitea gave it.

**How do I limit concurrency?**
`capacity` in the runner's config.yaml. Default is 1; raise it only if the host can take parallel containers.

**Workflows don't trigger at all.**
Check the file is in `.gitea/workflows/` or `.github/workflows/`, and that the `on:` events match what you did. A queued job means triggering worked; no job at all means it didn't.
