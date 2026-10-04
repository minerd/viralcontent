---
title: "InvenTree: Custom Plugin Not Discovered or Not Loading"
slug: inventree-plugin-not-loading
meta_description: "A plugin doesn't appear in the plugin table, or stops loading after a container rebuild. __init__.py, the plugin file hash, and static file collection."
updated: October 2026
cluster: round 14 (tech) — inventree/InvenTree GitHub issues and docs
competition: LOW
---

# InvenTree: Custom Plugin Not Discovered or Not Loading

If a plugin isn't in **Settings → Plugins**, InvenTree doesn't know it exists. That's a discovery problem, and it has a short checklist. If it *is* listed and fails when activated, that's a different problem.

## 1. The `__init__.py` requirement

Discovery walks the plugin directory as a **Python package tree**, so empty `__init__.py` files are mandatory:

```
plugins/
├── __init__.py                 ← required
└── my_plugin/
    ├── __init__.py             ← required
    ├── core.py
    └── version.py
```

Both. A missing `__init__.py` in either place makes the plugin invisible with no error anywhere — it is the single most common cause of "not discovered".

Then enable plugin loading at all:

```yaml
environment:
  INVENTREE_PLUGINS_ENABLED: "True"
  INVENTREE_PLUGIN_DIR: /home/inventree/data/plugins
```

```bash
docker exec inventree-server ls -la /home/inventree/data/plugins/
docker exec inventree-server ls -la /home/inventree/data/plugins/my_plugin/
```

## 2. Plugins installed from a requirements file

InvenTree can install plugins from `plugins.txt`:

```
# data/plugins.txt
inventree-brother-plugin==1.1.0
git+https://github.com/user/inventree-my-plugin@v0.3.0
```

Here is the trap, and it's a documented one: InvenTree stores a **hash of `plugins.txt`** and skips installation when the hash is unchanged. After replacing the container, the hash still matches the file — **but the Python environment is new and the packages aren't there**. InvenTree returns early, installs nothing, and the plugins are gone.

Force it:

```bash
docker exec inventree-server invoke int.plugins --force
# or, depending on version
docker exec inventree-server invoke update
```

Or defeat the hash by touching the file meaningfully (adding a comment with a date works). This is why plugins "disappear" after an image update — it's not a plugin bug, it's the cache.

Persist the Python environment across container replacements if you can: mount the site-packages directory, or bake your plugins into a custom image:

```dockerfile
FROM inventree/inventree:stable
COPY plugins.txt /tmp/plugins.txt
RUN pip install --no-cache-dir -r /tmp/plugins.txt
```

That removes the problem entirely and is the right answer for a production instance.

## 3. Static file collection and concurrency

A reported issue with real consequences: `collect_plugins_static_files()` has **no locking**, so concurrent `django-q` worker processes can corrupt the plugin static output. Each process sees a hash mismatch, all of them collect at once, and the resulting files are interleaved.

Symptoms: a plugin loads, its backend works, and its UI panels are blank or throw JavaScript errors.

Mitigation:

- **Run a single worker during startup**, or stagger worker start.
- After a plugin change, collect statics once explicitly and then start workers:

```bash
docker exec inventree-server invoke static
docker compose restart inventree-worker
```

- If panels are broken, clear the static output and re-collect rather than reinstalling the plugin.

## 4. Listed but errors on activation

```bash
docker logs inventree-server --tail 100 | grep -iE 'plugin|error|traceback'
```

- **`ModuleNotFoundError: No module named 'django'`** at any point means the virtual environment isn't active — a bare-metal install problem, not a plugin one.
- **An internal server error right after activating a plugin** (reported for the barcode plugins) usually means a migration the plugin needs hasn't run:

```bash
docker exec inventree-server invoke update
```

- **API version mismatch.** Plugins declare a minimum InvenTree version; one written against a newer API throws attribute errors on an older server. The plugin's metadata should say, and InvenTree's error names the missing symbol.

## 5. Plugin loads, settings don't appear

Plugin settings are registered by the plugin's mixin. If the settings page is empty:

- The plugin must inherit `SettingsMixin` and define `SETTINGS`
- A syntax error in that dict prevents registration without failing the load
- Settings are cached; reload the plugin registry:

```
Settings → Plugins → Reload plugins
```

## What not to do

- **Don't edit `plugins.txt` and assume it installed.** Check the plugin table and the log.
- **Don't rely on the pip environment surviving an image update.** Bake plugins into an image, or force reinstall.
- **Don't run several workers through a plugin static collection.** Collect first, then start them.
- **Don't install plugins from untrusted sources.** They run with full server privileges and database access.

## Prevention

| Habit | Why |
|---|---|
| `__init__.py` created first, in both directories | Removes the dominant discovery failure |
| Custom image with plugins baked in | Immune to the hash/environment mismatch |
| `invoke static` after plugin changes, before starting workers | Avoids corrupted plugin UI |
| Pin plugin versions in `plugins.txt` | Reproducible, and upgrades become deliberate |

## FAQ

**Where do custom plugins live for a Docker install?**
Under `INVENTREE_PLUGIN_DIR` on a mounted volume, or installed as pip packages.

**Can a plugin add database tables?**
Yes, with migrations, via the appropriate mixin. Those need `invoke update` to apply.

**Does disabling a plugin remove its data?**
No. Its settings and any tables remain.

**Plugin works in development and not in Docker.**
Nine times out of ten the directory isn't mounted where `INVENTREE_PLUGIN_DIR` points. Check from inside the container.
