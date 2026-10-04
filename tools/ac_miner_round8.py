import json, subprocess, urllib.parse, concurrent.futures as cf, re, sys, time

# Round 8: small mammals, cage birds, inverts/aquarium, koji/miso/tempeh family,
# cider/country wine, craft materials and small-scale growing (mushrooms, worm bin, bees).
NICHES = [
 "ferret","hedgehog","degu","pet rat","pet mice","gerbil","guinea fowl keets","chinchilla dust",
 "canary","zebra finch","gouldian finch","parrotlet","caique","eclectus","quaker parrot","dove",
 "turkey poults","peafowl","pheasant chicks","runner ducks",
 "ball python","bearded dragon","blue tongue skink","hermanns tortoise","leopard tortoise",
 "praying mantis","tarantula","emperor scorpion","hermit crab","isopod colony","crayfish",
 "mystery snail","betta fish","goldfish","guppies","aquarium plants","shrimp colony",
 "koji","shio koji","miso","tempeh","lacto fermented pickles","fermented garlic honey",
 "pickled eggs","cured egg yolks","homemade yogurt","labneh","hard cider","country wine",
 "kefir soda","jun tea","mushroom grow kit","oyster mushrooms","lions mane","microgreens",
 "hydroponic lettuce","carnivorous plant","worm bin","bokashi bucket","beehive",
 "epoxy resin","rock tumbler","candle making","leather dye","wood burning","needle felting",
 "macrame","weaving loom","bookbinding glue","calligraphy ink","lino print","tufting gun",
]
STEMS = [
 "why is my {n}","why does my {n}","why are my {n}","is it normal for {n}","how to fix {n}",
 "can you {n}","what to do if my {n}","{n} smells like","{n} turning","{n} not",
]
BRANDS = re.compile(r"\b(amazon|walmart|target|costco|apple|iphone|ipad|samsung|google|pixel|android|chatgpt|openai|gemini|meta|facebook|instagram|tiktok|youtube|netflix|spotify|microsoft|windows|xbox|playstation|nintendo|tesla|ikea|starbucks|nespresso|keurig|ninja|instant pot|instapot|lodge|le creuset|kitchenaid|cuisinart|dyson|roomba|nike|adidas|hoka|brooks|asics|merrell|rei|home depot|lowes|miracle gro|scotts|purina|chewy|petco|petsmart|blue buffalo|hills|royal canin|fiskars|pampered chef|hamilton beach|breville|bodum|chemex|hario|aeropress|v60|traeger|weber|oklahoma joe|pit boss|cricut|singer|lion brand|red heart|yankee|bath and body|mason|ball|zoo med|exo terra|fluval|seachem|api|tetra|oxballs|etsy|temu|shein|dollar tree|michaels|hobby lobby|joann|harbor freight|resin8|art resin|totalboat)\b", re.I)

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
lvl2_seeds = [s for s in res if len(s.split()) >= 5 and not BRANDS.search(s)]
tails = [" after", " in winter", " overnight", " suddenly", " at night"]
lvl2 = [s+t for s in lvl2_seeds for t in tails]
with cf.ThreadPoolExecutor(16) as ex:
    for q, sugg in zip(lvl2, ex.map(ac, lvl2)):
        for s in sugg:
            res.setdefault(s, q)
clean = sorted({s for s in res if not BRANDS.search(s) and len(s.split()) >= 6})
json.dump(clean, open(sys.argv[1],"w"), indent=0)
print(len(res), "total;", len(clean), "long-tail non-brand")
