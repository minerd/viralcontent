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
