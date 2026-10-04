---
title: "Storyteller: Read-Aloud Sync Is Wrong or Unavailable"
slug: storyteller-read-aloud-sync-wrong
meta_description: "Chapters mapped to the wrong audio, drift through the book, or sync unavailable entirely. Duration metadata, forced alignment limits and clean sources."
updated: October 2026
cluster: round 14 (tech) — Storyteller GitLab and BookOrbit GitHub issues
competition: LOW
---

# Storyteller: Read-Aloud Sync Is Wrong or Unavailable

Storyteller aligns an audiobook to an ebook by **forced alignment** — transcribing the audio and matching it to the text. Understanding that sets realistic expectations and points at the right fixes.

Three failures:

| Symptom | Cause |
|---|---|
| Read-aloud unavailable; no sync option offered | Media-overlay duration not detected — section 1 |
| One chapter maps to the wrong place, others fine | Chapter boundary detection — section 2 |
| Highlighting drifts progressively | Proportional scaling / alignment drift — section 3 |

## 1. "Read-aloud progress sync is unavailable"

The documented cause: **the Storyteller EPUB's media-overlay duration is not properly detected.**

A related reported case: a Storyteller read-aloud EPUB paired with a standalone audiobook where the M4B shows 23h 34m and the read-along EPUB shows 23h 23m — **the difference being un-narrated credit tracks.** The reader can't reconcile the two durations and disables sync.

What to do:

- **Remove non-narrated tracks before processing.** Publisher credits, "end of book" announcements and sample chapters are not in the text and corrupt the duration and the alignment:

```bash
# inspect the tracks
for f in *.m4b *.mp3; do
  printf '%s  ' "$f"
  ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"
done
```

Drop the ones that aren't the book.

- **Check the generated EPUB's declared duration:**

```bash
unzip -p storyteller-output.epub '*.smil' | grep -o 'clipEnd="[^"]*"' | tail -3
unzip -l storyteller-output.epub | grep -i smil | head
```

The SMIL files carry the media overlay. Missing or zero-duration entries mean the alignment produced nothing usable for those sections.

- If you're **bridging a Storyteller EPUB to a separate M4B** in another app, expect this: the two files must agree on duration. Using the single Storyteller-produced EPUB with its embedded audio avoids the whole question.

## 2. A chapter mapped to the wrong place

Reported precisely: **Chapter 4 of the audiobook mapped to the Table of Contents instead of the correct chapter**, while other chapters matched correctly.

Causes:

- **The EPUB's TOC contains entries with no corresponding audio** — a title page, a dedication, a map. Alignment tries to match them and consumes audio that belongs to the next real chapter.
- **Chapter titles read aloud differently** from the text ("Chapter Four" versus "4"), which the transcription matches poorly.
- **An audio file boundary not at a chapter boundary** — a multi-file audiobook where file 3 contains the end of chapter 3 and the start of chapter 4.

Fixes, in order of effectiveness:

- **Give it chapterised audio.** A single M4B with correct chapter markers aligned to the text's chapters is dramatically more reliable than loose MP3s. Add markers with a tagger if the file lacks them.
- **Strip front matter from the EPUB** that has no narration, or at least ensure it isn't in the spine as a separately-aligned unit.
- **Re-run alignment** after either change; the result is deterministic for a given input, so re-running the same input gains nothing.

## 3. Progressive drift

> **Forced alignment tools are prone to synchronisation drift, which can result in misalignment between text highlighting and audio, sometimes leading to audio truncation or time-stretching artefacts.**

Drift accumulates when alignment is interpolated across a long span rather than anchored frequently. The structural fix, which the project has discussed, is **chapter-by-chapter alignment instead of proportional scaling** — anchoring at every chapter boundary so errors can't accumulate across the book.

What you can do now:

- **More, shorter audio files** (one per chapter) give more anchors. This is the single most effective change.
- **Clean sources matter more than anything else.** Storyteller works best with clean source files; **long musical intros** and formatting irregularities in the ebook both degrade alignment.
- Trim music and silence from the head of each file.

```bash
# trim leading silence
ffmpeg -i chapter01.mp3 -af "silenceremove=start_periods=1:start_duration=0.5:start_threshold=-50dB" \
       -c:a aac -b:a 64k chapter01-trimmed.m4a
```

## 4. Matching the right ebook to the right audiobook

Mismatches that look like alignment failures:

- **Abridged audio against an unabridged ebook.** Alignment will fail badly and there is nothing to fix.
- **Different editions** — a revised text against older narration, or a translation.
- **A dramatised/full-cast production** with sound effects and non-text material.

Check total durations as a sanity test before processing: an audiobook should be roughly the word count divided by about 150 words per minute. A 20% discrepancy means a different edition.

## 5. Processing is slow or fails

Alignment transcribes the entire audiobook. That is genuinely expensive:

- Expect hours per book on CPU.
- Memory matters; a 20-hour audiobook processed in one pass needs real RAM.
- Per-chapter files also help here — each is a smaller unit of work and a failure doesn't lose the whole book.

## What not to do

- **Don't feed it a single 20-hour file** with no chapter markers if you care about accuracy.
- **Don't include credits and sample chapters** in the audio.
- **Don't pair abridged audio with unabridged text.** No tool fixes that.
- **Don't re-run alignment on unchanged input** expecting a different result.

## Prevention

| Habit | Why |
|---|---|
| One audio file per chapter, markers correct | More anchors, less drift, recoverable failures |
| Non-narrated tracks removed before processing | Fixes both duration detection and chapter mapping |
| Matching editions verified by duration estimate | Catches abridged/wrong-edition pairs early |
| Keep the source files | Re-processing with better inputs is the main remedy |

## FAQ

**Does it need a GPU?**
It benefits substantially from one for the transcription step; CPU works and is slow.

**Can I correct alignment by hand?**
The SMIL timings are editable in the produced EPUB, which is viable for one bad chapter and impractical for a whole book.

**Which readers support it?**
Readers that implement EPUB media overlays, including Storyteller's own app. Support elsewhere is patchy.

**Is this the same as Whispersync?**
Conceptually yes; this is the self-hosted equivalent, with the alignment done locally on files you own.
