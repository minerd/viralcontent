---
title: "paperless-ai Not Tagging Documents (Ollama Returning Nothing)"
slug: paperless-ai-not-tagging
meta_description: "The dashboard says idle, scans find zero documents, or Ollama returns no tags. Structured output support, the scan pipeline and the API token scope."
updated: October 2026
cluster: round 14 (tech) — paperless-ai GitHub issues
competition: LOW
---

# paperless-ai Not Tagging Documents (Ollama Returning Nothing)

Three separate failures present as "it isn't tagging". The log line tells you which:

```bash
docker logs paperless-ai --tail 100
```

| Log | Problem |
|---|---|
| `No tags or correspondent found in response from Ollama` | The model isn't returning valid JSON — section 2 |
| Scan finds 0 documents while RAG indexing works | The scan pipeline's filter — section 3 |
| 401 / 403 from paperless | API token — section 1 |

## 1. The paperless-ngx connection

```yaml
environment:
  PAPERLESS_API_URL: http://paperless-ngx:8000/api
  PAPERLESS_API_TOKEN: your-token
```

Points that matter:

- The URL ends in **`/api`**. Omitting it gives HTML back and a parse error that reads like a model problem.
- `localhost` means the paperless-ai container. Use the service name or LAN IP.
- The token comes from paperless-ngx → user → *Auth Token*, and the user needs permission to **change** documents, not just view them. A read-only token lets scanning work and tag writes fail silently.

Test it directly:

```bash
docker exec paperless-ai \
  curl -s -H "Authorization: Token YOUR_TOKEN" \
  http://paperless-ngx:8000/api/documents/?page_size=1 | head -c 300
```

## 2. Ollama returning no tags

This is the most common cause and it is not a prompt problem. paperless-ai asks for **structured output** — a JSON schema the model must conform to, enforced by constrained decoding. **Not every model supports it.**

```yaml
environment:
  AI_PROVIDER: ollama
  OLLAMA_API_URL: http://ollama:11434
  OLLAMA_MODEL: llama3.1:8b
```

What to check:

- **Use a model known to handle JSON schema output.** The 8B-class instruct models from the current generations do; older and heavily quantised small models frequently emit prose with the JSON embedded, which fails to parse.
- **Check the model is pulled with that exact tag:**

```bash
docker exec ollama ollama list
```

A missing tag returns a 404 that surfaces as an empty response.

- **Context length.** A long multi-page document plus the schema exceeds a small context window, the model truncates, and the JSON is invalid. Raise it or restrict the prompt to the first N characters:

```yaml
  OLLAMA_NUM_CTX: 8192
```

- **Verify manually.** This is the decisive test:

```bash
curl -s http://192.168.1.10:11434/api/chat -d '{
  "model": "llama3.1:8b",
  "messages": [{"role":"user","content":"Invoice from Acme, 2026-03-01, 240 EUR"}],
  "format": {"type":"object","properties":{"tags":{"type":"array","items":{"type":"string"}}},"required":["tags"]},
  "stream": false
}' | head -c 400
```

If that returns valid JSON, Ollama is fine and the problem is in paperless-ai's configuration. If it returns prose, the model is the problem — switch models.

If local inference keeps failing, switching `AI_PROVIDER` to an API-based model confirms whether the pipeline itself works, which is a useful bisect even if you don't intend to keep it.

## 3. Scan finds zero documents

The scan looks for documents matching its filter. The usual reasons it finds nothing while the RAG index has content:

- **The "only process documents without tags" setting** is on, and everything already has a tag (paperless-ngx's own matching rules may have tagged them).
- **A tag filter** restricts the scan to documents carrying a specific tag you haven't applied.
- **The processed marker.** paperless-ai records what it has handled; documents already seen are skipped. Use the manual re-process action on one document to test.

Start with a single document: open it in paperless-ai and trigger analysis manually. That bypasses the scan filter entirely and isolates sections 1–2 from section 3.

## What not to do

- **Don't rewrite the prompt first.** If the model can't do constrained JSON, no prompt fixes it.
- **Don't point `OLLAMA_API_URL` at `localhost`.** Service name or LAN IP.
- **Don't let it write to your whole archive untested.** Restrict to a tag, verify the tags it assigns on 10 documents, then widen.
- **Don't run a 70B model on a CPU-only host** and conclude the integration is broken. It will time out.

## Prevention

| Habit | Why |
|---|---|
| Confirm the model handles JSON schema before anything else | The dominant cause |
| Dedicated paperless user with write permission | Makes the audit trail clear and revocable |
| Test on a tag-restricted subset first | Mis-tagging a thousand documents is tedious to undo |
| Keep `OLLAMA_NUM_CTX` generous | Long documents are where parsing fails |

## FAQ

**Does it change my documents?**
Yes — it writes tags, correspondents and titles back into paperless-ngx. Back up the paperless database before a bulk run.

**Can I use it alongside paperless-ngx's own matching rules?**
Yes, but they will fight over tags. Pick one owner per tag.

**RAG chat works, tagging doesn't.**
That's exactly the section 3 pattern: different code path, different filter.

**How do I undo a bad run?**
Paperless-ngx has bulk edit; filter by the tag paperless-ai added and remove it. Easier if you had it add a marker tag to everything it touched.
