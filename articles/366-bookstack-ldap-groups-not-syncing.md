---
title: "BookStack LDAP Login Works But Groups Don't Sync"
slug: bookstack-ldap-groups-not-syncing
meta_description: "Users authenticate and land on the default role. The $ escaping in Docker Compose, recursive groups, parentheses in group names, and the debug switches."
updated: October 2026
cluster: round 14 (tech) — BookStackApp/BookStack GitHub issues
competition: LOW
---

# BookStack LDAP Login Works But Groups Don't Sync

Authentication and authorisation are separate steps. If login succeeds, your bind, base DN and user filter are fine — the problem is in the group half. Turn on the two debug switches before anything else; they print exactly what BookStack received.

```env
APP_DEBUG=true
LDAP_DUMP_USER_DETAILS=true
```

Log in, and BookStack renders the raw LDAP user object including its group memberships. That single output answers most of these questions.

## 1. The `$` escaping problem in Docker Compose

This one bites nearly everyone who runs BookStack in Compose, and it looks like a totally different bug.

```yaml
environment:
  - LDAP_USER_FILTER=(&(sAMAccountName=${user}))
```

Compose interprets `${user}` as a **variable it should substitute**, finds it empty, and passes `(&(sAMAccountName=))` to BookStack. The filter then matches nobody, or matches everyone, depending on the directory.

Escape it by doubling the dollar sign:

```yaml
  - LDAP_USER_FILTER=(&(sAMAccountName=$${user}))
```

Or put it in an `env_file`, where no substitution happens:

```env
# .env (referenced with env_file:, not environment:)
LDAP_USER_FILTER=(&(sAMAccountName=${user}))
```

Verify what the container actually got:

```bash
docker exec bookstack sh -c 'echo "$LDAP_USER_FILTER"'
```

## 2. Group sync configuration

```env
LDAP_USER_TO_GROUPS=true
LDAP_GROUP_ATTRIBUTE=memberOf
LDAP_REMOVE_FROM_GROUPS=true
```

Then, in BookStack: **Settings → Roles → (role) → External Authentication IDs**, set the group name. Matching rules that matter:

- BookStack matches on the **CN**, not the full DN. A `memberOf` of `CN=Wiki Admins,OU=Groups,DC=example,DC=com` matches an External Auth ID of `Wiki Admins`.
- Matching is case-insensitive and whitespace-sensitive. A trailing space in the role's External Auth ID silently fails.
- Multiple names go in comma-separated.
- `LDAP_REMOVE_FROM_GROUPS=true` means BookStack *manages* role membership — users lose roles they no longer have in LDAP. Without it, roles only ever accumulate.

## 3. Parentheses and special characters in group names

A documented failure: a security group with **parentheses in its name** breaks the LDAP search filter, because parentheses are filter syntax. The error is a "bad search filter" rather than anything about groups.

LDAP special characters must be escaped as `\28` `\29` `\2a` `\5c`:

```
# group literally named "Wiki (Admins)"
Wiki \28Admins\29
```

The pragmatic answer is to rename the group in the directory. Parentheses, asterisks and backslashes in group names cause problems in more tools than BookStack.

## 4. Recursive / nested groups

`memberOf` returns **direct** memberships only. A user in "Engineering", which is a member of "Wiki Users", does not get `memberOf: Wiki Users`.

BookStack has handled recursion inconsistently across versions — reports exist of `parsed_direct_user_groups` and `parsed_recursive_user_groups` coming back identical, meaning recursion did nothing. Two reliable workarounds:

- **Flatten the groups in the directory**: add users to the wiki group directly. Unglamorous and it always works.
- **For Active Directory**, use the matching-rule-in-chain filter in your user filter to resolve nesting server-side:

```
(&(sAMAccountName=$${user})(memberOf:1.2.840.113556.1.4.1941:=CN=Wiki Users,OU=Groups,DC=example,DC=com))
```

That OID is AD-specific and only restricts *login*; it doesn't populate roles. For roles, flattening is the dependable route.

## 5. Domain restriction interacting with groups

A known interaction: with **domain restriction enabled**, AD groups are not assigned on a user's *first* login — they get the default role only, and groups apply from the second login onward. If your users report "I had no permissions until I logged out and back in", that's this.

Either disable the domain restriction, or accept that first login is default-role and document it.

## 6. The sync only happens at login

Changing a user's LDAP groups does not update BookStack until they log in again. There is no background sync. For an urgent revocation, change the role in BookStack directly as well as in LDAP.

## What not to do

- **Don't debug group sync before confirming the filter.** `LDAP_DUMP_USER_DETAILS` first, always.
- **Don't leave `APP_DEBUG=true` on.** It leaks stack traces and configuration to any visitor.
- **Don't use parentheses in group names.** Rename the group.
- **Don't set `LDAP_REMOVE_FROM_GROUPS=true` without checking your mappings.** It will strip roles from everyone on their next login.

## Prevention

| Habit | Why |
|---|---|
| `$${user}` in Compose, or an env_file | Removes the single most common cause |
| Flat wiki groups in the directory | Recursion support is the least reliable part |
| No special characters in group names | Avoids filter escaping entirely |
| Keep one local admin account | Your way back in when LDAP breaks |

## FAQ

**Can I use LDAP and local accounts together?**
Yes, but the local admin is what saves you during an LDAP outage. Keep one.

**OIDC instead?**
Often simpler for group claims, if your IdP supports it. BookStack supports both.

**Users created with the wrong email?**
`LDAP_EMAIL_ATTRIBUTE` — AD usually wants `mail`, some directories `userPrincipalName`.

**Does it support LDAPS?**
Yes; `LDAP_SERVER=ldaps://host:636`, and the CA must be trusted in the container.
