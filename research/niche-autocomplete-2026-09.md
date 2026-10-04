# Markasız Niş Konular — Google Otomatik Tamamlama Yöntemi

**Neden bu yöntem:** Önceki konuların çoğu büyük markalar hakkındaydı ve denetimde büyük sitelerin o konuları hızla kapattığı görüldü. Bu yöntemde:
1. **Talep kanıtı:** Konular Google'ın kendi otomatik tamamlama önerilerinden geliyor. Google bir aramayı öneriyorsa insanlar onu gerçekten yazıyor.
2. **Marka filtresi:** Amazon, Apple, Google, Ninja, Lodge, Purina gibi markaları içeren sorgular elendi.
3. **Rekabet testi:** Kısa listedeki her sorgu WebSearch ile arandı. Yalnızca ilk sonuçlarda forum, alakasız ya da ince sayfaların baskın olduğu **LOW** sorgular seçildi.

## Kendin çalıştır

```bash
python3 tools/ac_miner.py out.json
```
`tools/ac_miner.py` içindeki `NICHES` listesine kendi hobi alanlarını ekle. Sonuçta ~6 dakikada binlerce uzun kuyruk soru çıkar.
Tüm çıktı: `data/longtail-queries.txt` (7.728 markasız soru, 6+ kelime).

## Rekabet testi sonuçları (60 sorgudan 17 LOW)

| Sorgu | Rekabet | Makale |
|---|---|---|
| why is my hummingbird feeder empty in the morning | LOW | ✅ 55 |
| do guinea pigs eat less in winter | LOW | ✅ 56 |
| why is my rabbit not licking me | LOW | ✅ 57 |
| can dogs get a cold after a bath | LOW | ✅ 58 |
| do leopard geckos eat less in winter | LOW | ✅ 59 |
| how to bathe guinea pigs in winter | LOW | ✅ 60 |
| can you put coffee grounds on plants in the winter | LOW | ✅ 61 |
| can you propagate snake plant in winter | LOW | ✅ 62 |
| hoya leaves turning yellow and falling off in winter | LOW | ✅ 63 |
| can i prune fiddle leaf fig in fall | LOW | ✅ 64 |
| cast iron skillet smells like iron | LOW | ✅ 65 |
| can you cold brew tea at room temperature | LOW | ✅ 66 |
| how to fix squeaky bread machine | LOW (talep küçük olabilir) | ✅ 67 |
| can you put guinea pigs outside after being inside | LOW | ✅ 68 |
| is algae bad for shrimp tank | LOW (sınırda) | ✅ 69 |
| why is my bunny shaking when guest visit | LOW (niyet boşluğu) | — |
| is it normal for pothos leaves to turn yellow in winter | LOW-MED | — |
| how to fix leaning fig tree (dış mekân incir) | LOW açısı | — |

**Sınırda (MED→LOW):** can i leave sourdough discard out overnight · why is my pressure canner not steaming · can you leave a cast iron skillet dirty overnight · slow cooker smells like burning plastic · can you make sourdough starter in winter (sıfırdan, soğuk mutfakta) · should i feed my lemon tree in winter · can you split a peace lily in the fall

**HIGH (kaçın):** hummingbird feeders in winter · cats shed more in fall · kitten alone overnight · catnip fall · cat dandruff winter · snake plants outside winter · compost pile winter · raised beds winter · christmas cactus · orchid branch · cold brew taste bad · sourdough acetone · watery starter · sauerkraut salty · slow cooker watery · tent pole elastic · fountain pen nibs · hiking boot blisters

## Sonraki adım
`data/longtail-queries.txt` içinde 700'den fazla mevsimlik (fall/winter) soru daha var. Her turda 20'şerli grupları test et ve sadece LOW olanları yaz. En iyi sinyal şu: ilk sonuçlarda Reddit, Quora ve forumlar baskınsa, **ya da** büyük siteler sorunun tersini veya daha genel bir versiyonunu cevaplıyorsa.

## Tur 2: Nadir hobiler (`tools/ac_miner_rare.py`, `data/longtail-queries-rare.txt`, 3.982 soru)

