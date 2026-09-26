# Taslak Promptu

Claude / ChatGPT / Gemini'ye aşağıdaki promptu ver. Köşeli parantezleri doldur. **Notlar bölümünü boş bırakma** — yazıyı özgün yapan tek şey o.

---

```
You're helping me draft a blog post for my tech/AI blog. Write like a real person
who actually used the thing, not like a content marketer.

TOPIC: [e.g. Claude vs ChatGPT vs Gemini for writing]
TARGET READER: [e.g. someone who writes emails/reports at work and wants to pick one tool]
MAIN QUESTION THEY SEARCHED: [e.g. "which AI is best for writing"]
MY VERDICT: [e.g. Claude for long drafts, ChatGPT for quick edits, Gemini if you live in Google Docs]

MY OWN NOTES FROM TESTING (use these, don't invent other results):
- [note 1]
- [note 2]
- [note 3]

RULES:
- First sentence must be concrete: a result, a claim, or the direct answer.
- Take a clear side. Don't end with "it depends on your needs".
- Mix short and long paragraphs. Some one-line paragraphs are fine.
- Use "I" and "you". Contractions are good.
- Never use: delve, leverage, seamless, robust, game-changer, landscape, realm,
  tapestry, elevate, harness, unlock, "in today's fast-paced world",
  "it's important to note", "in conclusion", "whether you're a... or a...".
- Go easy on em-dashes and bold text. Don't make every list three items.
- Don't invent statistics, quotes or test results. If a spot needs a real example
  from me, write [ADD: what's needed] instead.
- H2 headings should be questions or plain statements a person would search.
- Length: [1200-1800] words. Include a short FAQ at the end (3-4 questions).
```

---

## Sonra ikinci tur (düzeltme promptu)

```
Now reread the draft as a skeptical editor. List every sentence that sounds
generic, AI-written, or that any other blog could have written. Rewrite only
those sentences to be more specific or cut them. Keep everything else as is.
```

Ardından `method/human-writing-guide.md` kontrol listesini **kendin** uygula. Son düzeltme her zaman insan elinden geçmeli.
