---
title: "beets: \"No matching release found\" When the Album Exists"
slug: beets-no-matching-release-found
meta_description: "The import finds nothing for an album that's clearly in MusicBrainz. Plugin list, the Various Artists regression, and the match thresholds."
updated: October 2026
cluster: round 14 (tech) — beets GitHub issues and Discourse
competition: LOW
---

# beets: "No matching release found" When the Album Exists

Four causes, and the first two explain most of it.

## 1. Is the musicbrainz plugin even enabled?

Since beets split MusicBrainz into a plugin, it must appear in your plugin list. Without it, beets has no metadata source and reports no match for everything:

```yaml
plugins: musicbrainz fetchart embedart lastgenre scrub
```

```bash
beet version
beet config -d | head -20
```

`beet version` lists the loaded plugins. If `musicbrainz` isn't there, that's the answer. This catches people upgrading from older versions where it was built in.

## 2. The Various Artists regression

A specific, real bug worth knowing: in some 2.6.x releases, an album detected as **Various Artists** never invoked the MusicBrainz plugin at all. The symptom is distinctive — the import reports no match **immediately**, with zero candidates evaluated, while single-artist albums in the same run match fine.

```bash
beet -vv import ~/music/album 2>&1 | grep -iE 'candidate|musicbrainz|search'
```

Verbose output showing no search request at all (rather than a search returning nothing) confirms it. Workarounds: pin the previous minor version, or use `I` at the prompt to enter the MusicBrainz release ID by hand.

```bash
pip install 'beets==2.5.1'
```

## 3. Match thresholds and required fields

```yaml
match:
  strong_rec_thresh: 0.10
  medium_rec_thresh: 0.25
  rec_gap_thresh: 0.25
  max_rec:
    missing_tracks: medium
    unmatched_tracks: medium
  preferred:
    countries: ['GB', 'US']
    media: ['CD', 'Digital Media']
  required: []
```

The one to check: **`required`**. A config with `required: [label]` or `required: [year]` discards every candidate that lacks that field, and MusicBrainz releases often do. An empty `required` is the sane default.

Also:

- **`distance_weights`** heavily skewed will push everything past the threshold.
- **`strong_rec_thresh`** too low (strict) means candidates are found but never auto-applied, so a non-interactive import reports no match. Look at the output: "no matching release" is different from "candidates found, none strong enough".

## 4. The tags beets searches with

beets queries MusicBrainz using the tags already in your files, and it only evaluates the top few results. Files with empty or wrong tags produce a search that finds nothing useful.

The fixes, in increasing effort:

```
# at the import prompt
E   enter search  (type artist and album by hand)
I   enter ID      (paste a MusicBrainz release MBID or URL)
```

Entering the ID is decisive and takes ten seconds — use it for any album you know exists. For a directory of untagged files, also consider:

```bash
beet import -s ~/music/album     # singleton mode, per-track matching
beet import -C ~/music/album     # don't copy, match in place
```

And the structural cause: **one album per directory**. A directory containing two albums, or an album split across two directories, cannot match a single release. beets groups by directory first, so fixing the layout fixes a surprising number of "no match" cases.

Disc-split albums need either all discs in one directory or `per_disc_numbering`:

```yaml
per_disc_numbering: yes
```

## 5. When the release genuinely isn't in MusicBrainz

Then nothing will match it, and that's correct. Options:

- Add it to MusicBrainz. It's the upstream data source for most music tooling, and the edit takes a few minutes.
- Import as-is: `U` at the prompt (use as-is) keeps your existing tags and still files the album into your library structure.
- Use a different metadata source plugin (Discogs, Spotify) alongside MusicBrainz:

```yaml
plugins: musicbrainz discogs
```

Multiple sources means more candidates; it also means slower imports and occasionally worse matches.

## What not to do

- **Don't lower `strong_rec_thresh` to force matches.** You'll silently apply wrong metadata to your library, which is much harder to undo than a skipped album.
- **Don't run a large import non-interactively the first time.** `--quiet` applies strong matches and skips the rest, and you won't know what it did.
- **Don't let beets move files until you've tested on a copy.** `beet import -C` matches in place.
- **Don't fight one album for an hour.** `I` with the MBID ends it.

## Prevention

| Habit | Why |
|---|---|
| `required: []` in config | Removes the most common invisible filter |
| One album per directory, before importing | beets groups by directory |
| Pin the beets version in your notes | Metadata-source regressions have shipped |
| Keep `-vv` handy | Distinguishes "no search" from "no results" |

## FAQ

**Can I re-run the matcher on an already-imported album?**
`beet import -L album:"Name"` re-imports from the library.

**Does it edit my files?**
Yes — it writes tags and (by default) moves/copies files. `-C` and `write: no` change that.

**Why is it so slow?**
MusicBrainz rate-limits to roughly one request per second. A large import is genuinely hours. Running a local MusicBrainz mirror removes the limit.

**Singletons all fail to match.**
Single tracks have far less to match on. `-s` with good artist/title tags is the best you can do.
