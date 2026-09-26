# Yöntem — Konudan Yayına 6 Adım

Hedef: haftada 2–3 yazı, her biri insan yazmış gibi okunan ve **gerçekten işe yarayan**.
Yapay zeka taslağı hızlandırır; yazıyı sıralatan şey **senin eklediğin kısım**dır.

## Adım 1 — Konu seç (15 dk)
`research/topics.md` listesinden veya haftalık taramadan bir konu al. Kendine şu 3 soruyu sor:
- Bunu aratan kişi **ne karar vermeye** çalışıyor?
- İlk 5 Google sonucunda **eksik** olan ne? (eski mi, yüzeysel mi, test yok mu?)
- Benim **ekleyebileceğim** bir şey var mı? (deneme, ekran görüntüsü, net fikir)

Üçüncü soruya cevabın yoksa konuyu değiştir.

## Adım 2 — Kendin dene (30–60 dk) ⭐ en önemli adım
Yazıdan önce aracı/konuyu **gerçekten kullan**:
- Karşılaştırma yazısıysa: aynı görevi her araca ver, sonuçları kaydet.
- Rehberse: adımları kendin uygula, ekran görüntüsü al.
- Görüş yazısıysa: 2–3 kişiye sor veya Reddit'te insanların ne dediğini oku.

Notlarını kısa tut: "Gemini tabloyu bozdu", "Claude 2. denemede doğru yaptı" gibi. Bu notlar yazının ruhu olacak.

## Adım 3 — Taslak (20 dk)
`templates/draft-prompt.md` içindeki promptu kullan. Promptun içine **Adım 2 notlarını** yapıştır.
Notsuz taslak = herkesinkiyle aynı yazı.

## Adım 4 — İnsanlaştırma düzeltmesi (30 dk)
`method/human-writing-guide.md` kontrol listesini baştan sona uygula. Özellikle:
- Yasaklı kelimeleri sil
- Girişi yeniden yaz (ilk cümle = somut bir şey)
- En az 3 yere kendi deneyimini/fikrini ekle
- Sesli oku; takıldığın cümleyi kısalt

## Adım 5 — SEO ve yayın hazırlığı (15 dk)
- **Başlık**: ana kelime başta, 60 karakter altı, merak veya sayı içersin.
- **URL**: kısa, `/claude-vs-chatgpt-vs-gemini-writing`
- **Meta açıklama**: 150 karakter, sonuç vaat et.
- **H2'ler**: insanların aradığı sorular (Google "People also ask" kutusundan al).
- **Görseller**: kendi ekran görüntülerin. Stok görsel kullanma.
- **İç link**: aynı kümeden en az 2 yazıya bağlantı.
- **Tarih**: yazının üstünde "Updated: Eylül 2026" — güncel içerik tıklanır.
- **Yazar kutusu**: gerçek isim + kısa bio. Anonim blog 2026'da zor sıralanıyor.

## Adım 6 — Dağıtım ve güncelleme
Sadece Google'a bırakma, ilk trafiği kendin getir:
- Reddit: ilgili subreddit'te **linksiz** faydalı bir özet yaz, yorumda link ver (kurallara bak).
- X/Twitter: yazıdaki en çarpıcı bulguyu tek tweet yap.
- Hacker News: sadece geliştirici konuları için.
- **30 günde bir** en çok trafik alan 5 yazıyı güncelle (yeni model çıktıysa ekle, tarihi değiştir).

## Yapma listesi
- ❌ Günde 20 yapay zeka yazısı basmak (Google'ın spam politikası tam olarak bunu hedefliyor)
- ❌ Denemediğin bir aracı "test ettim" diye yazmak — okuyucu fark eder, güven biter
- ❌ Uydurma istatistik. Her sayıya kaynak link ver.
- ❌ Başkasının yazısını AI ile "yeniden yazdırmak"

## Ölçüm
Google Search Console'u bağla. 4 hafta sonra bak:
- Gösterim çok, tıklama az → başlık/meta zayıf, yeniden yaz.
- Tıklama var, sayfada süre kısa → giriş zayıf, ilk paragrafı düzelt.
- Hiç gösterim yok → konu çok rekabetli, daha uzun kuyruk bir versiyonunu yaz.