Alanlar: bıldırcın, isopod, hermit crab, chinchilla, sugar glider, bonsai, etobur bitkiler, kefir, ginger bug, natto, çömlek, punch needle, metal dedektörü, teleskop, soba, sump pump…
Sonuç: **60 sorgudan 18'i LOW**. Nadir alanlar belirgin şekilde daha iyi çıktı (ilk turda 60'ta 17'ydi, bu turda 60'ta 18, ve boşluklar daha net).

En güçlü sinyal: büyük sitelerin **sorunun tersini** cevaplaması. Örnekler: sugar glider "bite" var, "lick" yok · cockatiel "scream" var, "sing at night" yok · punch needle "loops falling out" var, "loops too big" yok · air dry clay "cracking while drying" var, "while molding" yok.

| Sorgu | Makale |
|---|---|
| why does my hamster squeak when eating | ✅ 70 |
| why is my hamster squeaking when sleeping | ✅ 71 |
| why does my sugar glider lick me | ✅ 72 |
| why does my cockatiel sing at night | ✅ 73 |
| why does my bird sneeze after drinking water | ✅ 74 |
| why is my budgie vibrating his wings | ✅ 75 |
| why does my chinchilla make noises at night | ✅ 76 |
| why is my fermented hot sauce bitter | ✅ 77 |
| why does my natto smell like ammonia | ✅ 78 |
| why does my ginger bug smell like vinegar | ✅ 79 |
| why is my ginger bug soda not carbonating | ✅ 80 |
| why is my rubber plant drooping after repotting | ✅ 81 |
| why is my string of hearts not pink | ✅ 82 |
| why are my punch needle loops so big | ✅ 83 |
| how to make air dry clay shiny | ✅ 84 |
| why is my air dry clay cracking while molding | ✅ 85 |
| can you make ginger bug with coconut sugar | (80'in SSS bölümünde) |
| why is my ducks pool water red · why does my bird bath have a hole in it | LOW ama talep çok küçük |

**Sınırda:** can you punch needle with embroidery floss · can you wet felt after needle felting · is it normal for goats to pant · amaryllis bulb turning red (kırmızı kabuk normal olabilir açısı) · string of hearts flowering · bat circling house (manevi anlam açısı)

## Tur 3 (60 sorgu, 15 LOW)

| Sorgu | Makale |
|---|---|
| why does my soap smell like ammonia | ✅ 86 |
| why does my trail camera keep shutting off | ✅ 87 |
| why did my film camera rewind early | ✅ 88 |
| why does my film camera say s | ✅ 89 |
| why does my quail sound like a frog | ✅ 90 |
| why does my hummingbird feeder smell like vinegar | ✅ 91 (sonuçlar ters soruyu cevaplıyor: "vinegar ile temizleme") |
| why is my guinea pig coughing when eating | ✅ 92 |
| why does my cockatiel hiss at me | ✅ 93 |
| why does my goats face look swollen | ✅ 94 (veteriner konusu, dikkatli yazıldı) |
| why is my dog panting so much in winter | ✅ 95 (en riskli LOW: güçlü genel sayfalar var) |
| why does my water kefir smell like vomit | ✅ 96 |
| how to fix kimchi too much garlic | ✅ 97 |
| why is my lavender plant drooping after repotting | ✅ 98 |
| why does my cold brew taste like alcohol | ✅ 99 |
| why does my cold brew taste like cigarettes | ✅ 100 |

**Sınırda (MEDIUM):** quail crowing at night · pond fish swimming upside down · how to fix hard air dry clay · tufted rugs tufts out · fountain pen not working after refill · trail camera pictures of nothing · well water black suddenly · sauerkraut smells like alcohol · kombucha scoby thin · pour over coffee acidic (mevcut sayfalar kimyayı yanlış anlatıyor) · amaryllis bulb not sprouting · guinea pig bite me softly · parakeet suddenly biting

## Tur 4 ("can you / is it ok" soruları, 60 sorgu, 13 LOW + 1 sınırda)

| Sorgu | Makale |
|---|---|
| can you cut polymer clay after baking | ✅ 101 |
| can you use bread machine yeast for pizza dough | ✅ 102 |
| can you use ginger bug to make bread | ✅ 103 |
| is it ok if cold brew gets warm | ✅ 104 |
| can you use wood stove pellets for cat litter | ✅ 105 |
| can you handle leopard gecko after feeding | ✅ 106 |
| should i feed my leopard gecko after shedding | ✅ 107 |
| can you flush aquarium snails down the toilet | ✅ 108 |
| can you leave budgies alone for a week | ✅ 109 |
| can you put aquarium snails in a pond | ✅ 110 |
| can you eat quail eggs after expiration date | ✅ 111 |
| is it ok for pellet stove to run all the time | ✅ 112 |
| can you soak orchids in water overnight | ✅ 113 |
| can you take hydrangea cuttings in winter | ✅ 114 (sınırda) |

**Gözlem:** Bitki sorularının çoğu HIGH çıktı (Gardening Know How, Gardener's Path ve üniversite yayın siteleri güçlü). En iyi alanlar sırayla: egzotik hayvanlar > fermente/mutfak ikameleri > soba/ev ekipmanı > el işi.
**Sınırda (MEDIUM):** pond fish dog food · isopods + millipedes · bat houses spacing · hermit crab in fish tank · winter white hamsters together · beehive in fall · bird feeders at apartments · candle eggs with flashlight · fiddle leaf fig fruit · forage mushrooms state parks · sea glass collecting legality · milk kefir in fridge (bitmiş içecek açısı) · raw tempeh · crochet blanket cut in half · embroidery normal thread

## Tur 5 (egzotik hayvan + fermente; `tools/ac_miner_exotic.py`, `data/longtail-queries-exotic.txt`, 2.183 soru)

**60 sorgudan 27 LOW**, bugüne kadarki en iyi tur. Egzotik hayvan (özellikle kanatlı: ördek yavrusu, kaz, silkie) ve niş fermente (tepache, kvass, fire cider, tallow, ghee) alanları neredeyse tamamen forum ve JustAnswer ile dolu.

Yazılanlar (115–137): jumping spider on back · hognose twitching · corn snake grey · uromastyx mouth open · box turtle in water · gargoyle gecko upside down · millipedes dying · ducklings sneeze · silkie panting · geese pant · ducklings eat poop · conure naps · geese drool · duckling neck swollen · pigeon attacking · lovebird regurgitate · tepache slimy · tepache not fizzy · grainy whipped tallow · ghee parmesan smell · beet kvass slimy · fire cider cloudy · sourdough pancakes gummy

**LOW ama yazılmadı (talep küçük / cevap kutusu riski):** hognose miss strike · jumping spider no web · ghee not solidifying in winter · canary flapping wings
**Sınırda (MEDIUM, denenebilir):** skink glass surfing · pacman frog deflated · corn snake tail rattle · crested gecko slow motion · conure green poop · zebra finch losing feathers · pet mice squeaking (evcil hayvan açısı) · kefir smells like cheese · fire cider solids

## Tur 6 (derin egzotik + süt ürünü/içki; `tools/ac_miner_deep.py`, `data/longtail-queries-deep.txt`, 1.725 soru)

Not: Bu turda alt ajan aracı hata verdi, rekabet testi doğrudan WebSearch ile 30 sorgu üzerinde yapıldı → **16 LOW**.

**Gözlem:** Ev yapımı süt ürünleri (buttermilk, crème fraîche, mozzarella, ricotta) büyük yemek sitelerince (Tasting Table, Takeout, Nigella, ATK) kapatılmış → HIGH/MEDIUM. Ama **ev yapımı içki (mead, sake)** ve **egzotik hayvan davranışları** hâlâ tamamen forumlarda.

Yazılanlar (138–153): White's tree frog purple · king snake tail shaking · russian tortoise hiss · veiled chameleon digging · tegu heavy breathing · button quail growling · guinea fowl limping · mead rubbing alcohol · sake vinegar · mead rotten eggs · cockatoo sneezing (sonuçlar cockatiel hakkında → niyet boşluğu) · russian tortoise skin peeling · green anole black · feeder hornworms green (sonuçlar bahçe zararlısı hakkında → niyet boşluğu) · mead bubbling over · superworms turning black

**HIGH/MEDIUM (atlandı):** buttermilk separating · creme fraiche split · mozzarella creamy · ricotta dry · homemade wine vinegary · african grey puff up · pygmy goat coughing · springtail culture died · bioactive terrarium smell · axolotl swimming to top · dubia roaches not moving · guinea fowl winter · mini pig grinding teeth

## Tur 7 (60 sorgu, 23 LOW)

**Gözlem:** Kümes hayvanları/su kuşları (kaz, ördek yavrusu, bantam) ve papağan davranışları (conure, lovebird, jako) en verimli alan oldu. Ev yapımı içki/fermantasyon güvenliği sorularında (salsa, sirke, switchel) sonuçlar Quora/forum ağırlıklı.

Yazılanlar (154–175): feeder hornworms turning black · jumping spiders burrow · dubia roaches eating each other · hognose cloudy eyes · tree frogs burrow · bantam chicks dying · geese eating dirt · conure sleeps on back · geese digging holes · ducklings peck each other · conure losing tail feathers · lovebirds sneezing · conure beak peeling · ducklings lay down a lot · african grey clicking (sınırda) · button quail not laying (sınırda) · mead sediment · sick from fermented salsa · mead after 2 weeks · too much switchel · botulism homemade vinegar · churn butter too long

Atlandı (LOW ama tarif sayfaları dolaylı cevaplıyor): ferment carrots and onions together

**MEDIUM (sonraki tura aday):** red eared sliders eating poop · dubia and crickets together · rosy boas together · fermented carrots slimy · sugar in lacto pickles · kvass beets eaten · shio koji raw · tallow separating · skyr separating · sake sediment · fire cider garlic blue · drinking whey · fermented honey garlic cooking · feeder crickets chirping/eating each other · praying mantis upside down · canaries sleep during day · pet rats scratching · ducklings losing feathers · geese honking at night · guinea fowl chasing / eggs not hatching · alpacas lay down · rabbits sleep in litter box

**HIGH (atlandı):** dubia turning white · crested gecko eat shed · pacman frog burying · RES sleep underwater · axolotl shed · bioactive mold · green anoles together · pet rat licks · ginger in beet kvass · ghee turn white · yogurt 24 hours · crested gecko sleep on ground · springtails with tarantulas

## Tur 8 (küçük memeli + kafes kuşu + akvaryum + koji/el işi; `tools/ac_miner_round8.py`, `data/longtail-queries-round8.txt`, 2.762 soru)

Yeni alanlar: ferret, kirpi, degu, evcil fare/gerbil, kanarya, zebra/gouldian ispinozu, parrotlet, caique, eclectus, quaker, hindi palazı, peafowl, sülün, mavi dilli skink, leopar/Hermann kaplumbağası, peygamberdevesi, tarantula, imparator akrep, hermit crab, mystery snail, kerevit, betta/japon balığı/lepistes, akvaryum bitkisi, kiraz karidesi, koji/shio koji/miso/tempeh, turşu yumurta/tuzda yumurta sarısı, elma şarabı, kefir sodası/jun, istiridye mantarı/aslan yelesi, microgreen, hidroponik, etobur bitki, solucan gübresi/bokashi, arı kovanı, reçine, taş tamburu, mum, deri boyası, keçe, lino baskı, tufting.

**59 sorgu test edildi → 21 LOW.** Verim Tur 7'nin biraz altında; sebebi net: bu turda test edilen alanların bir kısmı **kendi niş site ekosistemine sahip** (isopods.co.uk, ladygouldianfinch, unclejimswormfarm, tuftingshop, feltingandfiberstudio, carolinahoneybees, microgreenscorner, thehydroponicsplanet…). Buralara girmek anlamsız.

**Doymuş çıkan alanlar (atla):** el işi malzemeleri (lino, keçe, tufting, taş tamburu, deri boyası, mum, reçine) · yetiştirme (microgreen, hidroponik, mantar kiti, solucan kovası, bokashi) · arıcılık · ferret/gerbil/degu/evcil fare · hermit crab ve mystery snail davranışları · betta/japon balığı eşleştirme soruları · ev yapımı yoğurt/labneh/kefir · elma şarabı kusurları (pricklycider + scottlab kapatmış).

**Hâlâ açık olan alanlar:** kümes/su kuşu yavruları (hindi palazı, ördek yavrusu, kaz) · daha az tutulan papağanlar (eclectus, parrotlet, caique, quaker'ın spesifik davranışları) · ispinoz üretimi · akvaryum **kimya/süreç** soruları (karides molt ölümleri, bitki tutturma) · sürüngen renk/deri soruları · **fermente güvenliği ve oran** soruları (botulizm, salamura tekrar kullanımı, alkol kokusu).

Yazılanlar (176–196):

| Sorgu | Not | Makale |
|---|---|---|
| why do my geese honk at night | sonuçlar yabani Canada geese hakkında | ✅ 176 |
| why are my turkey poults fighting | sonuçlar yetişkin/yabani hindi | ✅ 177 |
| why are my turkey chicks so loud | sadece backyardchickens başlıkları | ✅ 178 |
| why are my turkey eggs soft | forum + tavuk odaklı sayfalar | ✅ 179 |
| why does my eclectus grind his beak | sonuçlar sultan papağanı/muhabbet kuşu | ✅ 180 |
| why is my eclectus regurgitating | JustAnswer + parrotforums | ✅ 181 |
| why is my parrotlet chirping so much | talkparrotlets başlıkları | ✅ 182 |
| why do my zebra finches eat their eggs | JustAnswer + akademik makale | ✅ 183 |
| why are my ducklings losing feathers | sayfalar yetişkin ördek tüy dökümü | ✅ 184 |
| why do my red eared sliders eat poop | sayfalar "kendi dışkısı" versiyonunu cevaplıyor | ✅ 185 |
| why is my blue tongue skink belly red | sadece forum + JustAnswer | ✅ 186 |
| why is my emperor scorpion not eating | tamamen arachnoboards | ✅ 187 |
| why are my cherry shrimp dying after molting | tamamen akvaryum forumları | ✅ 188 |
| aquarium plants not staying in substrate | forum başlıkları | ✅ 189 |
| carnivorous plant smells like rotting meat | sonuçlar titan arum/ceset çiçeği | ✅ 190 |
| fermented garlic honey smells like alcohol | tarif sayfaları tek cümleyle geçiyor | ✅ 191 |
| can you eat the beets from beet kvass | tarif sayfalarında tek satır | ✅ 192 |
| can you leave pickled eggs on the counter | forum + ince içerik çiftliği sayfaları | ✅ 193 |
| can you reuse lacto fermented pickle brine | sayfalar sirkeli salamurayı cevaplıyor | ✅ 194 |
| can you make miso with shio koji | sonuçlar "shio koji nasıl yapılır" | ✅ 195 |
| can you eat oyster mushrooms after they spore | sonuçlar spor toplama hakkında | ✅ 196 |

**MEDIUM (sonraki tura aday):** peahen sesi · leopar kaplumbağası aşırı besleme · zebra ispinozu + sultan papağanı birlikte · mourning dove yerde oturma · mystery snail ters dönme · tempeh soğuk yeme · jun tea gazsız · shio koji çiğ · tuzda yumurta sarısı (sadece tuz) · peygamberdevesi baş aşağı · degu ciyaklama · gerbil yemek saklama

**HIGH (atlandı):** pheasant chicks dying · isopod colony dying · ferret hiccups · gerbils alone after one dies · crayfish molt vs dead · mystery snail eggs moving · gouldian bald · kefir fizzy · bees washboarding · hard cider rotten eggs · worm bin too wet · bokashi smell · microgreens (hepsi) · hydroponic lettuce bitter · carnivorous plant winter feeding · felting needles breaking · tufting gun jamming · leather dye streaky · lino prints patchy · rock tumbler grit · fermented carrots slimy · sugar in lacto pickles · dubia + crickets · rat scratching · rabbit litter box · fire cider blue garlic · garlic honey cooking · feeder crickets cannibalism · canary sleeping daytime · hermit crab chirping/hair · hermann tortoise squeak/pacing · blue tongue skink peeing · quaker parrot purring

**Yöntem notu:** Tur 8'de en güvenilir LOW sinyali yine **niyet boşluğu** oldu (sorunun yabani/vahşi hayvan, farklı tür ya da farklı süreç versiyonunun cevaplanması: kaz, hindi palazı, eclectus, ördek yavrusu, kaplumbağa, etobur bitki, shio koji, istiridye mantarı sporu). İkinci sinyal: **tamamen forum** (akrep, karides, akvaryum bitkisi). Marka/ürün ve "kendi niş sitesi olan hobi" alanlarından uzak dur.
