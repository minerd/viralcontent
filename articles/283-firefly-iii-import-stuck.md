---
title: "Firefly III Import Stuck or Failing? Split the File and Read the Log"
slug: firefly-iii-import-stuck
meta_description: "Data Importer runs forever, errors on transfers, or stops with invalid data. The nginx PUT problem, import tags, BIC validation and batching strategy."
updated: October 2026
cluster: round 12 (tech) — Firefly III GitHub issues and docs
competition: LOW
---

# Firefly III Import Stuck or Failing? Split the File and Read the Log

The Data Importer is a separate service from Firefly III, which means there are **two logs** and the useful one is usually the Firefly III log, not the importer's.

```bash
docker compose logs -f app          # firefly iii
docker compose logs -f importer     # data importer
```

## 1. The reverse proxy that blocks PUT

A documented cause of imports failing in a confusing way: **the nginx configuration didn't allow the PUT request type**, so the importer's calls were rejected.

If your Firefly III sits behind a proxy with method restrictions, or a WAF, check that **GET, POST, PUT and DELETE** all pass:

```nginx
# don't do this
if ($request_method !~ ^(GET|POST)$) { return 405; }
```

A 405 or a silently dropped request produces "could not store transaction" with no further explanation.

## 2. Batch small, then scale up

The documentation's own advice, and it's the fastest way to find a bad row: **split the file into batches of about five transactions** while you're tuning the import configuration. Once a small batch imports cleanly, run the rest.

This matters because the importer stops being informative when 2,000 rows fail for 15 different reasons.

## 3. Invalid data isn't skipped

Firefly III validates, and **invalid BICs are not skipped** — they fail the import. Either remove them from the file or fix them at source (and tell your bank, which is the documentation's own suggestion).

Other validation stoppers:
- `transactions.0.foreign_amount` errors → a foreign-currency column mapped wrong, or a currency that doesn't exist in your Firefly III
- Amount parsing: decimal comma vs point, thousands separators, currency symbols in the field
- Dates in a format the configuration doesn't declare
- Empty required fields (description, amount, date)

## 4. Transfers between two asset accounts

Reported repeatedly: imports fail on **transfers** between two asset accounts, and on **inverted** transactions where there's no account name and the account number doesn't exist yet.

Practical approach:
- Make sure **both accounts exist** in Firefly III before importing transfers
- Map the opposing-account column explicitly, don't rely on auto-creation
- Import **transfers separately** from regular transactions if your bank export mixes them badly

## 5. Slow, not stuck

A reported pattern is an importer that's **extremely slow** rather than hung. Tail the **Firefly III** log during the import — you'll see each transaction being stored, which tells you the rate.

Then:
- Each transaction is an API call; a few thousand rows legitimately takes a long time
- Check **PHP/queue workers** and the database's disk speed
- Disable the **import tag** if it's slowing the final linking step (there's a documented case of the tag-linking phase being the problem)
- Raise proxy and PHP **timeouts** so a long import isn't cut off at 60 seconds

## 6. 504 Gateway Timeout

Standard for long imports behind a proxy:

```nginx
proxy_read_timeout 600s;
proxy_send_timeout 600s;
fastcgi_read_timeout 600s;
```
plus PHP's `max_execution_time`. The documentation lists this among the common import issues.

## 7. GoCardless / Nordigen / SimpleFIN connections

Bank-connection imports have their own failures: expired authorisations, country-specific quirks, accounts that return no transactions. Re-authorise the connection before debugging mappings, and check whether the bank is returning data at all.

## Prevention

1. Keep the **import configuration JSON** for each bank — it's reusable and saves re-mapping every month
2. **Batch** the first run of any new format
3. Allow all **HTTP methods** through your proxy; raise timeouts
4. Create accounts **before** importing transfers
5. Back up the **database** before a large import — an undo is a restore

## FAQ

**Why does the importer say "could not store transaction"?**
Firefly III rejected it. Its log has the validation error; the importer only reports the failure.

**Should I import thousands of rows at once?**
Get the mapping right with five, then do the rest.

**Why are transfers so troublesome?**
They need both sides to resolve to existing accounts. Create them first.

**Import is slow but moving.**
That's normal for large files. Raise timeouts rather than killing it.
