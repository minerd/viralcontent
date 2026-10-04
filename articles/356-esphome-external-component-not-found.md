---
title: "ESPHome: External Component Not Found or Not Loading"
slug: esphome-external-component-not-found
meta_description: "\"Unable to import component\", \"could not find __init__.py\", or a component that silently doesn't refresh. The directory layout and the cache."
updated: October 2026
cluster: round 14 (tech) — esphome/issues GitHub
competition: LOW
---

# ESPHome: External Component Not Found or Not Loading

The error text maps cleanly onto the cause:

| Error | Cause |
|---|---|
| `Could not find __init__.py file for component X` | Directory layout — section 1 |
| `No module named 'esphome.components.X'` | Component name doesn't match the directory |
| `Component not found: X` after it worked | Cache not refreshed — section 3 |
| `the 'custom' component has been removed` | ESPHome 2025.2+ — section 4 |

## 1. The directory layout is strict

For a local component:

```yaml
external_components:
  - source:
      type: local
      path: my_components
    components: [ my_sensor ]
```

ESPHome then expects, relative to your YAML file:

```
my_components/
└── my_sensor/
    ├── __init__.py          # required, may be empty
    ├── sensor.py            # the platform, if it's a sensor platform
    ├── my_sensor.cpp
    └── my_sensor.h
```

Non-negotiable points:

- **`__init__.py` must exist** in the component directory. An empty file is fine. This is the single most common cause.
- **The directory name must equal the component name** you list in `components:` and use in your YAML.
- **C++ files must be `.cpp`**, not `.c`. A `.c` file is compiled as C and the linker then can't find the C++ symbols.
- `path` is relative to the YAML, and in the Home Assistant add-on that means `/config/esphome/`. Mount it accordingly for a Docker install.

For a GitHub source:

```yaml
external_components:
  - source: github://user/repo@main
    components: [ my_sensor ]
    refresh: 1min
```

The repository must have the component under `components/<name>/` at its root, or you must give `path:` within the repo.

## 2. Check the resolved path

```bash
esphome compile device.yaml 2>&1 | grep -iE 'external|component|import'
```

For a Docker install, confirm what the container sees:

```bash
docker exec esphome ls -la /config/esphome/my_components/my_sensor/
```

A path that exists on your laptop and not in the container is the whole problem.

## 3. Changes don't take effect

ESPHome caches fetched components. Editing the upstream repo and recompiling can reuse the old copy:

```yaml
external_components:
  - source: github://user/repo@main
    refresh: 0s        # always re-fetch
```

`refresh: 0s` forces a fetch every compile — slow, but correct while developing. For a local component, use **Clean Build Files** from the dashboard's ⋮ menu, which clears the PlatformIO build cache as well:

```bash
esphome clean device.yaml
esphome compile device.yaml
```

A specific version regression is worth knowing: external components have failed to load or refresh in particular ESPHome releases. If a component that worked stops after an upgrade and the layout is unchanged, pin the previous version before rewriting anything:

```bash
pip install esphome==2026.1.4
```

## 4. The `custom` component is gone

ESPHome removed `custom:` / `custom_component:` in 2025.2. Configurations using it fail outright, and many third-party projects shipped as "custom components" need conversion.

The migration is mechanical but not trivial: a custom component was a C++ class you instantiated with a lambda; an external component is a Python config schema plus code generation plus the same C++. For a component you didn't write, check whether upstream has published an external-component version — most actively maintained ones have.

If you need a stopgap, the old `custom` path exists only on 2025.1 and earlier. Pinning there is a short-term measure, not a plan.

## 5. Compiles but the component misbehaves

- **API changed between ESPHome versions.** Components calling internal APIs break on upgrade; the compile error names the symbol.
- **`fatal error: string: No such file or directory`** — a C++ header included from a file compiled as C, or a missing `#include <string>`. Check the file extensions first.
- **Component loads, no entities appear.** The platform file (`sensor.py`, `switch.py`) didn't register anything. Loading `__init__.py` alone gives you a component with no platforms.

## What not to do

- **Don't copy a component directory and rename only the folder.** The Python module names inside must match.
- **Don't leave `refresh: 0s` in production.** Every compile hits GitHub.
- **Don't edit files inside the ESPHome build cache.** They're regenerated.
- **Don't mix a `custom:` block and external components** on a version where both appear to work. Convert fully.

## Prevention

| Habit | Why |
|---|---|
| Create `__init__.py` first, before anything else | Removes the dominant cause |
| Pin the ESPHome version per device, in a comment | External-component breakage happens on upgrades |
| `esphome clean` after any component change | Cache is the second-most-common cause |
| Keep components in a git repo, referenced by tag | Reproducible builds |

## FAQ

**Can I use a component from a pull request?**
Yes: `source: github://pr#1234` is supported.

**Does `components:` have to list everything?**
Omit it to load all components from the source. Listing them is faster and safer.

**Compiles for ESP32, fails for ESP8266.**
The component may not support the platform. Check its `SUPPORTED_PLATFORMS` or its README.

**Where do I put it for the HA add-on?**
`/config/esphome/<your folder>/`, referenced as a relative `path`.
