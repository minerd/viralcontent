---
title: "Ghostfolio: CSV Import of Activities Failing"
slug: ghostfolio-csv-import-failed
meta_description: "Imports reject valid rows, re-imports fail, or symbols with hyphens aren't accepted. The column names, the data source rules and the file-extension bug."
updated: October 2026
cluster: round 14 (tech) — ghostfolio/ghostfolio GitHub issues
competition: LOW
---

# Ghostfolio: CSV Import of Activities Failing

Ghostfolio validates every row before importing any of them, so one bad cell rejects the whole file. The error names the field — read it literally.

## 1. The exact column set

```csv
Date,Code,DataSource,Currency,Price,Quantity,Fee,Type,AccountId
2026-01-15,AAPL,YAHOO,USD,185.50,10,1.00,BUY,
2026-02-01,VWCE.DE,YAHOO,EUR,118.20,5,0.00,BUY,
```

Rules that cause most rejections:

- **`Date`** must be `YYYY-MM-DD`. A locale format (`15/01/2026`) gives `date is not valid`.
- **`Quantity` and `Price` must be positive numbers.** A comma decimal separator (`185,50`) is read as text. Convert to dots.
- **`Type`** is one of `BUY`, `SELL`, `DIVIDEND`, `FEE`, `INTEREST`, `ITEM`, `LIABILITY`. Case matters in some versions.
- **`Currency`** must be a valid ISO code, and must match what the data source reports for that symbol — a EUR-listed ETF imported as USD produces nonsense valuations rather than an error.
- **`DataSource`** must be a source Ghostfolio knows: `YAHOO`, `COINGECKO`, `MANUAL`.

```
activities.0.currency is not valid
quantity must be a positive number
```

Those messages name the **row index** (zero-based) — `activities.0` is the first data row.

## 2. Symbols with special characters

A documented bug: **symbols containing a hyphen** fail with "is not valid for the specified data source", even though the symbol is correct and resolvable. `BRK-B`, `RDS-A` and similar are affected.

Workarounds:

- Use the alternative ticker form the data source accepts (`BRK-B` vs `BRK.B` — try both).
- Create the asset profile manually in Ghostfolio first (Admin → Market data → add profile), then import with `DataSource=MANUAL` and that symbol.
- Add those few positions through the UI rather than the CSV.

## 3. Re-importing a file that previously worked

Another real one: adding new rows to a CSV and re-importing **fails**, even though the existing rows imported fine before. Duplicate detection rejects them, but not always cleanly — and in some conditions duplicates aren't detected at all and you get doubled positions.

The reliable approach: **import only new rows.** Keep your full history in a master file and export just the delta for each import. Tedious, deterministic, and it avoids both failure directions.

If you've already doubled positions, filter activities by date in the UI and delete the duplicates; there's no bulk de-duplicate.

## 4. The file extension bug

Files ending in **`.CSV`** (capital letters) have raised an error on import where `.csv` works. If your bank or broker exports in capitals, rename:

```bash
mv Transactions.CSV transactions.csv
```

Trivial, and it has cost people an hour.

## 5. Custom asset profiles (MANUAL)

Importing an activity with `DataSource=MANUAL` requires the asset profile to exist already — and a reported bug has it create a **new** profile instead of using yours, so the mapping isn't applied.

The order that works:

1. **Admin → Market data → Add asset profile**, with `MANUAL` as the source and your chosen symbol
2. Add a price manually, or set up the profile's scraper configuration
3. *Then* import activities referencing that exact symbol

Importing first and creating the profile after leaves you with two profiles and split history.

## 6. Preview looks right, import fails

The preview parses; the import validates against data sources and the database. So a row can preview correctly and then fail because:

- The symbol doesn't resolve at the named data source
- The currency doesn't match the resolved profile
- An account ID references an account that doesn't exist (leave `AccountId` empty to use the default)

Import in small batches while you're finding the problem — a 10-row file tells you which construct is wrong far faster than a 500-row one.

## What not to do

- **Don't import your whole history on the first attempt.** Ten rows, confirm, then the rest.
- **Don't re-import a growing master file.** Import deltas.
- **Don't fix a rejected row by removing the column.** Missing required fields fail differently and more confusingly.
- **Don't trust the preview as validation.** It parses; it doesn't verify symbols.

## Prevention

| Habit | Why |
|---|---|
| ISO dates and dot decimals in your master file | Removes the two commonest rejections |
| Asset profiles created before importing MANUAL activities | Prevents split history |
| Delta files per import, dated | Makes re-imports safe |
| Export a backup from Ghostfolio before each import | The only clean undo |

## FAQ

**Can I export and re-import to move instances?**
Yes — Ghostfolio's own export format round-trips better than a hand-built CSV.

**Dividends need a quantity?**
Set quantity to the shares held and price to the per-share dividend, or quantity 1 and price to the total — be consistent, because performance figures depend on it.

**Crypto imports?**
`DataSource=COINGECKO` with the CoinGecko id (`bitcoin`), not the ticker.

**Fees as separate rows or on the trade?**
Either works. On the trade keeps the cost basis tidier.
