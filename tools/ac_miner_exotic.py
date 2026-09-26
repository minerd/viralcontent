import json, subprocess, urllib.parse, concurrent.futures as cf, re, sys, time

NICHES = [
 "ball python","corn snake","hognose snake","crested gecko","gargoyle gecko","blue tongue skink","uromastyx","box turtle","red eared slider","tree frog","pacman frog","dart frog","tarantula","jumping spider","isopod colony","millipede","praying mantis",
 "pet rat","pet mice","degu","dwarf hamster","parrotlet","lovebird","conure","canary","zebra finch","pet pigeon","dove","ducklings","geese","silkie chicken","bantam",
 "tepache","jun kombucha","koji","shio koji","amazake","fermented honey garlic","lacto fermented pickles","fermented salsa","fermented carrots","beet kvass","fire cider","switchel","yogurt maker","homemade yogurt","sourdough pancakes","kefir cheese","labneh","ghee","tallow","lard",
]
STEMS = ["why is my {n}","why does my {n}","can you {n}","is it normal for {n}","how to fix {n}","what to do with {n}","{n} turning","{n} smells like"]
BRANDS = re.compile(r"\b(amazon|walmart|target|costco|apple|iphone|ipad|samsung|google|pixel|android|chatgpt|openai|gemini|meta|facebook|instagram|tiktok|youtube|netflix|spotify|microsoft|windows|xbox|playstation|nintendo|tesla|ikea|starbucks|nespresso|keurig|ninja|instant pot|instapot|lodge|le creuset|kitchenaid|cuisinart|dyson|roomba|nike|adidas|hoka|brooks|asics|merrell|rei|home depot|lowes|miracle gro|scotts|purina|chewy|petco|petsmart|blue buffalo|hills|royal canin|fiskars|pampered chef|hamilton beach|breville|bodum|chemex|hario|aeropress|v60|traeger|weber|oklahoma joe|pit boss|cricut|singer|lion brand|red heart|yankee|bath and body|mason|ball)\b", re.I)

def ac(q):
    url = "https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q=" + urllib.parse.quote(q)
    for _ in range(2):
        try:
            out = subprocess.run(["curl","-s","--max-time","10",url],capture_output=True,text=True).stdout
            return json.loads(out)[1]
        except Exception:
            time.sleep(1)
    return []

seeds = [s.format(n=n) for n in NICHES for s in STEMS]
res = {}
with cf.ThreadPoolExecutor(12) as ex:
    for q, sugg in zip(seeds, ex.map(ac, seeds)):
        for s in sugg:
            res[s] = q
# second level: expand promising 1st-level suggestions with " a".." z"? keep light: append common tails
lvl2_seeds = [s for s in res if len(s.split()) >= 5 and not BRANDS.search(s)]
tails = [" after", " in winter", " in fall", " overnight", " suddenly"]
lvl2 = [s+t for s in lvl2_seeds for t in tails]
with cf.ThreadPoolExecutor(16) as ex:
    for q, sugg in zip(lvl2, ex.map(ac, lvl2)):
        for s in sugg:
            res.setdefault(s, q)
clean = sorted({s for s in res if not BRANDS.search(s) and len(s.split()) >= 6})
json.dump(clean, open(sys.argv[1],"w"), indent=0)
print(len(res), "total;", len(clean), "long-tail non-brand")
