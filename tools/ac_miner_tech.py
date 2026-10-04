import json, subprocess, urllib.parse, concurrent.futures as cf, re, sys, time

# Tech long-tail miner. Unlike the niche miners, brand names are KEPT:
# in tech, the brand IS the query. What we filter for instead is the
# SHAPE of the query — error strings, post-update breakage, compatibility,
# "where did X go" — because those are the tech queries big publishers
# don't cover and forums do.
PRODUCTS = [
 # assistants / AI apps
 "chatgpt","claude","gemini","copilot","perplexity","notebooklm","sora","veo","grok",
 "cursor","windsurf","zed editor","ollama","lm studio","openwebui","comfyui","whisper",
 # phones / OS
 "ios 27","android 17","iphone 18","pixel 11","galaxy s26","one ui 9","watchos 27",
 "macos 27","windows 11","chromeos","ipados 27","carplay","android auto",
 # home / self-hosted
 "home assistant","proxmox","tailscale","synology","unraid","jellyfin","plex","immich",
 "frigate","pi-hole","raspberry pi 5","docker desktop","portainer","nextcloud","n8n",
 # dev / cloud
 "github actions","vercel","supabase","cloudflare tunnel","vscode","wsl","git lfs",
 "npm install","python venv","node 24","homebrew",
 # hardware / consumer
 "steam deck","quest 3","apple vision","airpods pro 3","matter smart home","thread border router",
 "starlink","wifi 7","usb4","sd express","nvme enclosure","gan charger",
 # productivity
 "obsidian","notion","excel","google sheets","outlook","teams","slack","zoom","canva","capcut",
 "davinci resolve","blender","figma","bitwarden","1password","signal app","whatsapp web",
]
STEMS = [
 "why does {n} say","{n} error","{n} not working after update","how to fix {n}",
 "{n} keeps","can you use {n} with","does {n} work with","why is {n} so slow",
 "{n} stopped working","where did {n} go","{n} missing","how to turn off {n}",
 "{n} eating battery","{n} free alternative","{n} limit","is {n} safe",
]
# Shape filter: keep queries that look like a specific problem, not a category page.
PROBLEM = re.compile(r"\b(error|fail|failed|won'?t|wont|cant|can'?t|not working|stopped|keeps|stuck|missing|gone|disappeared|greyed|grayed|disabled|crash|crashing|freez|loop|hang|slow|lag|drain|overheat|no sound|no audio|black screen|blank|invalid|denied|refused|timeout|timed out|unsupported|incompatible|corrupt|why does|why is|how to fix|after update|after updating|after upgrade|instead of)\b", re.I)

def ac(q):
    url = "https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q=" + urllib.parse.quote(q)
    for _ in range(2):
        try:
            out = subprocess.run(["curl","-s","--max-time","10",url],capture_output=True,text=True).stdout
            return json.loads(out)[1]
        except Exception:
            time.sleep(1)
    return []

seeds = [s.format(n=n) for n in PRODUCTS for s in STEMS]
res = {}
with cf.ThreadPoolExecutor(12) as ex:
    for q, sugg in zip(seeds, ex.map(ac, seeds)):
        for s in sugg:
            res[s] = q
# level 2: push the promising problem-shaped ones further
lvl2_seeds = [s for s in res if len(s.split()) >= 4 and PROBLEM.search(s)]
tails = [" after update", " on iphone", " on windows", " on mac", " fix", " 2026"]
lvl2 = [s+t for s in lvl2_seeds for t in tails]
with cf.ThreadPoolExecutor(16) as ex:
    for q, sugg in zip(lvl2, ex.map(ac, lvl2)):
        for s in sugg:
            res.setdefault(s, q)
clean = sorted({s for s in res if len(s.split()) >= 5 and PROBLEM.search(s)})
json.dump(clean, open(sys.argv[1],"w"), indent=0)
print(len(res), "total;", len(clean), "problem-shaped long-tail")
