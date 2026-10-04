---
title: "Mealie Can't Import a Recipe URL? The Structured Data Problem"
slug: mealie-recipe-import-failing
meta_description: "Mealie imports need ld+json or microdata on the page. Why some sites import blank, what the OpenAI fallback does, and how to handle paywalls and blocked requests."
updated: October 2026
cluster: round 12 (tech) — Mealie GitHub issues only
competition: LOW
---

# Mealie Can't Import a Recipe URL? The Structured Data Problem

Two different failures get described as "import not working":

- **An error** ("there was an error parsing the URL")
- **A blank import** — the recipe appears with a title and image but **no ingredients or instructions**

They have the same root cause.

## How Mealie actually imports

Mealie doesn't read the page like a human. It looks for **structured recipe data** — `ld+json` or microdata embedded in the HTML by the site. Most large recipe sites include it, which is why imports usually feel magic.

When a site removes, breaks or changes that markup, Mealie gets nothing useful and you get a blank recipe. A site that imported perfectly last year and imports empty today has usually changed its markup — this is the single most common cause, and it's reported for big names.

## Diagnose it in thirty seconds

View the page source and search for `application/ld+json` and `Recipe`:

```bash
curl -sL "https://example.com/recipe" | grep -o 'application/ld+json' | head
curl -sL "https://example.com/recipe" | python3 -c "import sys,re,json;
h=sys.stdin.read()
m=re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', h, re.S)
print(len(m), 'blocks'); print(m[0][:400] if m else 'none')"
```

- **No ld+json** → Mealie can't scrape it. Use the fallback or paste it manually
- **ld+json present but the curl output is a cookie wall / Cloudflare page** → your server is being blocked, not the parser

## When the server is being blocked

If the browser shows the recipe and Mealie can't fetch it:

- The site blocks **datacentre IPs** or non-browser user agents
- **Cloudflare** challenge pages return HTML with no recipe in it
- **Paywall or consent wall** served to anything without cookies
- Mealie running behind a **VPN/proxy** whose exit is blocked

Workarounds: use the **browser extension / bookmarklet** so the fetch comes from your browser, or copy the page text and use **Create → from text** with the AI parser.

## The AI fallback

Mealie can send page content to an **OpenAI-compatible model** to parse recipes that have no structured data. Points worth knowing:

- You configure your own key and base URL; it isn't on by default
- It's used when scraping fails, so it's the answer for blog-style recipes
- A reported bug sent HTML to the model **even when the HTTP request failed** — so check Mealie's log before blaming the model for nonsense output
- It costs tokens per import, and it is slower

## Other reported failure modes

- **Image not stored correctly** on URL import — a version-specific bug; check the issue tracker and the recipe's own image field
- **Wrong API endpoint** when importing from an integration (Home Assistant's Mealie integration has hit `/api/recipes/create-url` vs `/api/recipes/create/url`, giving a 405). Update the integration rather than Mealie
- Bulk URL import failing on one bad URL and stopping — import in smaller batches
- A recipe that imports but with **ingredients as one blob** — that's the parser doing its best with weak markup; use the ingredient parser tool afterwards

## What to do, practically

1. **Check the log**: `docker compose logs -f mealie` while you import. The real error is there
2. **Test with a known-good site** to prove Mealie works at all
3. For a site with no markup: **AI parser**, or copy-paste and use the ingredient parser
4. For a blocked fetch: **browser extension**
5. For a version regression: check GitHub issues, pin the previous tag

## Prevention

- **Pin the image tag**; Mealie moves quickly
- **Back up** the data volume (recipes, images, database)
- Don't rely on an import you never checked — verify the ingredients saved correctly before you delete the source

## FAQ

**Why do some sites import perfectly and others not at all?**
Only sites publishing `ld+json`/microdata recipe data can be scraped. The rest need the AI parser or manual entry.

**Is the AI parser required?**
No, it's optional and you supply the key. Without it, unstructured sites can't be imported automatically.

**The browser shows the recipe but Mealie gets nothing.**
Your server is being blocked or served a consent/Cloudflare page. Use the browser extension.

**Can I fix an already-blank import?**
Yes — edit the recipe and paste the ingredients, then run the ingredient parser.
