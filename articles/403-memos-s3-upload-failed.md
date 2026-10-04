---
title: "Memos: Attachment Upload to S3 Failing"
slug: memos-s3-upload-failed
meta_description: "SignatureDoesNotMatch, unsupported protocol scheme, or 401 on the attachments API. Endpoint format, path style and the S3-compatible gotchas."
updated: October 2026
cluster: round 14 (tech) — usememos/memos GitHub issues
competition: LOW
---

# Memos: Attachment Upload to S3 Failing

Three distinct errors, each with a specific cause.

| Error | Cause |
|---|---|
| `unsupported protocol scheme ""` | Endpoint missing its scheme — section 1 |
| `SignatureDoesNotMatch` | Region, path style, or a non-AWS provider — section 2 |
| `POST /api/v1/attachments 401` | API token scope — section 4 |

## 1. "unsupported protocol scheme"

The endpoint field needs a **full URL including `https://`**. A bare hostname produces exactly this, and it's the most common mistake with Backblaze, Wasabi, MinIO and the rest.

```
Endpoint:   https://s3.us-west-004.backblazeb2.com
Region:     us-west-004
Bucket:     my-memos
Access key: 004...
Secret key: K004...
URL prefix: https://f004.backblazeb2.com/file/my-memos
```

Points that matter:

- **Scheme required**, no trailing slash.
- **Region must match the endpoint.** Backblaze and Wasabi encode the region in the hostname; a mismatch between the two is the usual cause of signature failures (section 2).
- **URL prefix** is what gets written into your memos as the public link. It is often a *different* host from the API endpoint — Backblaze's `f004.` friendly URL versus the `s3.` API host, for example. Getting this wrong gives successful uploads and broken images.

## 2. SignatureDoesNotMatch

Signature failures with correct keys come down to how the request was formed.

**Path style vs. virtual-hosted style.** AWS defaults to `bucket.s3.region.amazonaws.com`; MinIO and many self-hosted gateways need `endpoint/bucket`. If your provider requires path style and Memos uses virtual-hosted (or the reverse), every request fails the signature check. Check whether your Memos version exposes a path-style toggle; for MinIO, using the endpoint exactly as MinIO documents it is the deciding factor.

**Google Cloud Storage via the S3/XML API.** A documented case: `PutObject` fails with `SignatureDoesNotMatch`, and separately the **presigned URLs** Memos generates for the browser also fail. GCS's S3 interoperability layer is strict about which headers are signed. If you need GCS, consider using it through a gateway that presents a standard S3 surface, or use local storage and back the volume up to GCS out of band.

**Clock skew.** S3 signatures include a timestamp with a 15-minute window:

```bash
docker exec memos date; date
```

A container hours out of sync fails every request. Fix the host's NTP.

**Cross-bucket copy.** A reported failure: `copyObject` against certain S3-compatible providers fails whenever source and destination buckets differ, with no fallback to download-then-upload. If your workflow involves moving objects between buckets, test it explicitly.

## 3. Verify outside Memos

This removes all ambiguity:

```bash
docker run --rm -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... \
  amazon/aws-cli s3 ls s3://my-memos \
  --endpoint-url https://s3.us-west-004.backblazeb2.com
```

If the CLI can list and put objects with the same credentials and endpoint, the credentials and bucket policy are fine and the problem is in how Memos forms its requests — which points at path style or region.

```bash
docker run --rm -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... \
  amazon/aws-cli s3 cp /etc/hostname s3://my-memos/test.txt \
  --endpoint-url https://s3.us-west-004.backblazeb2.com
```

## 4. 401 on the attachments API

A separate, reported problem: `POST /api/v1/attachments` returning **401 despite a valid bearer token**, making programmatic uploads (scripts, MCP integrations, mobile clients using the API) impossible while the web UI works.

Things to check:

- The token is an **access token** created in Memos → Settings → Access Tokens, used as `Authorization: Bearer <token>`.
- Memos' API versions coexist (`/api/v1`, and newer paths). A token or an endpoint from a different major can 401. Match the API path to your server version.
- Behind a reverse proxy, confirm the `Authorization` header is forwarded:

```nginx
proxy_set_header Authorization $http_authorization;
proxy_pass_header Authorization;
```

Many proxy configurations strip it, and the symptom is exactly a 401 with a token that works locally.

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $TOKEN" \
  https://memos.example.com/api/v1/memos
```

If that returns 200 and the attachments POST returns 401, it's version/path. If both 401, it's the token or the proxy.

## 5. Uploads succeed, images don't display

That's the **URL prefix** (section 1) or the bucket's access policy. Memos stores a link; the browser fetches it directly.

- For a public bucket, the prefix must be the public base URL.
- For a private bucket, Memos must generate presigned URLs — supported, and the presigning is where the GCS problem in section 2 shows up.

```bash
curl -sI 'https://f004.backblazeb2.com/file/my-memos/2026/03/file.png'
```

A 403 here with a successful upload means the bucket is private and you're serving public links.

## What not to do

- **Don't put the bucket name in the endpoint.** Endpoint and bucket are separate fields.
- **Don't leave local storage files behind when switching to S3.** Memos doesn't migrate existing attachments; old memos keep local links that break if you remove the volume.
- **Don't use a root/admin S3 key.** Create one scoped to the bucket with put/get/delete.
- **Don't debug inside Memos first.** The AWS CLI test is definitive and takes a minute.

## Prevention

| Habit | Why |
|---|---|
| Verify credentials with the AWS CLI before configuring Memos | Separates provider problems from app problems |
| Endpoint with scheme, region matching it, prefix tested | The three fields that cause everything |
| NTP on the host | Signature windows are 15 minutes |
| Keep the local volume after migrating | Old attachments still reference it |

## FAQ

**Can I migrate existing attachments to S3?**
Not from the UI. Copy the files to the bucket preserving paths and rewrite the links in the database — back up first.

**Does Memos need S3 at all?**
No; local storage is the default and fine for a single user. S3 matters for multi-host or large libraries.

**Which providers work best?**
Anything with a standard S3 surface: MinIO, Backblaze B2 (S3 API), Wasabi, Cloudflare R2, AWS. GCS's interop layer is the awkward one.

**Attachments deleted from Memos remain in the bucket.**
Check your version's delete behaviour and set a lifecycle rule on the bucket if you want cleanup.
