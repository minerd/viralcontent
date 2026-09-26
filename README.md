# viralcontent — Tech/AI Blog İçerik Sistemi

İngilizce teknoloji / yapay zeka blogu için konu araştırması, yazım yöntemi ve hazır taslaklar.

## Klasörler

| Dosya | Ne işe yarar |
|---|---|
| `research/topics.md` | Eylül 2026 araştırması: hangi içerik trafik alıyor, 5 konu kümesi, 30 günlük yayın planı |
| `method/workflow.md` | Konudan yayına 6 adımlık yöntem + SEO + dağıtım |
| `method/human-writing-guide.md` | AI izlerini silme rehberi, yasaklı kelimeler, yayın öncesi kontrol listesi |
| `templates/draft-prompt.md` | Taslak ve düzeltme için hazır prompt |
| `research/idea-bank.md` | 40 orijinal başlık, kategori ve yayın sırasıyla |
| `research/trend-radar-2026-09.md` | Eylül 2026 trend radarı: yeni AI ürünleri, yeni terimler, cihazlar, para/sağlık, markalar (~60 konu, kaynaklı) |
| `research/low-competition-2026-09.md` | Az rekabetli konular: Google rekabet testi, forum soruları, Product Hunt, GitHub/HN, Exploding Topics (~90 konu) |
| `research/niche-autocomplete-2026-09.md` | **Markasız niş yöntem**: Google otomatik tamamlama + rekabet testi |
| `tools/ac_miner.py` + `data/longtail-queries.txt` | Konu madencisi ve 7.728 gerçek, markasız soru |
| `tools/ac_miner_rare.py` + `data/longtail-queries-rare.txt` | Nadir hobiler için madenci ve 3.982 soru |
| `tools/ac_miner_exotic.py` + `data/longtail-queries-exotic.txt` | Egzotik hayvan + fermente madencisi, 2.183 soru |
| `articles/` | 137 İngilizce makale |

## Makaleler

1. **Claude vs ChatGPT vs Gemini for Writing** — karşılaştırma (en kalıcı trafik)
2. **Will AI Take My Job?** — yüksek arama hacmi
3. **How to Use NotebookLM to Study Anything** — öğrenci sezonu
4. **Family Safe Word vs AI Voice Scams** — en paylaşılabilir, yayına hazır
5. **Why Does ChatGPT Agree With Everything I Say?** — yayına hazır
6. **AI Agents: 9 Rules Before You Let Them Click** — güncel, yayına hazır
7. **Ask AI What You're Missing** — görüş/rehber, yayına hazır
8. **How to Tell If an Image Is AI in 2026** — yayına hazır
9. **The AI Subscription Audit** — fiyat notu hariç hazır
10. **Gemini Call for Me** — güncel, 1 kontrol notu var

11. **Sora's API Is Gone** — haber, geliştirici kitlesi
12. **The 'Ban Superintelligence' Bill, Explained** — haber
13. **How to Explain AI Scams to Your Parents** — güvenlik serisi
14. **Just Got Scammed? What to Do in the First Hour** — güvenlik serisi
15. **What Is Prompt Injection?** — açıklayıcı
16. **Can Teachers Tell If You Used AI?** — öğrenci sezonu
17. **Will AI Replace Translators?** — meslek serisi #1
18. **Your AI Chats Aren't as Private as You Think** — gizlilik
19. **5 Custom Instructions Worth Copying** — kopyala-yapıştır
20. **Google Answers Everything. Why Do Blogs Still Exist?** — görüş

21. **iPhone 18 Pro Keeps Restarting After Face ID?** — sorun çözme, iOS 27.0.1 çıkınca güncelle
22. **Where's the Regular iPhone 18? (iPhone Duo)** — merak + satın alma
23. **The Fed Just Raised Rates** — para
24. **Are You a 'Meat Proxy'? New AI Slang** — yeni terimler
25. **New Dictionary Words 2026 (Looksmaxxing, Crashout…)** — yeni terimler, ebeveynler
26. **Fibermaxxing** — sağlık trendi
27. **Google Assistant Is Gone** — "ne oldu?" araması
28. **What Is Meta Muse?** — yeni AI markası (+ Instinct)
29. **Googlebook vs Chromebook** — yeni ürün, 4 Ekim'den önce yayınla
30. **Ozempic Maker Is Now 'Novo'** — sağlık + iş dünyası

31–44: **az rekabetli** yeni özellik/forum sorunları (Pinterest Restyle, YouTube custom feeds, Microduck, Bonsai 2, Clementine, ghostlighting, agent washing, watchOS 27 Siri timer, Siri AI sorunları, Siri AI neden yok, Astra/Sol/Luna, Spotify Taste Profile, Pixel Health Guardian, Android Motion Assist)

45–54: **Product Hunt / GitHub / trend terimleri** (Voiskey vs MosMos vs Loqua, Zella, ToneBird, world model / PixVerse R2, Human Atlas, Spotifast, Fugleramme, Remember November 2026 meme, Jimothy raccoon, run club friends)

55–69: **Markasız niş sorular** (Google önerisi = talep var, rekabet testi = LOW): hummingbird feeder, guinea pig kış bakımı, rabbit, dog bath, leopard gecko, coffee grounds, snake plant, hoya, fiddle leaf fig, cast iron, cold brew tea, bread machine, shrimp tank

70–85: **Nadir hobiler** (hamster, sugar glider, cockatiel, budgie, chinchilla, fermente acı sos, natto, ginger bug, rubber plant, string of hearts, punch needle, air dry clay). Büyük siteler buralarda sorunun ya **tersini** ya da daha genelini cevaplıyor.

86–100: **Tur 3 nadir sorular** (milk soap ammonia, trail camera, film camera, quail, hummingbird nectar, guinea pig cough, cockatiel hiss, goat swelling, dog winter panting, water kefir, kimchi garlic, lavender, cold brew ×2)

101–114: **Tur 4 "olur mu?" soruları** (polymer clay, bread machine yeast, ginger bug bread, cold brew warm, pellet cat litter, leopard gecko ×2, aquarium snails ×2, budgies alone, quail eggs, pellet stove 24/7, orchid soak, hydrangea cuttings)

115–137: **Tur 5 egzotik hayvan + niş fermente** (60 sorgudan 27 LOW, en iyi tur): sürüngen, eklembacaklı, ördek/kaz/silkie, papağan türleri, tepache, kvass, fire cider, tallow, ghee

⚠️ Denetim notu: 31–54 arasındaki marka/ürün yazılarının çoğunun rekabeti sonradan yüksek çıktı. Ayrıntı `research/low-competition-2026-09.md` bölüm 7'de.

4–137 arası yazılar deneyim gerektirmeyen açılarla yazıldı; 1–3'teki `[ADD]` yerleri kendi testlerinle doldurulmalı.

Taslaklardaki `[ADD: ...]` yerleri senin gerçek deneme sonuçların ve ekran görüntülerinle doldurulmalı.
Bu kısım bilerek boş: yazıyı Google'da sıralatan ve insan yazmış gibi hissettiren şey tam olarak o.

## Başlangıç
1. `research/topics.md` oku
2. `articles/01` için 5 görevi üç modele ver, sonuçları doldur
3. `method/human-writing-guide.md` kontrol listesini uygula, yayınla
