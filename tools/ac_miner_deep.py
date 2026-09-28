import json, subprocess, urllib.parse, concurrent.futures as cf, re, sys, time

NICHES = [
 "axolotl","springtails","bioactive terrarium","dubia roaches","superworms","hornworms","feeder crickets","mealworm farm","kingsnake","rosy boa","sulcata tortoise","russian tortoise","fat tail gecko","veiled chameleon","green anole","tegu","tiger salamander","fire belly toad","whites tree frog","newt",
 "quaker parrot","african grey","cockatoo","ringneck parrot","button quail","guinea fowl","peacock","turkey poults","mini pig","alpaca","pygmy goat","rabbit litter",
 "homemade mozzarella","homemade ricotta","churning butter","cultured butter","clabbered milk","creme fraiche","homemade buttermilk","skyr","homemade vinegar","garum","ginger beer plant","hard cider","country wine","sake","doburoku","mead"
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
