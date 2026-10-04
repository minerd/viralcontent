---
title: "DokuWiki: \"Extension Directory Is Not Writable\""
slug: dokuwiki-extension-directory-not-writable
meta_description: "The Extension Manager refuses to install, or complains about bundled plugins. Which directories need write access, and which warnings to ignore."
updated: October 2026
cluster: round 14 (tech) — dokuwiki GitHub issues and dokuwiki.org
competition: LOW
---

# DokuWiki: "Extension Directory Is Not Writable"

The Extension Manager installs by unpacking archives into `lib/plugins/` and `lib/tpl/`. For that, the **web server user** needs write access — and the requirement is narrower than people assume, which matters because over-granting is a real security problem.

## 1. What actually needs to be writable

| Path | Needs write? | Why |
|---|---|---|
| `lib/plugins/` | **Yes** | New plugins are created here |
| `lib/tpl/` | **Yes** | New templates are created here |
| `lib/plugins/<existing>/` | Only to update that plugin | Updating replaces its files |
| `lib/plugins/<bundled>/` | **No** | See section 3 |
| `data/` | **Yes** | Pages, media, meta, cache |
| `conf/` | **Yes** | Config written by the Configuration Manager |

So the minimum for installing extensions:

```bash
cd /var/www/dokuwiki
sudo chown -R www-data:www-data data conf lib/plugins lib/tpl
sudo find data conf lib/plugins lib/tpl -type d -exec chmod 755 {} \;
sudo find data conf lib/plugins lib/tpl -type f -exec chmod 644 {} \;
```

Replace `www-data` with your web server's user (`http` on Arch, `nginx`, `apache`, or the PHP-FPM pool user — which is **not** necessarily the same as the web server's). Find it:

```bash
ps aux | grep -E 'php-fpm|apache|nginx' | grep -v root | head -3
```

A mismatch between the nginx user and the PHP-FPM pool user is a frequent cause: nginx can read, PHP can't write.

## 2. Verify from PHP's point of view

Ownership looking right and PHP still failing usually means something else:

```bash
sudo -u www-data test -w /var/www/dokuwiki/lib/plugins && echo writable || echo NOT
```

- **SELinux** (RHEL/Fedora/Rocky) blocks writes regardless of POSIX permissions:

```bash
sudo setsebool -P httpd_unified 1
sudo semanage fcontext -a -t httpd_sys_rw_content_t '/var/www/dokuwiki/(data|conf|lib/plugins|lib/tpl)(/.*)?'
sudo restorecon -Rv /var/www/dokuwiki
```

- **AppArmor** on Ubuntu for php-fpm, less commonly.
- **`open_basedir`** in PHP restricting paths.
- **An immutable flag or a read-only mount:**

```bash
mount | grep dokuwiki
lsattr -d /var/www/dokuwiki/lib/plugins
```

## 3. The bundled-plugin warning you can ignore

DokuWiki 2025-05 "Librarian" and nearby releases **warn about write permissions for bundled plugins and templates**. This is the known-confusing one.

The warning is not actionable in the way it sounds. Bundled plugins (`authplain`, `config`, `usermanager`, `extension`, `revert`, `popularity`, and the `dokuwiki` template) **can only be updated when DokuWiki itself is updated.** Making their directories writable achieves nothing useful and widens your attack surface.

The correct posture:

- `lib/plugins/` and `lib/tpl/` writable — so new things can be installed
- `lib/plugins/<bundled>/` and `lib/tpl/dokuwiki/` **not** writable — nothing legitimate writes there

Ignore the warning for bundled items. Act on it for third-party plugins you want to update in place.

## 4. Install manually when you'd rather not grant write access

This is a defensible permanent choice for a public wiki: keep `lib/` read-only to the web server and install by hand.

```bash
cd /var/www/dokuwiki/lib/plugins
sudo -u www-data false   # no write needed; you're root here
sudo curl -L -o /tmp/plugin.zip https://github.com/user/dokuwiki-plugin-x/archive/master.zip
sudo unzip -q /tmp/plugin.zip -d /tmp/
sudo mv /tmp/dokuwiki-plugin-x-master /var/www/dokuwiki/lib/plugins/x
sudo chown -R root:www-data /var/www/dokuwiki/lib/plugins/x
sudo find /var/www/dokuwiki/lib/plugins/x -type d -exec chmod 755 {} \;
sudo find /var/www/dokuwiki/lib/plugins/x -type f -exec chmod 644 {} \;
```

**The directory name matters.** A plugin's folder must be named exactly what the plugin expects — usually the plugin's short name, not the repository name. A plugin in a wrongly-named directory loads partially or not at all, with no error. Check the plugin's documentation or its `plugin.info.txt`:

```bash
cat /var/www/dokuwiki/lib/plugins/x/plugin.info.txt
```

The Extension Manager detects and reports missing permissions and tells you to install manually — that message is correct advice, not a failure.

## 5. After any permission change

```bash
# clear the cache so DokuWiki re-reads what's installed
sudo rm -rf /var/www/dokuwiki/data/cache/*
```

Then check **Admin → Extension Manager** lists the plugin, and **Admin → Configuration Settings** shows its options.

## What not to do

- **Don't `chmod -R 777`.** It makes every file world-writable, including `conf/` with your authentication settings. On a wiki reachable from the internet this is a compromise waiting to happen.
- **Don't make bundled plugin directories writable** to silence the warning.
- **Don't make the DokuWiki root writable.** Only `data`, `conf`, `lib/plugins`, `lib/tpl`.
- **Don't edit files as root and leave them root-owned** if the Extension Manager will later update them.

## Prevention

| Habit | Why |
|---|---|
| Write access limited to four directories | Minimum surface, full functionality |
| Confirm the PHP-FPM pool user, not just the web server user | The commonest mismatch |
| `data/` excluded from the web root, or protected | DokuWiki's `.htaccess` does this; nginx needs explicit rules |
| Back up `data/` and `conf/` | Pages, media and configuration; plugins are re-installable |

## FAQ

**Is `data/` really not web-accessible by default?**
Apache's shipped `.htaccess` denies it. **nginx ignores `.htaccess`** — you must add `location ~ /(data|conf|bin|inc|vendor)/ { deny all; }` yourself, or your page sources and config are downloadable.

**Can I run DokuWiki fully read-only?**
Pages need `data/` writable. Everything else can be read-only, which is a good hardening step.

**Extension Manager shows no available plugins.**
It fetches a catalogue from dokuwiki.org; no outbound access means an empty list.

**Plugin installed but does nothing.**
Wrong directory name (section 4), or it needs enabling in Configuration Settings.
