---
title: "Tandoor Recipes: Importing From a URL Fails"
slug: tandoor-recipe-import-failed
meta_description: "Import from source errors, or works for some sites and not others. The recipe-scrapers version, schema-less pages and the bookmarklet path."
updated: October 2026
cluster: round 14 (tech) — TandoorRecipes/recipes GitHub issues
competition: LOW
---

# Tandoor Recipes: Importing From a URL Fails

Tandoor imports via the **recipe-scrapers** library, which works in two modes:

- **Generic**: reads `ld+json` structured data (Schema.org `Recipe`). Works on any site that publishes it.
- **Site-specific scrapers**: hand-written parsers for sites that don't.

That split explains almost every failure: a site changed its HTML, or it never had structured data.

## 1. Check whether the page has structured data

```bash
curl -s 'https://example.com/recipe' | grep -o 'application/ld+json' | head -1
```

Better, look at what's in it:

```bash
curl -s 'https://example.com/recipe' \
  | python3 -c "
import sys,re,json
html=sys.stdin.read()
for m in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S):
    try:
        d=json.loads(m)
        print(json.dumps(d, indent=2)[:600])
    except Exception as e:
        print('unparseable:', e)
"
```

- **Valid `Recipe` JSON-LD present** → the generic scraper should work; a failure is a Tandoor/library version issue (section 2).
- **Nothing** → you need a site-specific scraper, or a different import method (section 4).

## 2. The library version

This is the main lever. Tandoor bundles a version of `recipe-scrapers`, and when a site changes its markup the fix lands upstream first. Your Docker image may be months behind.

```bash
docker exec tandoor pip show recipe-scrapers | head -3
```

The documented behaviour: **import failures from a specific site are usually fixed by a newer recipe-scrapers, which arrives with a newer Tandoor image.** So:

```bash
docker compose pull && docker compose up -d
```

If you're already current and a site still fails, the fix isn't released yet — check the recipe-scrapers repository for your site before assuming your install is broken. A site breaking on the same day for everyone is upstream, not you.

## 3. "Import from source" errors

Two distinct errors here.

**Missing URL parameter.** Reported as an issue around the `org_url` parameter: importing from a valid JSON source fails because the originating URL isn't passed through. If you're pasting raw JSON into the import dialog rather than a URL, include the source URL field — some paths require it.

**Site blocks the server.** Tandoor fetches from the **server**, not your browser. Sites behind Cloudflare, or that block datacentre IPs, return a challenge page and the scraper sees HTML with no recipe:

```bash
docker exec tandoor curl -s -o /dev/null -w '%{http_code}\n' 'https://example.com/recipe'
```

A 403 or 503 here with a 200 in your browser is the whole answer. The bookmarklet (section 4) solves it, because it reads the page your browser already has.

## 4. Use the bookmarklet or the extension

For sites with no structured data, or that block the server, Tandoor offers:

- **The bookmarklet** — drag it to your bookmarks bar from Settings; it posts the current page's content to your instance.
- **The browser extension**, which does the same more cleanly.

Known limitation: **the bookmarklet import fails on sites with no schema data**. It gets you past the fetching problem, not the parsing one. For those pages the honest answer is manual entry, or Tandoor's "import from text" which lets you paste ingredients and steps and parses them heuristically — that's the feature designed for the long tail.

## 5. Partial imports

A recipe that imports with a title and no instructions means the scraper matched the page but the field selectors have drifted — exactly what happens after a site redesign. Reported for several large recipe sites.

What to do:

- Report it upstream with the URL. These get fixed quickly and your report is the trigger.
- In the meantime, import what works and paste the instructions manually.

Don't rewrite your Tandoor config; nothing on your side causes a partial parse.

## 6. Import from another Tandoor instance

Reported as broken between Tandoor v1 and v2. If you're migrating:

- Use the **export** feature on the old instance (Settings → Export → the full recipe archive) and **import** on the new one, rather than the URL-based "import from Tandoor" path.
- A database-level migration is the other option, and it keeps everything including meal plans and shopping lists — but requires matching schema versions, so upgrade in place before moving hosts.

## What not to do

- **Don't retry a failing URL repeatedly.** The result is deterministic; the page either parses or it doesn't.
- **Don't blame your install for a site-wide failure.** Check recipe-scrapers' issues first.
- **Don't paste a URL that needs a login.** The server has no session.
- **Don't skip the export before migrating.** The "import from Tandoor" path has been unreliable across majors.

## Prevention

| Habit | Why |
|---|---|
| Keep the image current | Scraper fixes ship with it |
| Install the bookmarklet/extension on day one | Covers blocked-server and session-required pages |
| Export your recipes on a schedule | Independent of any migration path working |
| Note which sites work for you | Saves retrying the same dead ends |

## FAQ

**Which sites import reliably?**
Anything publishing Schema.org `Recipe` — most major recipe sites and food blogs on WordPress with a recipe plugin.

**Can I import from a PDF or a photo?**
Not directly. "Import from text" plus OCR elsewhere is the practical route.

**Does importing copy the image?**
Yes, where the structured data includes one and the server can fetch it.

**Ingredients parse into the wrong fields.**
Tandoor's ingredient parser is heuristic and locale-sensitive. Check Settings → Ingredient parsing, and fix units in the food/unit management screens so future imports map correctly.
