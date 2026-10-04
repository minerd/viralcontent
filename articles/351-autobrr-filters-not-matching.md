---
title: "autobrr: Filters Not Matching Releases"
slug: autobrr-filters-not-matching
meta_description: "Releases appear in the feed and nothing is grabbed. Read the rejection reason, understand the AND logic, and fix the anime season-0 case."
updated: October 2026
cluster: round 14 (tech) — autobrr GitHub issues
competition: LOW
---

# autobrr: Filters Not Matching Releases

autobrr tells you exactly why it rejected a release. Most time spent on this problem is time spent not reading that.

```
Settings → Logs → set level to DEBUG
```

Then watch the log while a release comes in:

```
rejected: resolution not matching: got 2160p want [1080p]
rejected: season not matching: got 0 want 1-99
rejected: release group not matching
```

That line is the whole answer. Everything below is about the cases where the message is misleading.

## 1. Every field is ANDed

A filter approves a release only when **every field you filled in matches**. One stray value kills it. The fields people fill in and forget:

- **Resolutions** — leaving 1080p selected while grabbing a 2160p release
- **Seasons / Episodes** — `1-99` in Seasons rejects season packs with no season number, and rejects specials (season 0)
- **Release groups** — a typo, or a group that renamed
- **Minimum / Maximum size** — a size filter set in MB when you meant GB
- **Years** — a year range excluding the release

The practical approach: start with an almost-empty filter (indexer + one must-contain term), confirm it grabs, then add constraints one at a time. Narrowing from a working filter is far faster than widening a broken one.

## 2. The anime absolute-numbering case

This one is a real parsing quirk worth knowing. Anime releases numbered absolutely (`Show - 137 [1080p]`) parse with **season 0**, because there is no season in the name. A filter with Seasons `1-99` therefore rejects them, while the same filter happily takes `S02E05`-style names.

Fix: leave Seasons **empty** for anime filters, and control scope with must-contain terms instead:

```
Match releases: Show Name*
Except releases: *Batch*, *BD*
```

Keep anime in its own filter rather than trying to make one filter serve both naming conventions.

## 3. Indexer-specific name formats

Some trackers put the release group **at the start** of the name:

```
[GroupName] Show Name - 01 (1080p)
```

A "Match releases" pattern of `Show Name*` will not match that, because the string doesn't start with it. Use a leading wildcard:

```
*Show Name*
```

autobrr's match fields are glob-style, not regex, unless you enable the regex option — in which case `.*` replaces `*` and the syntax changes completely. Mixing the two silently matches nothing.

Also: tags that the parser doesn't recognise from an IRC announce (certain containers, some audio formats) leave the corresponding field empty, and a filter requiring that field then rejects. If a container or format filter is rejecting things you can see are correct, clear that field and use a must-contain term on the text instead.

## 4. Duplicate / already-have rejections

```
rejected: already exists in client
```

autobrr checks the download client. Two things to know:

- Duplicate detection compares the release name; two different releases that happen to share a name (different hashes) can be falsely matched. If you're losing legitimate grabs, check whether the "skip duplicates" option is comparing what you expect.
- `Torrent not found in history` on announce means autobrr saw the announce but has no record of the torrent — usually a restart cleared in-memory state. Harmless.

## 5. Nothing arrives at all

Different problem from "not matching". Check **Indexers → the indexer → status**:

- IRC announce: the network must show connected and the announce channel joined. A wrong nick, missing invite command, or an NickServ password failure stops everything.
- RSS/Torznab: the feed must return results. `Settings → Feeds` shows the last run and its error.

If the feed is empty, a tracker-side search filter (freeleech-only, for example) applies to it and legitimately returns nothing.

## What not to do

- **Don't build a 20-field filter and then debug it.** Start minimal.
- **Don't use Seasons on anime filters.** Absolute numbering guarantees rejection.
- **Don't mix glob and regex syntax.** Pick one per filter.
- **Don't run with INFO logging while debugging.** The rejection reasons are at DEBUG.

## Prevention

| Habit | Why |
|---|---|
| One filter per content type and naming convention | Avoids impossible combinations of constraints |
| Build up, never down | Each added constraint is independently testable |
| Keep DEBUG on for new filters, then lower it | The log is the only honest source |
| Note which fields the indexer actually populates | Prevents filters on fields that are always empty |

## FAQ

**Can I test a filter without waiting for an announce?**
Yes — the filter page has a test field where you paste a release name and see the verdict and reason.

**Does it work with *arr apps for the final decision?**
Yes: autobrr can hand the release to Sonarr/Radarr, which applies its own quality profile. A grab rejected there is an *arr problem, not an autobrr one.

**Why did it grab something I didn't want?**
An empty field means "no constraint", not "exclude". Review for blanks.

**Season packs rejected despite being wanted.**
Episode range `1-99` excludes packs. Leave Episodes empty and handle packs in a separate filter.
