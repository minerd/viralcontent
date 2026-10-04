import json, subprocess, urllib.parse, concurrent.futures as cf, re, sys, time

# Round 9: the seams round 8 found still open —
# poultry/waterfowl chicks, less-common parrots, finch breeding,
# aquarium process/chemistry, reptile skin & colour, fermentation safety/ratio.
NICHES = [
 # game birds, waterfowl, poultry young stock
 "chukar","partridge chicks","call ducks","runner duck","muscovy ducklings","pekin ducklings",
 "goslings","serama","silkie chicks","frizzle chickens","coturnix quail chicks","gambel quail",
 "homing pigeons","squab","ringneck doves","diamond doves","pigeon squeakers",
 # less-common parrots and finches
 "senegal parrot","meyers parrot","pionus","indian ringneck","alexandrine parakeet","rosella",
 "lorikeet","green cheek conure","amazon parrot","bourke parakeet","linnie parrot",
 "society finches","java sparrow","canary chicks","finch nest","hand feeding formula",
 # aquarium process
 "nerite snails","amano shrimp","sponge filter","cycling a tank","guppy fry","betta fry",
 "snail eggs","aquarium cycling","fish fry","brine shrimp hatchery","live plants melting",
 # reptile skin and colour
 "crested gecko shedding","mourning gecko","sand boa","garter snake","ackie monitor",
 "leachianus","chahoua","frog shedding","toad","axolotl gills",
 # ferment and brew
 "amazake","doburoku","natto starter","idli batter","dosa batter","injera","kefir cheese",
 "sourdough discard","perry","country wine","kilju","hard seltzer","root beer","birch sap",
 "salt rising bread","koji amazake","nukazuke","miso aging","soy sauce moromi","vinegar mother",
]
STEMS = [
 "why is my {n}","why does my {n}","why are my {n}","is it normal for {n}","how to fix {n}",
 "can you {n}","what to do if my {n}","{n} smells like","{n} turning","{n} not",
 "how long does {n}","is it safe to {n}",
]
BRANDS = re.compile(r"\b(amazon|walmart|target|costco|apple|iphone|ipad|samsung|google|pixel|android|chatgpt|openai|gemini|meta|facebook|instagram|tiktok|youtube|netflix|spotify|microsoft|windows|xbox|playstation|nintendo|tesla|ikea|starbucks|nespresso|keurig|ninja|instant pot|instapot|lodge|le creuset|kitchenaid|cuisinart|dyson|roomba|nike|adidas|hoka|brooks|asics|merrell|rei|home depot|lowes|miracle gro|scotts|purina|chewy|petco|petsmart|blue buffalo|hills|royal canin|fiskars|pampered chef|hamilton beach|breville|bodum|chemex|hario|aeropress|v60|traeger|weber|oklahoma joe|pit boss|cricut|singer|lion brand|red heart|yankee|bath and body|mason|ball|zoo med|exo terra|fluval|seachem|api|tetra|etsy|temu|shein|dollar tree|michaels|hobby lobby|joann|harbor freight|kaytee|zupreem|harrisons|exact|tropican|nutribird|mazuri|repashy|pangea|co-?op|aqueon|marineland|eheim|oase|twinstar|ada|tropica|dennerle)\b", re.I)

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
tails = [" after", " in winter", " overnight", " suddenly", " at night", " first time"]
lvl2 = [s+t for s in lvl2_seeds for t in tails]
with cf.ThreadPoolExecutor(16) as ex:
    for q, sugg in zip(lvl2, ex.map(ac, lvl2)):
        for s in sugg:
            res.setdefault(s, q)
clean = sorted({s for s in res if not BRANDS.search(s) and len(s.split()) >= 6})
json.dump(clean, open(sys.argv[1],"w"), indent=0)
print(len(res), "total;", len(clean), "long-tail non-brand")
