import json, subprocess, urllib.parse, concurrent.futures as cf, re, sys, time

# Round 10: lean hard into the seam round 9 proved most productive —
# self-hosted / homelab / dev tooling, where the only existing answer is a
# GitHub issue or a project forum. Plus current-version consumer symptoms.
PRODUCTS = [
 # self-hosted media & photos
 "jellyfin","plex","emby","navidrome","audiobookshelf","immich","photoprism","paperless-ngx",
 "sonarr","radarr","prowlarr","bazarr","qbittorrent","gluetun","jellyseerr",
 # home automation
 "home assistant","esphome","zigbee2mqtt","zwave-js-ui","mosquitto","node-red","scrypted",
 "frigate","tasmota","shelly","matter bridge","thread border router","homebridge",
 # infra & networking
 "proxmox","truenas","unraid","docker compose","portainer","watchtower","k3s","caddy",
 "traefik","nginx proxy manager","authentik","cloudflared","wireguard","tailscale",
 "adguard home","pi-hole","opnsense","pfsense","unifi controller","omada controller",
 "vaultwarden","nextcloud","syncthing","restic","borgbackup","duplicati","grafana","influxdb",
 # dev tooling
 "vscode","cursor","windsurf","zed","git","github actions","npm","pnpm","docker build",
 "python venv","uv pip","node 24","bun","wsl2","homebrew","ollama","lm studio","open webui",
 # consumer, current versions
 "ios 27.1","ipados 27","macos 27","watchos 27","android 17","one ui 9","windows 11 25h2",
 "pixel 11","galaxy s26","quest 3","steam deck","switch 2","sonos app","airpods pro 3",
]
STEMS = [
 "{n} not working after update","{n} error after upgrade","why does {n} say","{n} keeps restarting",
 "{n} stopped working","how to fix {n}","{n} missing after update","{n} broken after update",
 "{n} not detected","{n} permission denied","{n} stuck on","{n} fails to start",
 "where did {n}","{n} suddenly slow","{n} high cpu","{n} out of memory","{n} not syncing",
]
PROBLEM = re.compile(r"\b(error|fail|failed|won'?t|wont|cant|can'?t|not working|not detected|not syncing|stopped|keeps|stuck|missing|gone|disappeared|greyed|grayed|disabled|crash|crashing|freez|loop|hang|slow|lag|drain|overheat|no sound|no audio|black screen|blank|invalid|denied|refused|timeout|timed out|unsupported|incompatible|corrupt|permission|high cpu|out of memory|oom|why does|why is|how to fix|after update|after updating|after upgrade|after reboot|instead of)\b", re.I)

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
lvl2_seeds = [s for s in res if len(s.split()) >= 4 and PROBLEM.search(s)]
tails = [" after update", " docker", " fix", " 2026", " reddit"]
lvl2 = [s+t for s in lvl2_seeds for t in tails]
with cf.ThreadPoolExecutor(16) as ex:
    for q, sugg in zip(lvl2, ex.map(ac, lvl2)):
        for s in sugg:
            res.setdefault(s, q)
clean = sorted({s for s in res if len(s.split()) >= 5 and PROBLEM.search(s)})
json.dump(clean, open(sys.argv[1],"w"), indent=0)
print(len(res), "total;", len(clean), "problem-shaped long-tail")
