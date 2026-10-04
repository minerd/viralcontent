---
title: "Funkwhale: Imported Music Doesn't Appear"
slug: funkwhale-import-not-showing
meta_description: "In-place import completes and tracks don't show, or won't play. Symlinks that aren't mounted, the two path variables, and missing file tags."
updated: October 2026
cluster: round 14 (tech) — Funkwhale docs, YunoHost forum, SocialHub
competition: LOW
---

# Funkwhale: Imported Music Doesn't Appear

In-place imports have two requirements that, when missed, produce exactly this symptom: the import reports success and the library is empty or unplayable.

## 1. The two path variables must match

```env
MUSIC_DIRECTORY_PATH=/srv/funkwhale/data/music
MUSIC_DIRECTORY_SERVE_PATH=/srv/funkwhale/data/music
```

- **`MUSIC_DIRECTORY_PATH`** is where the *import process* looks for files.
- **`MUSIC_DIRECTORY_SERVE_PATH`** is where the *web server* reads them to stream.

If they differ, the import finds and catalogues the files and playback 404s. The reported fix is simply to set both to the same directory — which is the right answer unless you have a deliberate reason for a split (a container path versus an nginx path), in which case nginx's `internal` location must map accordingly:

```nginx
location /_protected/music/ {
    internal;
    alias /srv/funkwhale/data/music/;
}
```

Tracks appearing in the library and failing to play is the signature of this half.

## 2. Symlinks are not followed into containers

A specific and easily-missed cause: `/srv/funkwhale/data/music` is mounted into the containers, but **symlinked subdirectories inside it are not**. Docker mounts a path, not the targets of symlinks beneath it.

So this looks fine on the host and is empty inside the container:

```
/srv/funkwhale/data/music/
└── albums -> /mnt/bigdisk/music/albums     ← invisible in the container
```

Use **bind mounts** instead, which replicate the directory tree:

```yaml
services:
  api:
    volumes:
      - /srv/funkwhale/data/music:/music:ro
      - /mnt/bigdisk/music:/music/bigdisk:ro
```

or on the host:

```bash
sudo mount --bind /mnt/bigdisk/music /srv/funkwhale/data/music/albums
# and in /etc/fstab for persistence:
# /mnt/bigdisk/music /srv/funkwhale/data/music/albums none bind 0 0
```

Verify from inside:

```bash
docker compose exec api ls -la /music/albums | head
```

An empty listing there is the whole problem, and no Funkwhale setting works around it.

## 3. File tags

Funkwhale builds artists, albums and tracks **entirely from embedded metadata**. Files with missing or incomplete tags cannot be processed, and the import reports an error per file:

```bash
docker compose exec api funkwhale-manage import_files \
  "$LIBRARY_ID" "/music/**/*.flac" --recursive --in-place --async
```

Then read what it said:

```bash
docker compose logs api --tail 100 | grep -iE 'skip|error|import'
```

The minimum usable tag set is artist, album and title. Fix the files before importing rather than after — Funkwhale won't re-read tags on its own:

```bash
# inspect
ffprobe -v error -show_entries format_tags=artist,album,title -of default=nw=1 track.flac
```

For a library with inconsistent tags, running it through **beets** first is far less work than fixing it inside Funkwhale.

## 4. Imported, library tab empty

A version-specific bug: the **tracks tab of a library showed no tracks**, fixed in 1.2.2. If you're below that, upgrade before investigating.

Otherwise:

- **The import is still running.** `--async` queues it to Celery; check the worker:

```bash
docker compose logs celerybeat celeryworker --tail 50
```

A stopped or crashed worker means the import sits in the queue forever and the library stays empty. This is the most common cause after paths.

- **Wrong library ID.** The import targets a specific library UUID; sending files to a library you're not looking at produces exactly this.
- **Visibility.** A library set to "private" shows its content only to you; "me" versus "instance" versus "everyone" affects what other users see, not what you see.

## 5. "Library: This field is required"

An import invoked without a library — the CLI needs the library's UUID as its first argument:

```bash
docker compose exec api funkwhale-manage shell_plus -c \
  "from funkwhale_api.music.models import Library; print([(str(l.uuid), l.name) for l in Library.objects.all()])"
```

Use the UUID, not the name.

## What not to do

- **Don't symlink into the music directory.** Bind mounts only.
- **Don't import untagged files** expecting to fix them in the UI. Tag first.
- **Don't run an import without checking the Celery worker is alive.** It queues silently.
- **Don't use `--in-place` on files you intend to move later.** The database stores paths.

## Prevention

| Habit | Why |
|---|---|
| Both path variables identical | Removes the catalogued-but-unplayable class |
| Bind mounts, never symlinks | The container-visibility problem has no workaround |
| Tag with beets before importing | Funkwhale is tag-driven and won't re-read |
| Watch the Celery worker during imports | Where silent failures live |

## FAQ

**In-place or copy import?**
In-place keeps one copy and means Funkwhale depends on your layout staying put. Copying doubles disk use and decouples them.

**Can I re-scan for tag changes?**
`funkwhale-manage import_files` again over the same files updates metadata in recent versions; older ones need the tracks removed first.

**Federation shows my library elsewhere but not locally.**
Then the files are catalogued and the serve path is wrong — section 1.

**Does it transcode?**
Yes, on demand, if the transcoding settings are enabled and ffmpeg is present.
