---
title: "Gitea or Forgejo Rejecting Pushes After an Update? Regenerate the Hooks"
slug: forgejo-gitea-hook-push-failing
meta_description: "'pre-receive hook declined' or 'Internal Server Error' on push after upgrading. The admin regenerate-hooks command, broken-hook warnings and what causes them."
updated: October 2026
cluster: round 12 (tech) — Gitea/Forgejo GitHub issues, forum and Codeberg
competition: LOW
---

# Gitea or Forgejo Rejecting Pushes After an Update? Regenerate the Hooks

Symptoms after an upgrade: `! [remote rejected] main -> main (pre-receive hook declined)`, sometimes with **Internal Server Error** in the output, or the repository page warning that **"the Git hooks of this repository seem to be broken"**.

## 1. Regenerate the hooks (the actual fix)

Every repository has Git hook scripts on disk that call back into the server. After an upgrade — especially one that changed paths, the binary location, or the config — those scripts can point at the wrong place.

```bash
# Gitea
gitea --config /etc/gitea/app.ini admin regenerate hooks
# Forgejo
forgejo --config /etc/forgejo/app.ini admin regenerate hooks
# Docker
docker exec -u git gitea gitea admin regenerate hooks
```

Also useful:
```bash
gitea --config ... admin regenerate keys
```

This is the documented remedy and it fixes the majority of post-upgrade push failures. Run it as the **git user**, with the **same config file** the service uses — running it as root creates files the service can't use, which turns one problem into two.

## 2. The "hooks seem broken" warning specifically

Documented meaning: **the database disagrees with Git about the commit ID for a branch.** It's often transient.

- The suggested workaround is simply **push another commit** so the hooks run again
- If it persists, regenerate hooks, then check the repository's health
- `gitea doctor check --all` (and `--fix`) is the maintenance command for consistency problems like this

## 3. Internal Server Error on push

The hook calls the server's internal API. If that call fails, the push is rejected. Look at the server log at **debug** level during a push:

```ini
[log]
LEVEL = debug
```

Then push and read what the internal call returned. Common causes:

- **`ROOT_URL` / `LOCAL_ROOT_URL`** wrong after a domain or port change, so the hook can't reach the API (`Post http://localhost:3000/api/internal/hook/...` failing)
- **`INTERNAL_TOKEN`** mismatched or missing in `app.ini`
- The server listening on a different interface than the hook is calling
- SSH pushes running as a user that can't reach the HTTP port (firewall on localhost, or a container boundary)

Set `LOCAL_ROOT_URL` explicitly in `app.ini` when the public URL isn't reachable from the server itself — this is the classic reverse-proxy-plus-Docker case.

## 4. Permissions on the repository tree

```bash
ls -la /var/lib/gitea/data/gitea-repositories/<owner>/<repo>.git/hooks/
```

- Everything must be owned by the **git user** the service runs as
- Hooks must be **executable**
- A restore from backup with wrong ownership produces exactly this failure
- In Docker, check `USER_UID`/`USER_GID` still match the volume's ownership after a host change

## 5. Branch protection and Actions

Not every rejection is a broken hook:

- **Branch protection** rules reject pushes by design — read the full message, which usually names the rule
- Reported for Forgejo: a branch-protection whitelist that allows a PAT push locally but rejects the identical push from **Forgejo Actions**, because the Actions identity isn't whitelisted
- Required status checks or signed-commit requirements
- Push size limits, or LFS misconfiguration

The giveaway: it fails for **everyone and every branch** (hooks) versus **specific branches or identities** (protection rules).

## 6. If an upgrade broke it for everyone

1. `admin regenerate hooks`
2. `doctor check --all`
3. Check `ROOT_URL`, `LOCAL_ROOT_URL`, `INTERNAL_TOKEN`
4. Check ownership/permissions of the repository tree
5. Roll back to the previous version if you need pushes working now — then upgrade again after reading the release notes

## Prevention

1. **Back up `app.ini`, the database and the repository tree** before upgrades
2. Run admin commands **as the git user with the real config**
3. Set **`LOCAL_ROOT_URL`** when behind a proxy or in Docker
4. **Pin the image tag**
5. Read Gitea/Forgejo release notes — major versions have migration steps

## FAQ

**Is `regenerate hooks` safe?**
Yes. It rewrites the hook scripts; it doesn't touch your repository contents.

**Why does one more commit fix it?**
Because the warning is often a transient database/Git disagreement the next hook run reconciles.

**Pushes work over SSH but not HTTPS (or vice versa).**
That points at URL/token configuration rather than hooks.

**Only one branch is rejected.**
Branch protection, not hooks. Read the rejection message.
