---
title: "iOS 27 Stuttering With Tinted or Clear Icons? The ProMotion Bug Explained"
slug: ios-27-tinted-icons-stutter
meta_description: "App Switcher and Home Screen jitter on iOS 27 when tinted or clear app icons are on, on 120 Hz iPhones. Why it happens, the workaround, and which devices are spared."
updated: October 2026
cluster: round 9 (tech) — one MacRumors forum thread and a general bug round-up
competition: LOW
---

# iOS 27 Stuttering With Tinted or Clear Icons? The ProMotion Bug Explained

If your iPhone's **App Switcher judders** and the Home Screen animations feel broken since iOS 27, check one setting before you blame the phone: your **app icon style**.

**The reported bug:** on **ProMotion (120 Hz) iPhones**, turning on **tinted or clear app icons** makes the App Switcher stutter badly. With the default light or dark icons, the same device animates smoothly. It reportedly affects all ProMotion models **except the iPhone 18 Pro and 18 Pro Max**, and it was still present as of iOS 27.0.1.

## How to confirm it on your phone

1. Long-press the Home Screen → **Edit → Customize**
2. Note which icon style is selected: **Light / Dark / Automatic / Tinted / Clear**
3. If it's **Tinted** or **Clear**, switch to **Light** or **Dark**
4. Swipe up to the App Switcher a few times and compare

If the jitter goes away with default icons and comes back with tinted or clear, you've reproduced the bug. That's useful to know — it means nothing is wrong with your hardware.

## The workaround

**Use default (light/dark/automatic) icons** until Apple ships a fix. That's the whole fix available today.

If you want to keep the tinted look and live with some jitter, two things reduce it:

- **Fewer icons per page.** A very crowded Home Screen makes launch animations stutter on its own, separately from this bug. Move apps into folders or onto later pages, and lean on Spotlight and the App Library
- **Accessibility → Motion → Reduce Motion: on**, and **Display & Text Size → Reduce Transparency: on**. Both cut the amount of per-frame compositing work

## Why icon style costs performance at all

Tinted and clear icons aren't just recoloured images. iOS re-derives them from each app's icon layers and composites them against a translucent, blurred background that samples the wallpaper underneath — live, as things move. At 120 Hz that compositing has a 8.3 ms budget per frame. Miss it and you see exactly what people are describing: smooth most of the time, then a visible hitch during big transitions like the App Switcher.

That also explains why the newest Pro models appear unaffected: more GPU headroom and a newer display pipeline absorb the extra work.

## Related iOS 27 interface complaints (different causes)

- **Touchscreen briefly unresponsive** — widely reported on iOS 27, separate from the icon bug
- **Keyboard lag in Messages** — tied to keyboard haptics for many people
- **Auto-brightness misbehaving** — try toggling it, cleaning the ambient-light sensor area, and turning off True Tone/Night Shift to test
- **General post-update sluggishness** for the first day or two while the phone re-indexes

If you have several of these at once, do a full restart, then change one thing at a time.

## What not to bother with

- **Reset All Settings** or a DFU restore for this specific issue — it's a software bug in the compositor path, not your configuration
- Battery replacement
- Third-party "speed up iOS" utilities

## FAQ

**Which iPhones are affected?**
ProMotion (120 Hz) models, per user reports, with the iPhone 18 Pro and Pro Max apparently spared. 60 Hz models don't show it the same way.

**Is it fixed in iOS 27.0.1?**
Reports say no. Watch later point releases.

**Does Reduce Motion fix it?**
It reduces the amount of animation work, so it helps, but it doesn't remove the underlying stutter.

**Do tinted icons slow down anything else?**
They add compositing work generally, which is why a very full Home Screen plus tinted icons feels worst.
