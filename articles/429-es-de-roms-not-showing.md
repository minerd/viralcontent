---
title: "ES-DE: ROMs or Custom Collections Not Showing"
slug: es-de-roms-not-showing
meta_description: "Games missing from a system, or custom collections empty after a move. The gamelist-only setting, %ROMPATH% portability and orphaned entries."
updated: October 2026
cluster: round 14 (tech) — ES-DE user guide and GitLab
competition: LOW
---

# ES-DE: ROMs or Custom Collections Not Showing

ES-DE builds its view from two sources: the files on disk and `gamelist.xml`. Which one wins depends on a setting most people don't know is there.

## 1. "Only show games from gamelist.xml files"

```
Menu → Other Settings → Only show ROMs from gamelist.xml files
```

With this **on**, ES-DE loads whatever is in the gamelists **regardless of whether the files exist**, and ignores everything not listed. Consequences:

- A game you added to the ROM directory but never scraped does not appear.
- Games you deleted still appear, and launching them fails.
- The `noload.txt` logic is bypassed entirely.

With it **off**, ES-DE scans the directories and shows what's there.

So: games missing while the files are definitely present, and you recently scraped — check this setting first. It's the single most common cause of this symptom and it's a one-click fix.

## 2. Check the log

```
~/.emulationstation/es_log.txt
# or, newer versions:
~/ES-DE/logs/es_log.txt
```

```bash
grep -iE 'warn|error' ~/ES-DE/logs/es_log.txt | head -40
```

The warnings are specific and name files:

```
Warning: ROM file "/roms/snes/Game.sfc" referenced in gamelist.xml does not exist
Warning: Couldn't find emulator "RetroArch" for system "snes"
```

The documented cause of orphaned entries: **removing game files from the ROMs directory manually instead of deleting them through ES-DE's metadata editor** leaves gamelist entries, scraped media and custom collection entries pointing at nothing. Those produce exactly these warnings on every startup.

Clean them with the metadata editor, or edit the gamelist:

```bash
# back up first
cp ~/ES-DE/gamelists/snes/gamelist.xml ~/gamelist.snes.bak
```

## 3. Custom collections become non-portable

The documented rule: using **hardcoded paths instead of the `%ROMPATH%` variable** in custom systems makes custom collections non-portable, because every game is stored with an absolute path. Move your ROMs and every collection entry breaks.

```xml
<!-- es_systems.xml — portable -->
<system>
  <name>snes</name>
  <path>%ROMPATH%/snes</path>
  <extension>.sfc .smc .zip .7z</extension>
  <command>%EMULATOR_RETROARCH% -L %CORE_RETROARCH%/snes9x_libretro.so %ROM%</command>
</system>
```

```xml
<!-- non-portable: avoid -->
  <path>/home/user/games/snes</path>
```

Custom collection files live in:

```bash
ls ~/ES-DE/collections/
cat ~/ES-DE/collections/custom-favourites.cfg
```

They contain one path per line. If they're absolute and your ROM path changed, a bulk rewrite fixes them:

```bash
cd ~/ES-DE/collections
cp -a . ../collections.bak
sed -i 's|/old/path/roms|%ROMPATH%|g' *.cfg
```

Whether `%ROMPATH%` is honoured in collection files depends on version — check one entry after editing. If it isn't, use the new absolute path rather than the variable.

## 4. System doesn't appear at all

ES-DE hides a system when its directory contains no matching files:

- **Extension not listed.** A `.chd` in a system whose `<extension>` list lacks it is invisible. Check `es_systems.xml` for that system.
- **Directory name mismatch.** The directory must match `<path>` exactly, case included on Linux.
- **The emulator isn't found.** A system with no resolvable emulator is skipped with a log warning. `%EMULATOR_X%` entries resolve against `es_find_rules.xml`; a custom install location needs an entry there.

```bash
grep -A5 '<system>' ~/ES-DE/custom_systems/es_systems.xml | head -40
```

Put customisations in `custom_systems/`, not in the bundled file — the bundled one is replaced on update.

## 5. Media (boxart, videos) missing

Separate from games missing. Scraped media lives in a directory structure mirroring the ROMs:

```
~/ES-DE/downloaded_media/snes/covers/Game.jpg
~/ES-DE/downloaded_media/snes/screenshots/Game.jpg
```

The filename must match the ROM's base name exactly. Reported for ROMs in a **custom location**: media not found because the media directory path didn't follow. Set it explicitly:

```
Menu → Other Settings → Media Directory
```

Rename a ROM and its media no longer matches — rename both, or re-scrape.

## 6. Android and other platforms

ES-DE's paths differ by platform, and a guide for one misleads on another. On Android the ROM and media directories are chosen during setup and stored differently; on Windows the default is under the user profile. Always check what your install reports:

```
Menu → Other Settings → (the paths are shown)
```

## What not to do

- **Don't delete ROM files from the filesystem.** Use the metadata editor, or expect orphaned entries and warnings.
- **Don't hardcode paths in `es_systems.xml`.** Use `%ROMPATH%`.
- **Don't edit the bundled `es_systems.xml`.** Your changes vanish on update; use `custom_systems/`.
- **Don't leave "only show games from gamelist.xml" on** unless you specifically want a curated, scrape-driven library.

## Prevention

| Habit | Why |
|---|---|
| `%ROMPATH%` everywhere | Collections and systems survive a move |
| Customisations in `custom_systems/` only | Survives updates |
| Delete games through ES-DE | No orphans, no warnings |
| Back up `gamelists/`, `collections/` and `custom_systems/` | Everything you curated, none of it regenerable |

## FAQ

**Does it scrape automatically?**
No — scraping is a deliberate action from the menu, per system or per game.

**Can two front ends share a gamelist?**
Formats differ between ES-DE, EmulationStation forks and others. Expect to scrape per front end.

**Why is a game listed twice?**
Two files matching the same game (a `.zip` and an extracted `.sfc`), or a gamelist entry plus a real file with a different name. Restrict extensions per system.

**Folders instead of games?**
Multi-disc and multi-file games are commonly stored in folders; set the folder's metadata and use `.m3u` playlists for multi-disc.
