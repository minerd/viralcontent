---
title: "Semaphore UI: \"The playbook could not be found\""
slug: semaphore-playbook-could-not-be-found
meta_description: "Ansible tasks fail on a missing playbook or a missing repository directory. Paths relative to the repo root, the git requirement, and the clone failures."
updated: October 2026
cluster: round 13 (tech) — Semaphore UI GitHub issues and discussions
competition: LOW
---

# Semaphore UI: "The playbook could not be found"

```
ERROR! the playbook: pb_apt-update.yml could not be found
```

Semaphore clones your repository into a temporary directory and runs `ansible-playbook` from the clone's root. So the playbook path in the task template must be **relative to the repository root** — and the three ways this goes wrong are all path-shaped.

## 1. The path is relative to the repo root

If your repository looks like this:

```
ansible-repo/
├── playbooks/
│   ├── apt-update.yml
│   └── deploy.yml
├── inventory/
│   └── production.yml
└── roles/
```

then the template's **Playbook Filename** must be `playbooks/apt-update.yml`, not `apt-update.yml` and not `/home/ansible/playbooks/apt-update.yml`.

Check what Semaphore cloned:

```bash
docker exec semaphore ls -la /tmp/semaphore/repository_1/
docker exec semaphore ls -la /tmp/semaphore/repository_1/playbooks/
```

The directory number corresponds to the repository id in Semaphore. If the directory is missing entirely, the clone failed — section 3. If it's there and your playbook isn't at the path you specified, that's the answer.

Case matters. `Playbooks/apt-update.yml` and `playbooks/apt-update.yml` are different files on Linux, and a typo is the single most common cause of this error. The issue tracker has a report of exactly this: one letter missing in the path.

## 2. "chdir ... no such file or directory"

```
Listing playbook hosts failed: chdir /tmp/semaphore/repository_2: no such file or directory
```

The clone directory doesn't exist when the task runs. Causes:

- **`/tmp` cleared between operations.** On some systems `systemd-tmpfiles` or a container restart wipes it. Point Semaphore's temp directory at a persistent path:

```yaml
    environment:
      SEMAPHORE_TMP_PATH: /var/lib/semaphore/tmp
    volumes:
      - semaphore-tmp:/var/lib/semaphore/tmp
```

- **Permissions.** The Semaphore process must be able to create directories there.
- **Disk full.** A failed clone from a full disk leaves nothing behind. `df -h` inside the container.

## 3. The repository can't be cloned

Semaphore requires a **git repository**. A local directory of playbooks is not enough:

```
fatal: repository '/etc/ansible/playbooks' does not exist
```

If you want to use local files, make them a git repo and reference it with a `file://` URL — or better, mount them and point at a path that *is* a repository:

```bash
cd /etc/ansible/playbooks
git init && git add -A && git commit -m "initial"
```

Then the repository URL is `/etc/ansible/playbooks` with the **local** branch, and Semaphore clones from it. The directory must be visible inside the Semaphore container.

For remote repositories:

- **SSH key**: add it under **Key Store** as an SSH key, and select it on the repository. The key must have no passphrase, or Semaphore can't use it unattended.
- **Host key verification.** First clone from an unknown host fails. Semaphore handles this in recent versions; if not, add the host to known_hosts inside the container or use HTTPS with a token.
- **HTTPS with a token**: use a Login/Password key with the token as the password, and a URL of the form `https://git.example.com/user/repo.git`.

Test the clone from inside the container, which removes all ambiguity:

```bash
docker exec -it semaphore git clone <your-repo-url> /tmp/test-clone
```

## 4. "Listing playbook hosts failed"

This runs before the playbook and fails for related but distinct reasons:

- **Inventory path wrong.** Same relative-to-repo-root rule. For a file inventory, `inventory/production.yml`.
- **Inventory type mismatch.** Semaphore inventories can be "static", "static YAML", or "file". A YAML inventory declared as static text won't parse.
- **A dynamic inventory script** needs its interpreter and dependencies present in the Semaphore container, which the default image may not have.

## 5. Dependencies and roles

- **`requirements.yml` is not installed automatically** in all versions. If your playbook uses roles or collections from Galaxy, install them — a task template of type "Galaxy" run before the playbook, or a `pre-task` in your own playbook. A missing role gives "the role ... was not found", not the playbook error, but people conflate them.
- **`ModuleNotFoundError: No module named 'ansible'`** after an upgrade means the image's Python environment changed. Use the official image matching your Semaphore version; don't pip-install Ansible into a running container, because it won't survive a recreate.
- **Custom Python dependencies** (a cloud SDK, `netaddr`, `jmespath`) must be in the image. Build your own:

```dockerfile
FROM semaphoreui/semaphore:latest
USER root
RUN apk add --no-cache py3-netaddr || pip install --break-system-packages netaddr jmespath
USER semaphore
```

## What not to do

- **Don't use absolute host paths in the playbook filename.** Semaphore runs from the clone, not from your filesystem layout.
- **Don't pip-install into a running container** as a permanent fix. Build an image.
- **Don't store SSH keys with passphrases** in the key store expecting them to work unattended.
- **Don't put the temp path on tmpfs** with a small size if you clone large repositories.

## Prevention

| Habit | Why |
|---|---|
| Repo-relative paths, copied from `git ls-files` output | Eliminates typos and case errors |
| Persistent `SEMAPHORE_TMP_PATH` | Removes the vanished-clone class |
| A custom image with your collections and Python deps | Survives upgrades and recreates |
| Test the clone from inside the container when adding a repo | Separates git problems from path problems instantly |

## FAQ

**Can I run a playbook that isn't in a repository?**
Not cleanly. Semaphore's model is repository-driven; make a repo, even a local one.

**Does it support ansible-vault?**
Yes — add the vault password as a key in the Key Store and select it on the template.

**Task output is truncated.**
Semaphore stores output in its database; very verbose runs can be cut. Reduce verbosity or write artefacts to a file the playbook uploads.

**Bash/Python task templates only show YAML files in the picker.**
A known file-picker limitation in some versions. Type the path manually instead of using the picker.
