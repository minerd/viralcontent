---
title: "Fugleramme: The Raspberry Pi Frame That Hears Birds and Draws Them Like It's 1850"
slug: fugleramme-raspberry-pi-bird-frame
meta_description: "Fugleramme listens for birds, identifies them with local AI, and shows each one as a vintage hand-cut illustration on an e-ink frame. What you need to build one and how it works."
updated: September 2026
cluster: Hacker News viral (top Show HN of the month) — LOW-MEDIUM competition
competition: LOW-MEDIUM
---

# Fugleramme: The Raspberry Pi Frame That Hears Birds and Draws Them Like It's 1850

Some tech projects are useful. Some are impressive. Every so often, one is just lovely.

**Fugleramme** is a picture frame that listens to the birds outside your window, figures out which species are singing, and displays them as real **1800s natural-history illustrations**. It became the most upvoted Show HN on Hacker News in September, with over 2,300 points.

Here's how it works and what you'd need to build one.

## What it does

In the creator's words: "Bird frame for Raspberry Pi - real-time bird detection by audio, fully local AI, rendered as real, hand-cut 1800s bird illustrations."

The loop is simple:
1. A **microphone** listens outside.
2. **BirdNET-Go**, a bird-sound recognition system, identifies the species.
3. The software finds a matching vintage illustration.
4. The frame displays the birds, arranged on textured "paper" and **sized by body mass**, so a crow looks bigger than a wren.

The frame only updates when the birds it hears change, which suits e-ink displays perfectly.

**Everything runs locally.** No cloud, no subscription, no app.

## The artwork

This is what makes it special. The project includes **more than 800 hand-curated cutouts** from **public-domain natural-history plates**, covering **over 400 species**. Each bird is cut out from its original background and placed on the page.

The collection leans toward **Scandinavian, British and Central European** birds. If you live elsewhere, some local species may not have an illustration yet.

## What you need

The reference build uses:
- **Raspberry Pi 5**
- **Inky Impression 13.3"** e-ink display (Spectra 6 color)
- A **microphone**
- An **A4 picture frame**

The e-ink panel is optional. You can also show it on a TV, an HDMI monitor, or any screen on your network, which makes it much cheaper to try.

[ADD: current prices for the parts in your country, and total build cost]

## How hard is it to build?

If you've set up a Raspberry Pi before and are comfortable following instructions in a terminal, it's a reasonable weekend project. The software runs as a Python service that talks to BirdNET-Go and manages the display.

If you've never touched a Raspberry Pi, it's a fun first project, but expect to spend time learning the basics first.

## Where does the name come from?

"Fugleramme" is Norwegian for "bird frame." The creator says it references a WWF poster by Axel Thorenfeldt.

## Licensing (read this if you want to sell one)

- **The code:** MIT license
- **The classic artwork set:** CC BY-SA 4.0
- **BirdNET detection software:** CC BY-NC-SA 4.0, which means **non-commercial**

So it's fine to build one for your home or as a gift. Building and selling them commercially would run into the non-commercial license on the detection software.

## Why people love it

Most smart-home gadgets want your attention. Fugleramme quietly tells you something true about the world just outside, in a style from 170 years ago. It's the opposite of doomscrolling.

## FAQ

**What is Fugleramme?**
An open-source Raspberry Pi project that identifies birds by sound using local AI and displays them as vintage illustrations on an e-ink frame.

**Does Fugleramme need the internet?**
No. Detection and display run locally.

**What hardware does Fugleramme need?**
The reference build uses a Raspberry Pi 5, an Inky Impression 13.3" e-ink display, a microphone and an A4 frame. The e-ink display is optional.

**Does it work outside Europe?**
BirdNET can recognize many species worldwide, but the illustration set focuses on Scandinavian, British and Central European birds.

---
*Sources: [Fugleramme on GitHub](https://github.com/arnegiacomo/fugleramme), [Hacker News discussion](https://news.ycombinator.com/item?id=49711544)*
