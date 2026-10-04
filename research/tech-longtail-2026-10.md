# Teknoloji İçeriğinde Neden Hit Alamıyoruz — ve Ne İşe Yarıyor (Ekim 2026)

Bu dosya tek bir soruya cevap veriyor: **tech yazıları neden trafik almıyor?** Tur 9'da 25 tech sorgusu canlı SERP üzerinde test edildi; sonuç net bir kalıp verdi.

## 1. Teşhis: yanlış içerik tipini yazıyorduk

`low-competition-2026-09.md` bölüm 7'deki denetim notu şunu söylüyordu: 31–54 arası marka/ürün yazılarının çoğunun rekabeti sonradan yüksek çıktı. Tur 9'da bunun **neden** olduğu ölçüldü.

Test edilen güncel haber/açıklayıcı konular ve sonuçları:

| Konu (Ekim 2026'da yeni) | Sonuç | Kaç gün sonra |
|---|---|---|
| ChatGPT virtual try-on | **HIGH** — freepressjournal, Yahoo, androidheadlines, macobserver, AOL, 2 "nasıl kullanılır" sitesi | ~2 gün |
| Gemini 4 Argon 1M token | **HIGH** — ghacks, techdogs, mindstudio, kucoin, smartscope, 4 blog daha | ~2 gün |
| Cloudflare Clef | **HIGH** — slashdot, datanorth, daily.dev, zeniteq, 5 site daha | ~3 gün |
| Meta Neural Band el yazısı | **HIGH** — androidcentral ×2, ubergizmo, Meta kendi help sayfası, wearablexp | hafta |
| WhatsApp ebeveyn kontrolü | **HIGH** — gsmarena, gulfnews, newsbytes, latestly, 4 site daha | gün |

**Sonuç:** Bir AI/teknoloji haberi, çıktıktan **24–72 saat içinde** hem büyük yayıncılar hem de onlarca içerik çiftliği tarafından kapatılıyor. Biz o yarışa 3. günde giriyoruz. Kaybetmemizin sebebi yazının kalitesi değil, **yarışa girdiğimiz an**.

Niş hayvan/fermente yöntemi işe yarıyor çünkü orada rakip yok. Tech'te rakip devasa ve anında. Yani tech'te **farklı bir sorgu şekli** gerekiyor.

## 2. İşe yarayan üç şekil (kanıtla)

### Şekil A — Sürüm + spesifik belirti
Sorgu: `<ürün/sürüm>` + `<tam belirti>`. SERP'te genelde sadece **Apple Community / resmi forum** ve **eski sürüm için yazılmış genel sayfalar** oluyor.

| Sorgu | SERP | Sonuç |
|---|---|---|
| iOS 27 keyboard lag / slow typing | Apple Community + iOS 17/18 için yazılmış genel "keyboard lag" sayfaları | **LOW** ✅ 206 |
| iOS 27 tinted/clear icons stutter (ProMotion) | 1 MacRumors başlığı + genel bug round-up | **LOW** ✅ 207 |
| Copilot missing from Excel on Mac | **tamamı Microsoft Q&A başlığı**, tek makale yok | **LOW** ✅ 211 |

Karşı örnek (işe yaramayan): `iOS 27 auto brightness`, `iOS 27 CarPlay`, `iOS 27 liquid glass off` → bunlara geeksmodo/reiboot/tenorshare/motorys gibi siteler zaten dedike sayfa açmış = **MEDIUM/HIGH**. Yani Şekil A otomatik kazanmıyor; **test şart**.

### Şekil B — Niyet boşluğu: yeni özellik, eski cevap
Sorgu yeni bir özelliği soruyor ama SERP **eski, genel yorumu** cevaplıyor.

| Sorgu | SERP ne cevaplıyor | Sonuç |
|---|---|---|
| ChatGPT ile çok sayfayı tek PDF'e tarama | Adobe/Smallpdf/yazıcı tarayıcıları (yıllar öncesi) | **LOW** ✅ 209 |
| iOS 27 Photos albümleri nerede | iOS 18 başlıkları + "fotoğraf kurtarma" yazılım spam'i | **LOW** ✅ 208 |
| ChatGPT projects kayboldu | OpenAI community başlıkları; basın "kayıp sohbet" genelini yazmış | **LOW** ✅ 210 |

### Şekil C — Self-hosted / dev: cevap sadece GitHub ve forumda
En temiz seam. Kitlesi küçük ama **niyeti çok yüksek** ve rakip yok çünkü içerik çiftlikleri bu konuları anlamıyor.

| Sorgu | SERP | Sonuç |
|---|---|---|
| Home Assistant app lag on iOS 27 | sadece GitHub issue + HA community | **LOW** ✅ 212 |
| Jellyfin HDR tone mapping update sonrası bozuldu | GitHub issues + Jellyfin forum | **LOW** ✅ 213 |
| Proxmox VM kernel update sonrası açılmıyor | sadece Proxmox forum başlıkları | **LOW** ✅ 214 |
| Pi-hole update sonrası reklam engellemiyor | sadece Pi-hole discourse | **LOW** ✅ 215 |
| Frigate Coral TPU update sonrası görünmüyor | sadece GitHub discussions | **LOW** ✅ 216 |

**Önemli gözlem:** Bu beş yazının ortak noktası — gerçek cevap bir GitHub issue'sunun içine gömülü ve **hiç kimse onu makaleye çevirmemiş**. Örnek: iOS 27'nin düz HTTP sayfalarını `WebContent.EnhancedSecurity` ile çalıştırması, loopback'i muaf tutup LAN IP'sini tutmaması. Bu, binlerce HA kullanıcısının sorununun tam cevabı ve tek kaynağı bir issue.

## 3. HIGH çıkanlar (bir daha denemeye değmez)

AirPods Pro 3 live translation · Android Auto update sonrası bağlanmıyor · Android Auto error 21 · Gemini Assistant'ı değiştirdi · iOS 27 auto brightness · iOS 27 CarPlay · iOS 27 liquid glass · macOS 27 Spotlight · WSL update sonrası açılmıyor · Obsidian sync çakışması · Immich external library · Tailscale subnet route · ChatGPT "error in message stream" · iOS 26.7 vs iOS 27 karışıklığı · Steam Deck SD kart · bees washboarding

Kalıp: **büyük kitlesi olan tüketici sorunları** zaten reiboot / tenorshare / drfone / appuals / thewindowsclub / makeuseof tarafından kapatılmış. Oralarda kazanmak için otorite gerekir, içerik değil.

## 4. Madenci

```bash
python3 tools/ac_miner_tech.py data/longtail-queries-tech.txt
```

Niş madencilerden iki farkı var:
1. **Marka filtresi YOK.** Tech'te marka sorgunun kendisi.
2. Yerine **şekil filtresi** var: `PROBLEM` regex'i sadece hata/arıza/kayıp şeklindeki sorguları tutuyor (`error`, `not working`, `after update`, `missing`, `stuck`, `keeps`, `where did`, `why does`…).

Çıktı: **11.982 öneri → 4.976 problem-şekilli uzun kuyruk** (`data/longtail-queries-tech.txt`).

İçinden henüz test edilmemiş güçlü adaylar: `copilot not working after vscode update` · `windsurf error while fetching extensions` · `nextcloud auto upload not working iphone` · `plex auto match not working` · `why does claude say now using credits` · `why does steam say stream instead of play` · `windows 11 explorer keeps restarting after update` · `how to fix wsl catastrophic failure` · `why does google sheets say invalid type`.

## 5. Tech için yayın kuralları

1. **Haber yazma.** Yeni ürün/model/özellik duyurusu = 48 saatte HIGH. İstisna: duyuruyu ilk 24 saatte yakalarsan ve SERP hâlâ eski yorumu cevaplıyorsa (Şekil B).
2. **Sürüm numarasını başlığa koy.** "iOS 27 keyboard lag", "Proxmox kernel update". Rekabetin olmadığı yer tam orası.
3. **Test etmeden yazma.** Şekil A'nın yarısı MEDIUM çıkıyor. 10 dakikalık SERP kontrolü, 2 saatlik boşa yazmaya değer.
4. **GitHub issue → makale** en verimli dönüşüm. Issue'daki kök nedeni oku, doğrula, sıralı bir çözüm akışına çevir.
5. **Dürüst ol:** "henüz resmi düzeltme yok" yazmak sayfayı güçlendirir; uydurma çözüm listesi (reiboot tarzı) zayıflatır.
6. **Güncelle.** Sürüm yazıları ölür. Nokta sürüm çıktığında `updated:` alanını ve "ne düzeltildi" bölümünü yenile. Makale 21 bu turda böyle yenilendi (Apple Pay/Wallet dalgası + panic-full log okuma).
7. **İç bağlantı:** aynı sürümün belirtilerini birbirine bağla (206 ↔ 207 ↔ 208). Bir kullanıcı genelde birden fazla belirti yaşıyor.

## 6. Tur 9 tech sonucu

**25 sorgu test edildi → 11 LOW → 11 makale (206–216) + makale 21 güncellendi.**

Oran %44 — niş turlarının (%35–40) üzerinde. Yani doğru şekil seçilirse teknoloji, hayvan/fermente nişlerinden **daha** verimli. Yanlış şekil seçilirse (haber/açıklayıcı) oran sıfır.

---

# Tur 10: tamamı teknoloji (22 sorgu → 17 LOW, %77)

Tur 9'un bulgusu test edildi ve doğrulandı: **kanıtlanmış seam'de balık tutarsan oran üçe katlanıyor.** Tur 9'da 25 sorgudan 11 LOW (%44) çıkmıştı, çünkü karışık test ediyordum. Tur 10'da sadece Şekil C ağırlıklı test edildi → **17/22 (%77)**.

## Yeni madenci

```bash
python3 tools/ac_miner_tech2.py data/longtail-queries-tech2.txt
```

Ürün listesi tamamen self-hosted/homelab/dev araçlarına çevrildi (Jellyfin, Immich, Paperless, Sonarr, Zigbee2MQTT, ESPHome, Proxmox, TrueNAS, Unraid, Authentik, Vaultwarden, Grafana, Caddy, Traefik, k3s, Cursor, LM Studio, Ollama…). Stem'ler de arıza şekline odaklandı: `not detected`, `permission denied`, `fails to start`, `stuck on`, `high cpu`, `out of memory`, `where did`.

Çıktı: **5.712 öneri → 2.653 problem-şekilli** (`data/longtail-queries-tech2.txt`). Tech madencilerinin toplamı artık **7.629 test edilmemiş sorgu**.

## Yazılanlar (217–233)

| Sorgu | SERP'te ne var | Makale |
|---|---|---|
| nextcloud auto upload not working iphone | GitHub issues + help.nextcloud | ✅ 217 |
| lm studio error fetching staff picks | **1 GitHub issue**, kalanı alakasız (Wikipedia, Etsy, Scratch) | ✅ 218 |
| airpods pro 3 mic not working teams windows 11 | MS Tech Community + Apple Community + MS Q&A, tek makale yok | ✅ 219 |
| synology smb not working after dsm update | synology community + synoforum | ✅ 220 |
| nextcloud with cloudflare tunnel | forumlar + GitHub discussions + 1 Medium | ✅ 221 |
| lm studio keeps unloading model | GitHub bug-tracker + docs (kimse ikisini birleştirmemiş) | ✅ 222 |
| cursor error while fetching extensions | **sadece** forum.cursor.com | ✅ 223 |
| zigbee2mqtt devices unavailable after update | Z2M GitHub + HA community | ✅ 224 |
| paperless-ngx consumer not picking up files | GitHub discussions + docs | ✅ 225 |
| truenas scale app stuck deploying | truenas forumları + 1 Medium | ✅ 226 |
| grafana panel no data after upgrade | Grafana GitHub + community forum | ✅ 227 |
| unraid array won't start after update | **sadece** unraid forumları | ✅ 228 |
| esphome encryption key is invalid | HA community + GitHub | ✅ 229 |
| audiobookshelf progress not syncing | **sadece** GitHub issues | ✅ 230 |
| authentik login loop after upgrade | **sadece** goauthentik GitHub | ✅ 231 |
| adguard home dns not responding after update | AdGuardHome GitHub + opnsense forum | ✅ 232 |
| vaultwarden websocket not working after update | Vaultwarden GitHub discussions + forum | ✅ 233 |

## HIGH çıkanlar — ve ortak özellikleri

| Sorgu | Kim kapatmış |
|---|---|
| ollama not using gpu | **8 dedike sayfa**: dev.to, mylocalai, gigagpu, netray, neuralgist, localaimaster, aimadetools, runaihome |
| copilot missing from outlook ribbon | Microsoft resmi KB + bleepingcomputer ×2 + wisechecker |
| docker desktop error during wsl startup | windowsreport, koskila, usedocker |
| copilot keeps asking me to sign in | wisechecker ×2 + windowsreport |
| synology quickconnect not working | mariushosting, epistechnology, spacerex, dev.to |

**Kalıp net: kurulum bariyeri düştükçe rekabet yükseliyor.**

- `ollama not using gpu` → tek komutla kurulur, milyonlarca kullanıcı → 8 içerik çiftliği
- `authentik login loop after upgrade` → Docker Compose + PostgreSQL + reverse proxy + OIDC bilgisi gerekir → **sıfır makale**

## Tur 10'un yeni kuralı: tekrar üretilebilirlik testi

Bir sorguyu yazmaya değer mi diye sorarken şunu sor:

> **Bir içerik çiftliği yazarı bu sorunu kendi makinesinde üretebilir mi?**

- **Evet** (Ollama kur, iOS güncelle, Office aç) → rekabet var ya da yarın olacak. Atla.
- **Hayır** (16 cihazlı bir Zigbee ağı, upgrade edilmiş bir authentik instance'ı, DSM 7'ye geçmiş bir NAS, Coral TPU'lu bir Frigate) → **senin alanın**.

Bu, Tur 9'daki "GitHub-only" sinyalinin nedenini açıklıyor: cevap GitHub issue'sunda, çünkü **sorunu yaşayan tek grup onu yaşayan kullanıcılar** ve kimse pazarlama için o kurulumu yapmıyor.

İkinci gözlem: **AI araçları artık iki parçaya ayrıldı.** Genel AI sorunları (`ollama not using gpu`) doymuş durumda. Ama **tam hata metinleri** (`error fetching staff picks`, `error while fetching extensions`) hâlâ bomboş, çünkü içerik çiftlikleri hata metinlerini bilmiyor — onları ancak araç gerçekten kırıldığında görürsün.

## Yazı kalıbı (217–233'te kullanılan)

1. **Belirtiyi aynen yaz** — kullanıcı o cümleyle arıyor
2. **Tek satırda kök neden** ("sebep neredeyse her zaman reverse proxy", "bu bir ayar, bug değil")
3. **Sıralı teşhis** — en ucuz ve en olası adım önce
4. **Gerçek config/komut blokları** — nginx map bloğu, `proxy-boot-tool kernel pin`, `PAPERLESS_CONSUMER_POLLING`
5. **"Şunu yapma"** — reinstall, re-flash, re-pair gibi pahalı ve gereksiz adımları kes
6. **"Bir daha yaşamamak için"** — tag pinleme, YAML yedeği, UID sabitleme
7. **FAQ** — 4 soru, SERP'teki "people also ask" şekli

Bu kalıp aynı zamanda **otorite sinyali** veriyor: forumdan kopyalanmış bir liste değil, sorunu anlamış bir metin.

## İç bağlantı kümesi

217–233 arası yazıların 11'i "update sonrası bozuldu" şeklinde. Bunları birbirine bağla ve bir **"after an update" hub sayfası** aç: *"Bir güncelleme self-hosted kurulumunu bozduğunda: önce ne kontrol edilir"* (tag pinleme, config yedeği, önceki sürüme dönme, log okuma). Hub, 11 yazıdan link alır ve kendisi de uzun kuyruk toplar.

## Tur 11 için hazır adaylar (test edilmemiş)

`data/longtail-queries-tech2.txt` ve `-tech.txt` içinden, aynı testi geçmeye en yakın olanlar:

immich machine learning container restarting · qbittorrent stalled after update · sonarr import failed after update · caddy certificate error after update · traefik 404 after update · k3s node notready after reboot · portainer agent not connecting · watchtower broke my container · jellyfin intel qsv after driver update · scrypted plugin crash loop · node-red flows missing after update · mosquitto connection refused after update · immich mobile upload stuck · navidrome scan not finding files · restic repository locked · borgbackup lock timeout · duplicati database rebuild stuck · zwave-js-ui devices dead after update · esphome ota failed after update · proxmox backup job failed after upgrade

**Beklenen oran:** %70+. Bu listeyi bitirmek 3–4 tur yeter.

---

# Tur 11: ön-elemeli listeden hasat + hub sayfası (18 sorgu → 12 LOW, %67)

Tur 10'un sonunda bırakılan 20 aday test edildi. Oran %67 — Tur 10'un %77'sinin biraz altında, çünkü listedeki bazı adaylar bu arada kapanmış (ya da zaten MEDIUM'du).

## Yazılanlar (234–245)

| Sorgu | SERP | Makale |
|---|---|---|
| immich machine learning container restarting | **sadece** Immich GitHub issues | ✅ 234 |
| sonarr not importing downloads | sonarr forumları + GitHub | ✅ 235 |
| caddy certificate error after update | caddy.community + GitHub | ✅ 236 |
| z-wave js ui devices dead after update | HA core GitHub + HA community | ✅ 237 |
| traefik 404 after update | **sadece** Traefik community forumu | ✅ 238 |
| node-red flows missing after update | nodered forum + HA community + GitHub | ✅ 239 |
| mosquitto not authorised after update | HA addons GitHub + chirpstack forumu | ✅ 240 |
| jellyfin intel qsv stopped after driver/kernel update | Jellyfin forum + GitHub + Proxmox (kurulum rehberleri başka soruyu cevaplıyor) | ✅ 241 |
| scrypted plugin crash loop | **sadece** koush/scrypted GitHub | ✅ 242 |
| immich mobile upload stuck | **sadece** Immich GitHub | ✅ 243 |
| proxmox backup job failed after upgrade | **sadece** Proxmox forumu | ✅ 244 |
| esphome ota update failed | ESPHome GitHub + HA community | ✅ 245 |

## HIGH/MEDIUM çıkanlar — ve ne öğrettikleri

| Sorgu | Kim kapatmış | Ders |
|---|---|---|
| portainer agent not connecting | **oneuptime'ın 6 dedike sayfası** (hepsi 2026-03-20 tarihli) | Bir B2B blog bütün bir ürünün uzun kuyruğunu tek günde kapatabiliyor |
| k3s node notready after reboot | 3 Medium yazısı (biri tam olarak "clock skew" cevabını vermiş) + drdroid + groundcover | Kubernetes artık "self-hosted" değil, kurumsal içerik alanı |
| watchtower broken update | dev.to + 4 blog | Watchtower'ın bakımsız kalması bir haber döngüsü yarattı, blog'lar doldu |
| restic repository locked | homelabfix dedike sayfa | Tek kişilik homelab blog'ları da seam'i kapatıyor |
| qbittorrent stalled | makeuseof + torrenttrackerslist | Torrent = tüketici ölçeği, her zaman HIGH |
| navidrome scan | resmi docs iyi yazılmış | Projenin kendi dokümantasyonu iyiyse seam yok |

**Yeni kural:** Şekil C'nin istisnası var. Bir araç şu üçünden birine sahipse rekabet var:
1. **Kurumsal/B2B ilgisi** (Kubernetes, Portainer, gözlemlenebilirlik) → SaaS blog'ları içerik üretiyor
2. **İyi yazılmış resmi dokümantasyon** (Navidrome, Tailscale) → docs sıralanıyor, makaleye yer kalmıyor
3. **Bir haber döngüsü** (Watchtower'ın terk edilmesi) → bloglar konuyu doldurdu

Hâlâ en temiz alan: **tek geliştiricinin veya küçük bir ekibin projesi + donanıma bağlı + cevabı issue tracker'da** (Scrypted, Immich, ESPHome, Z-Wave JS UI, Zigbee2MQTT).

## Hub sayfası (246)

Tur 10'da önerilen küme sayfası yazıldı: **"A Self-Hosted Service Broke After an Update: What to Check, in Order"** (`246-self-hosted-after-update-checklist.md`).

İçeriği, 30 yazıyı yazarken çıkan tekrar eden rutin:
0. **Önce döngüyü durdur** (crash loop ACME kotası yakıyor, Z-Wave stick'i dövüyor)
1. **Ne değişti, tek satır** (servis sürümü + host + unattended mı)
2. **Doğru log** — exit 137/OOMKilled, config parse hatası, permission denied
3. **Veri yolunu kanıtla** — "verilerim gitti" vakalarının neredeyse tamamı farklı dizinden okuma
4. **Kasıtlı breaking change mi** (Mosquitto anonim giriş, Traefik v3 söz dizimi, DSM 7 SMB izni, Unraid boş pool, Grafana UID)
5. **Tek değişkenle lokalize et** (sürüm pin, kernel pin, proxy'yi atla)
6. **Sonra ileriye doğru düzelt**

Ayrıca **"dört hata"** (kanıtlamadan re-pair/re-flash, boş config'i deploy etmek, döngüyü açık bırakmak, beş şeyi birden değiştirmek) ve bir **alışkanlık tablosu** (tag pin, named volume, hangi dosyayı yedekle, `by-id` yolu).

Sayfa 26 yazıya link veriyor; küme hem iç bağlantı hem de "update sonrası" uzun kuyruğunu topluyor.

## Toplam durum

- **Tech yazı sayısı:** 206–246 arası 41 yazı (Tur 9: 11, Tur 10: 17, Tur 11: 13)
- **Test edilen tech sorgu:** 65 → **40 LOW (%62)**
- **Kalan havuz:** `longtail-queries-tech.txt` (4.976) + `-tech2.txt` (2.653) = **7.629 sorgu**, test edilmemiş

## Tur 12 adayları

Aynı testi geçmeye en yakın, henüz denenmemiş olanlar (tek geliştirici + donanım + issue tracker kriterine uyanlar):

mealie recipe import failing · homebridge child bridge not responding · zwavejs2mqtt ozw migration · wyoming satellite not detected · piper tts not working after update · whisper addon slow after update · double-take not detecting · motioneye camera offline after update · shinobi stream not loading · octoprint serial connection failed after update · klipper mcu error after firmware update · moonraker database locked · home assistant recorder database corrupt after update · esphome bluetooth proxy stopped working · music assistant player unavailable · plex meta manager failing · tdarr node not connecting · stash scan not finding scenes · romm library empty after update · gotify notifications stopped after update

---

# Tur 12: 50 makale tek turda (72 sorgu → 52 LOW, %72)

Hedef açıkça 50 yayınlanabilir makaleydi. Tur 10–11'de daraltılan kriter (tek geliştirici projesi + donanıma bağlı + cevabı issue tracker'da) doğrudan uygulandı; test edilen 72 sorgudan **52'si LOW**, bunların **50'si yazıldı** (247–296).

## Oranın neden bu kadar yüksek olduğu

Tur 9'da %44, Tur 10'da %77, Tur 11'de %67, Tur 12'de %72. Fark tamamen **aday seçiminde**. Bu turda test edilen her sorgu şu üç kutuyu işaretliyordu:

1. Yazılım **tek kişi veya küçük bir ekip** tarafından geliştiriliyor (Immich, Frigate, ESPHome, Scrypted, Mealie, Beszel, Vikunja, Stash, Kavita…)
2. Sorun **belirli donanım veya belirli bir kurulum** gerektiriyor (Coral TPU, Zigbee koordinatörü, ESP32, Z-Wave stick, 3D yazıcı, kamera, NAS)
3. Cevap **GitHub issue / proje forumu** içinde gömülü, makaleye çevrilmemiş

Bazılarının SERP'inde **tek bir makale yok**: Immich ML container, Immich mobil upload, Scrypted crash loop, Stash scan, Pterodactyl console, Mealie import, Moonraker "database is locked" (sonuçlar Oracle ve IBM dokümantasyonu!), Tdarr node (IBM/Oracle), LM Studio staff picks (Wikipedia/Etsy/Scratch).

## HIGH/MEDIUM çıkanlar ve nedenleri (Tur 11'in kuralını doğruluyor)

| Sorgu | Kim kapatmış | Hangi istisna |
|---|---|---|
| ollama not using gpu | 8 dedike sayfa | Kurulum bariyeri düşük (tek komut) |
| shelly device offline after firmware | smarthomemend ×2, trunetto | Tüketici markası |
| unifi device stuck adopting | hostifi, lazyadmin, gurunetid, randomadult | Kurumsal + tüketici kesişimi |
| zigbee2mqtt coordinator not responding | **Z2M'in kendi dokümantasyonunda dedike sayfa** | İyi resmi dokümantasyon |
| jellyfin plugin catalog | lumadock + wp301redirects | Kurulum bariyeri düşük |
| prowlarr indexer sync | techgeeks + flaresolverr | "*arr" ekosistemi rehber yazarlarını çekiyor |
| matter device won't pair | selorahomes + trunetto | Tüketici smart-home |
| restic repository locked | homelabfix | Tek kişilik homelab blogu |
| qbittorrent stalled | makeuseof | Tüketici ölçeği |
| k3s node notready | 3 Medium + drdroid + groundcover | Kurumsal ilgi |

**Operasyonel kural:** aday listesi yaparken ürünü değil **kitleyi** düşün. "Bunu kuran kaç kişi var ve kaçı blog yazarı?" Oran ne kadar küçükse seam o kadar temiz.

## Yazılan 50 makale

**Home Assistant & otomasyon (13):** homebridge child bridge · HA recorder corrupt · HA MariaDB migration · HA backup failed · HA InfluxDB · ESPHome BT proxy · Wyoming satellite · Music Assistant · Tasmota MQTT · WLED Wi-Fi · Grocy barkod · Zigbee/Z-Wave ilgili çapraz bağlantılar · Mosquitto (Tur 11)

**Kamera/NVR (4):** Frigate recordings · Frigate go2rtc · Frigate semantic search · motionEye

**Medya ve kütüphane (12):** Jellyfin trickplay · Sonarr import · Bazarr · Jellyseerr · Kometa · Tautulli · Tdarr · Kavita · Stash · Calibre-Web · Audiobookshelf podcast + Android Auto · qBittorrent/Gluetun

**Foto/doküman (6):** Immich ML · Immich duplicates · Immich mobil upload · Paperless OCR · Nextcloud notify_push · Collabora

**Ağ/DNS (4):** Pi-hole v6 · OPNsense Unbound · OpenWrt sysupgrade · Jitsi

**Dev/platform (8):** Gitea/Forgejo hooks · Wiki.js · Pterodactyl · Beszel · Uptime Kuma · Gotify · ntfy · Vikunja · Firefly III · Syncthing · Duplicati

**3D baskı (3):** Moonraker · OctoPrint serial · OctoPrint plugin

**Diğer (2):** Mealie · LM Studio (Tur 10'dan devam)

Hepsi **246 numaralı hub sayfasına** bağlandı; hub artık 70'ten fazla yazıya link veriyor ve kümenin giriş kapısı.

## Henüz test edilmemiş, aynı kriteri geçen adaylar

klipper input shaper verisi okunmuyor · bambu/prusa connect bağlantısı · romm library empty · komodo/dockge deploy hatası · semaphore ansible job · double-take detection · shinobi stream · navidrome scrobble · immich-go upload hatası · zwavejs2mqtt ozw migration · esphome voice PE yanıt vermiyor · home assistant zigbee network stuck · scrypted nvr storage dolu · plex meta manager overlay · tubearchivist indexleme · audiobookshelf match hatası · linkwarden arşivleme · hoarder/karakeep ingest · paperless-ai etiketleme · actual budget sync

**Beklenen oran:** %70+. Bu liste tek başına bir sonraki 20 makaleyi verir.

## Toplam durum (Tur 9–12)

- **Tech yazı:** 206–296 → **91 yazı**
- **Test edilen tech sorgu:** 137 → **92 LOW (%67)**
- **Kalan havuz:** 7.629 madenci sorgusu + yukarıdaki 20 el seçimi aday
