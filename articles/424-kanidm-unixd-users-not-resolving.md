---
title: "kanidm-unixd: Users Not Resolving, SSH Keys Ignored"
slug: kanidm-unixd-users-not-resolving
meta_description: "getent finds nothing, or sshd ignores Kanidm's AuthorizedKeysCommand. The systemd-userdbd conflict, nsswitch order and the resolver restart."
updated: October 2026
cluster: round 14 (tech) — kanidm/kanidm GitHub issues
competition: LOW
---

# kanidm-unixd: Users Not Resolving, SSH Keys Ignored

Two separate integrations fail in two separate ways. Decide which you have:

```bash
getent passwd alice@idm.example.com
getent passwd alice
```

- **`getent` returns nothing** → NSS (section 1)
- **`getent` works, SSH key auth fails** → the `AuthorizedKeysCommand` conflict (section 3)

## 1. NSS configuration and order

```
# /etc/nsswitch.conf
passwd: kanidm compat
group:  kanidm compat
shadow: files kanidm
```

The documented ordering rule: **`kanidm` goes before `compat` or `files`**, because the kanidm resolver caches and also serves content from local files. Putting it after means local lookups shadow Kanidm entries, and anything not in `/etc/passwd` may not be reached depending on the lookup.

Then confirm the daemons are up — there are two:

```bash
systemctl status kanidm-unixd
systemctl status kanidm-unixd-tasks
```

`kanidm-unixd` answers lookups; `kanidm-unixd-tasks` creates home directories and manages symlinks. A working `getent` with no home directory on login is `kanidm-unixd-tasks` not running — a distinct and commonly-missed half.

Configuration:

```toml
# /etc/kanidm/unixd
pam_allowed_login_groups = ["posix_users"]
default_shell = "/bin/bash"
home_prefix = "/home/"
home_attr = "uuid"
home_alias = "spn"
uid_attr_map = "spn"
gid_attr_map = "spn"
```

```toml
# /etc/kanidm/config
uri = "https://idm.example.com"
verify_ca = true
```

`pam_allowed_login_groups` is a gate: a user who resolves but isn't in one of these groups cannot log in, and the PAM message is unhelpfully generic.

## 2. "Stops returning users after a while"

A documented behaviour: `getent passwd <user>` hangs briefly, then reports the user cannot be found, and **restarting `kanidm-unixd` fixes it.**

```bash
sudo systemctl restart kanidm-unixd
```

Causes and mitigations:

- The resolver's connection to the Kanidm server dropped and the cache expired. Check connectivity and the server's own health.
- Certificate problems surface this way too — an expired or rotated CA makes every refresh fail while the cache serves until it doesn't:

```bash
kanidm-unixd-status
journalctl -u kanidm-unixd -n 60 --no-pager | grep -iE 'error|tls|cert|timeout'
```

- As a pragmatic safety net, a periodic health check that restarts the resolver on failure is reasonable until the underlying cause is found.

Also worth knowing: `/v1/account/999/_unix/_token` appearing in server logs is the resolver looking up an id it has cached; stray entries for nonexistent accounts are noise rather than a fault.

## 3. The systemd-userdbd / sshd conflict

This is the specific, high-value one.

**sshd does not support multiple `AuthorizedKeysCommand` directives.** Whichever configuration fragment loads first wins. `systemd-userdbd` drops in a fragment using:

```
AuthorizedKeysCommand /usr/bin/userdbctl ssh-authorized-keys %u
```

If that loads **before** Kanidm's fragment, Kanidm's command never runs and SSH key authentication against Kanidm silently does nothing — password auth may still work, which makes it look like a key problem.

The fix is ordering. Install Kanidm's fragment with a name that sorts first:

```
# /etc/ssh/sshd_config.d/10-kanidm.conf
AuthorizedKeysCommand /usr/bin/kanidm_ssh_authorizedkeys %u
AuthorizedKeysCommandUser nobody
```

```bash
ls -la /etc/ssh/sshd_config.d/
# 10-kanidm.conf must sort before whatever systemd dropped in
sudo sshd -T | grep -i authorizedkeyscommand
```

`sshd -T` prints the **effective** configuration — that single command tells you which command sshd will actually run, and is the fastest way to confirm the fix.

Test the command directly:

```bash
sudo -u nobody /usr/bin/kanidm_ssh_authorizedkeys alice@idm.example.com
```

It should print the user's public keys. Nothing means the resolver can't reach the server, or the user has no keys uploaded.

Note `AuthorizedKeysCommandUser nobody` — the command runs as an unprivileged user, so the unixd socket must be readable by it. That's the default packaging; a hardened umask on `/var/run/kanidm-unixd/` breaks it.

## 4. Home directories not created

```bash
systemctl status kanidm-unixd-tasks
journalctl -u kanidm-unixd-tasks -n 40 --no-pager
```

Reported: `err=PAM_SUCCESS` with no home directory created. Authentication succeeded and the tasks daemon didn't act.

- The tasks daemon must be running **and** have write access to `home_prefix`.
- `pam_mkhomedir` and kanidm-unixd-tasks both trying to create homes conflict; use one.
- SELinux can block creation under `/home` with correct POSIX permissions.

## 5. Service accounts and reserved names

A documented limitation: creating a service account named **`root`** is not possible, and by extension Kanidm will not shadow critical local accounts. That's deliberate — the `compat`/`files` entry in nsswitch keeps local root resolvable regardless, which is what you want when the IdP is unreachable.

Keep a local break-glass account with a password and sudo rights. An IdP outage with no local account means console access only.

## What not to do

- **Don't put `kanidm` after `files` in nsswitch.** Ordering is documented for a reason.
- **Don't add a second `AuthorizedKeysCommand`.** sshd takes one; verify with `sshd -T`.
- **Don't rely solely on Kanidm for host login.** Keep a local admin.
- **Don't skip `kanidm-unixd-tasks`.** Half the integration lives there.

## Prevention

| Habit | Why |
|---|---|
| `sshd -T | grep authorizedkeyscommand` after any change | Shows the effective config, not the intended one |
| Both unixd daemons enabled and monitored | Lookups and home directories are separate |
| Local break-glass account on every host | IdP outages happen |
| `kanidm-unixd-status` in your checks | Surfaces cache and connection state early |

## FAQ

**Does it work with sudo?**
Yes, via PAM and group membership. Grant sudo by group in `/etc/sudoers.d/`.

**Offline authentication?**
The resolver caches credentials for a configurable period, so a host can authenticate known users during an outage.

**Can I use short usernames instead of `user@domain`?**
With `uid_attr_map = "name"`, yes — at the cost of collision risk across domains.

**SSSD instead?**
Kanidm's own resolver is the supported path and is simpler. SSSD against Kanidm's LDAP interface is possible and less well-trodden.
