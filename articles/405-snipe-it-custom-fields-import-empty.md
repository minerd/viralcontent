---
title: "Snipe-IT: CSV Import Leaves Custom Fields Empty"
slug: snipe-it-custom-fields-import-empty
meta_description: "Assets import fine and the custom fields are blank. The fieldset must be associated with the model — plus the list-type and blank-value traps."
updated: October 2026
cluster: round 14 (tech) — grokability/snipe-it GitHub issues
competition: LOW
---

# Snipe-IT: CSV Import Leaves Custom Fields Empty

One cause dominates, and it is not in the CSV:

> **The custom fieldset must be associated with the asset model you are importing into.**

Snipe-IT stores custom field values against the asset, but only accepts them for fields that belong to a fieldset attached to that asset's **model**. Import an asset whose model has no fieldset, and the values are discarded silently — the asset is created, the preview looked right, and the fields are empty.

## 1. Attach the fieldset to every model you import

```
Settings → Custom Fields → Fieldsets → (your fieldset)
Assets → Models → (each model) → Edit → Fieldset
```

If you're importing hundreds of assets across twenty models, **all twenty models need the fieldset**. This is the fix in the overwhelming majority of reports: people assign the fieldset to a few models, import, see blanks, and look at the CSV.

Do it before importing. Assigning the fieldset afterwards makes the fields *visible* on the asset but does not retroactively populate them — you have to re-import.

## 2. Header names must match the field names exactly

```csv
Asset Tag,Model Name,Category,Manufacturer,Serial,Warranty Expiry,MAC Address
A0001,Latitude 5440,Laptop,Dell,ABC123,2027-06-01,00:11:22:33:44:55
```

- The custom field's **name** as shown in Settings → Custom Fields is what the importer matches against, not the database column (`_snipeit_mac_address_1`).
- Case and spacing matter. `MAC address` and `MAC Address` are different headers as far as matching goes in some versions.
- The importer's **column mapping screen** is where you confirm this — it shows your CSV headers alongside Snipe-IT's fields. If a custom field isn't offered in that dropdown, the fieldset isn't attached to the model (section 1).

## 3. List-type fields

A documented limitation: custom fields with the **"List" / dropdown** type often don't populate on import, even when the fieldset is attached and the exact list item exists. Manual edits work; the import doesn't.

Workarounds:

- Import those values into a **text** custom field and convert later
- Set the list values by hand after import, or via the API:

```bash
curl -s -X PATCH 'https://snipe.example.com/api/v1/hardware/42' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"_snipeit_department_7":"Finance"}'
```

The API accepts the database column name (`_snipeit_<slug>_<id>`), which you can find in Settings → Custom Fields by inspecting the field, or from a single asset's API response.

## 4. Blank values filled with the previous row's data

A real and nasty one: **blank custom field cells get populated with seemingly random values from other rows.** The documented nuance is that a cell left blank in a column that has values elsewhere can inherit; an **entirely blank column** is correctly treated as blank.

Consequences for how you prepare the file:

- **Never leave a custom-field cell empty** if other rows in that column have values. Put an explicit empty marker your process understands, or split the import into files where each file's columns are uniformly populated.
- **Verify a sample after import.** Pick ten assets across different rows and compare against the CSV. This is the only way to catch inherited values, because nothing errors.

## 5. Import via CLI doesn't update custom fields

Another reported gap: the **CLI importer** doesn't update custom fields on existing assets, while the web importer does. If you're scripting updates, use the API rather than `snipe-it:import`.

```bash
# web importer: Settings → Import, with "Update existing values" checked
```

## 6. Check what actually landed

```bash
curl -s "https://snipe.example.com/api/v1/hardware/42" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | grep -A3 custom_fields
```

The API response is the truth; the UI can show a field as present-but-empty for several different underlying reasons.

## What not to do

- **Don't import before attaching fieldsets to models.** It's the cause, and re-importing is the only cure.
- **Don't leave blank cells in partially-populated custom columns.** You'll get inherited values you never notice.
- **Don't trust the import preview.** It shows parsing, not the fieldset association.
- **Don't import 5,000 rows on the first attempt.** Ten rows, verify via the API, then the rest.

## Prevention

| Habit | Why |
|---|---|
| Fieldset attached to every model, checked before import | The dominant cause |
| Ten-row test import, verified through the API | Catches both blank fields and inherited values |
| Text fields instead of lists for imported data | Lists are the unreliable type |
| A database backup before every bulk import | Undoing a bad import otherwise means deleting assets by hand |

## FAQ

**Can I undo an import?**
Not as a unit. Filter by created date and delete, or restore the database backup.

**Does it match existing assets by asset tag?**
Yes, with "update existing values" enabled. Without it, duplicates.

**Users and licences import the same way?**
Same importer, same fieldset logic for their custom fields.

**Encrypted custom fields?**
They import, but only users with the decrypt permission can read them — and they don't appear in plain API responses.
