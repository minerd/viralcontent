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
