---
title: "iPhone 18 Pro Keeps Restarting After Face ID? Here's What's Going On"
slug: iphone-18-pro-restarting-face-id-fix
meta_description: "iPhone 18 Pro reboots during Face ID, Apple Pay or a call. What iOS 27.0.1 fixed, what people still report, how to read the panic-full log, and when to ask for a replacement."
updated: October 2026
cluster: E (problem solving) — refreshed in round 9 with the Apple Pay/Wallet reports and panic-full logs
---

# iPhone 18 Pro Keeps Restarting After Face ID? Here's What's Going On

You just got a brand-new iPhone 18 Pro. You try to open an app that's locked with Face ID, like Passwords. Face ID fails. And instead of asking you to try again, the whole phone reboots.

If that's happening to you, you're not alone, and your phone probably isn't broken.

## The short answer

Apple has confirmed the problem. It told 9to5Mac it will "release a software update early next week to fix a problem causing some iPhone 18 Pro and Pro Max units to restart after a failed Face ID attempt."

That points to a software bug, not faulty hardware. The fix is expected to arrive as **iOS 27.0.1**, likely in the last days of September.

**October 2026 update: iOS 27.0.1 shipped on September 19, 2026** with six fixes, covering Wi-Fi, Bluetooth and Face ID problems. For a lot of people that ended it.

**But reports didn't stop.** Owners of iPhone 18 Pro and Pro Max units continue to describe sudden reboots and freezes — and now not only at Face ID:

- During **Apple Pay / payment authorisation**
- When opening **Wallet**
- **During phone calls**
- At **Face ID unlock**, as before

Apple has not confirmed a root cause for this second wave, and users disagree about whether it is still software or a hardware fault in some units. Service centres have handled replacements case by case; there is no recall or published policy.

## What people are reporting

Since the iPhone 18 Pro and Pro Max went on sale on September 18, owners have reported a few related issues:

- **Reboot after a failed Face ID attempt**, mainly when unlocking apps or features that use Face ID (the Passwords app comes up a lot).
- **A "Face ID is Not Available" message** during setup for some users.
- **Crash logs** showing up in Settings after the restart.

Not every iPhone 18 Pro is affected. Plenty of owners haven't seen it at all.

## Read your own panic log — it's the useful evidence

When an iPhone reboots from a system-level failure, iOS writes a **panic-full** log. That's what distinguishes "the OS crashed" from "the battery died" or "I imagined it".

**Settings → Privacy & Security → Analytics & Improvements → Analytics Data**, then scroll to entries beginning **panic-full**. Tap one and note:
- The **date and time** — does it match your reboot?
- The repeated strings near the top (they name the subsystem that failed)

You don't need to interpret it. What matters is that **a panic-full entry exists at the moment your phone restarted**: that is the thing to show at a Genius Bar or in a support chat, and it's much harder to dismiss than a description. Use the share button to export it.

If there is **no** panic-full entry at that time, consider an unexpected shutdown instead (battery, extreme temperature) rather than a kernel panic.

## Software or hardware? How to judge

Treat it as **software** if:
- It only happens in one flow (Face ID in one app, say)
- It started with an update and others with your model report the same
- It stopped after iOS 27.0.1

Push for **hardware service** if, on current iOS:
- It reboots during **several unrelated** things (Face ID, Apple Pay, calls)
- There are **repeated panic-full logs** over days
- It happens on a **clean restore** set up as a new device
- The phone also runs hot, or the screen or finish shows a defect

A brand-new phone that panics repeatedly after a clean restore is a warranty conversation, not a troubleshooting project. Book an appointment, bring the exported logs, and ask for the reboot history to be noted on the case.

## What you can do until the fix arrives

None of these are guaranteed, but they're low-risk and worth trying.

**1. Check for updates first.**
Go to **Settings > General > Software Update**. Install iOS 27.0.1 or later — that's the fix for the original Face ID reboot. Keep installing point releases; later ones are where the remaining reports would be addressed.

**2. Try without your screen protector.**
Some owners report that matte or privacy screen protectors interfere with Face ID. If you're using one, take it off for a day and see if failed attempts go down. Fewer failed attempts means fewer chances to trigger the bug.

**3. Re-register Face ID.**
Go to **Settings > Face ID & Passcode > Reset Face ID**, then set it up again in good lighting. A cleaner scan can mean fewer failed matches.

**4. Use your passcode for locked apps for now.**
If the restart happens mainly with one app, unlock that app with your passcode until the update lands. Annoying, but it avoids the crash.

**5. Back up your phone.**
Random restarts are usually harmless, but it's never a bad moment to make sure iCloud Backup is on.

## When to contact Apple

If any of these apply, don't wait for the update:

- Face ID doesn't work **at all**, even after a restart and reset
- You see **lines on the screen**, discoloration, or physical damage
- The phone restarts constantly, not just after Face ID fails

Those could point to a hardware issue, and a brand-new phone is covered by warranty. Book a Genius Bar appointment or contact Apple Support.

## Should you return your iPhone 18 Pro?

For the Face ID restart bug alone, probably not. Apple has acknowledged it and says a software fix is days away. Bugs like this are common in the first weeks after a big iPhone launch, and they usually get patched quickly.

If you're inside Apple's return window and you're seeing other problems too, that's a different call. Keep an eye on the return deadline for where you bought it.

## FAQ

**Is the iPhone 18 Pro Face ID restart a hardware problem?**
Apple has described it as a problem it will fix with a software update, which suggests it isn't hardware.

**When is iOS 27.0.1 coming out?**
Apple told 9to5Mac a fix would arrive "early next week" from September 24, 2026, which points to around September 28.

**Does this affect the iPhone Duo or older iPhones?**
Reports so far focus on the iPhone 18 Pro and Pro Max.

**Will the update delete my data?**
No. Normal iOS updates keep your data, though a backup is always smart.

---
*Sources: [9to5Mac](https://9to5mac.com/2026/09/24/ios-27-0-1-update-likely-coming-soon-for-iphone-users/), [MacRumors](https://www.macrumors.com/2026/09/21/iphone-18-pro-face-id-issues/), [Macworld](https://www.macworld.com/article/3240287/iphone-18-pro-owners-report-two-serious-bugs-causing-freezes-and-restarts.html)*
