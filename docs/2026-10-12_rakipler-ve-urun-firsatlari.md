# Umap için rakipler, çözülecek sorunlar ve niş ürün fikirleri

İnceleme tarihi: **12 Ekim 2026**. Bu belge [mimari araştırmayı](2026-10-12_umap-arastirma-raporu.md) tamamlar. Rakip özellikleri resmi ürün sayfaları ve proje depolarından incelendi; ürünler kurularak karşılaştırmalı test yapılmadı. Aşağıdaki öncelikler ürün önerisidir; müşteri talebi veya pazar büyüklüğü ölçümü değildir.

## Benim ürün tercihim

Projeyi **tasarımcılar ve geliştiriciler için, yerel veriden düzenlenebilir ve tekrar üretilebilir harita çıktıları hazırlayan bir kütüphane** olarak konumlandırırdım. Python, CLI ve MCP aynı üretim motoruna bağlanır. İlk kullanıcı grubunda mimarlık/tasarım stüdyolarını, ilk somut işte farklı alanlardan tutarlı sunum haritaları üretmeyi hedeflerdim.

Güzel hazır temalar başlangıç deneyimini sağlar. Uzun vadeli ürün değeri; geometri doğruluğu, kaliteli tipografi, üretim öncesi kontrol, düzenlenebilir çıktı ve revizyonların hızlı olmasıdır. MCP bu iş akışına erişimi kolaylaştırır. Tek başına MCP desteği farklılaşma sayılmaz: Mapbox'ın resmi sunucusu ve topluluk QGIS MCP projeleri zaten var. [Mapbox MCP](https://github.com/mapbox/mcp-server), [QGIS MCP](https://github.com/nkarasiak/qgis-mcp)

## Rakip ve alternatif haritası

Tablodaki son sütun kendi değerlendirmemdir. Bir özelliğin README'de görünmemesi o üründe kesinlikle bulunmadığı anlamına gelmez. Kütüphane, masaüstü GIS ve baskı mağazası aynı kullanıcı görevinde alternatif olabilir; aynı ürün kategorisi değildir.

| Ürün | İlişki | Kaynakta görülen özellikler | Bizim için anlamı |
|---|---|---|---|
| [Prettymapp](https://github.com/chrieke/prettymapp) | En yakın Python/web alternatifi | Prettymaps yeniden yazımı; Python paketi ve Streamlit; sade stil yapılandırması; yerel OSM XML | Basit başlangıç deneyimi şart. Hız hedefini ölçülmüş üstünlük kabul etmiyoruz. |
| [MapToPoster](https://github.com/originalankur/maptoposter) | Doğrudan poster üreticisi | Python komutu, şehir/koordinat seçimi, temalar, boyutlar, çok dilli başlık/font seçenekleri | Tema sayısı ve şehir posteri üretimi tek başına yeterli farklılaşma sağlamaz. |
| [Maposter](https://github.com/mossepoch/maposter) | MapToPoster ailesindeki web uygulaması | MapToPoster üzerine Next.js/FastAPI arayüzü ve Docker dağıtımı | Bağımsız yeni motor gibi sayılmamalı; arayüz eklemek kolayca tekrar edilebilir. |
| [MapToPoster JS](https://github.com/dimartarmizi/map-to-poster) | Tarayıcı tabanlı poster alternatifi | Leaflet/MapLibre, işaretçiler, rotalar, tipografi, çerçeveler ve yüksek çözünürlüklü PNG | Etkileşimli tasarım deneyimi bir rekabet ölçütü. Tarayıcıda çizim, tam çevrimdışı çalışma anlamına gelmiyor. |
| [Mapiful](https://www.mapiful.com/editor/) | Son kullanıcı/baskı ürünü | Konum, yazı, renk ve boyutla kişiselleştirilen StreetMap posterleri | Satın alınan değer kişisel anlam ve bitmiş üründür; SDK kullanımından farklı bir görev. |
| [MapTiler Map Designer](https://docs.maptiler.com/guides/map-design/maps-and-styles-basics/) | Harita tasarım platformu | Palet/font, katmanlar, filtreler, veri kaynakları, dil ve harita görünümü ayarları | Stil editörü tek başına yeni kategori değil; bizim odak fiziksel çıktı ve kendi veri hattı olabilir. |
| [Maputnik](https://github.com/maplibre/maputnik/wiki/Design-a-Map-Style) | Açık kaynak stil editörü | Katman düzenleme ve GL stil JSON'u dışa aktarma | Stil ekosistemiyle uyumluluk değerli; bütün stil standardını ilk sürümde yeniden uygulamak pahalı. |
| [QGIS Print Layout / Atlas](https://docs.qgis.org/3.44/en/docs/user_manual/print_layout/index.html) | Güçlü masaüstü alternatifi | Sayfa düzeni, harita serileri, resim/PDF/SVG çıktısı | Toplu üretim ve vektör çıktı mevcut. Bizim önerimiz belirli işi daha az kurulum ve daha dar API ile sunmak. |
| [Felt](https://felt.com/blog/map-backgrounds-and-styling-controls) | Ekipler için web GIS | Kendi taban haritası/verisi, stil ve işbirliği; PNG/PDF aktarımı belgelenmiş | Genel ekip GIS'i geniş bir kapsam. Kaynak özellik duyurusu 2022 tarihli; güncel plan/ücret uygunluğu ayrıca incelenmedi. |
| [Mapbox MCP Server](https://github.com/mapbox/mcp-server) | Doğrudan MCP karşılaştırması | Konum/rota araçları, interaktif harita ve statik görsel; ayrıca çevrimdışı geometri işlemleri | Farkımız kendi verimizle sanat/baskı üretimi ve denetlenebilir düzenleme sözleşmesi olmalı. |
| [QGIS MCP](https://github.com/nkarasiak/qgis-mcp) | Topluluk MCP alternatifi | QGIS katman/stil/öğe düzenleme, render, layout ve atlas araçları | MCP ile düzenleme de tek başına benzersiz değil; daha dar ve taşınabilir iş akışı sınanmalı. |

MapToPoster JS belgesi geocoding, rota, tile ve font hizmetlerini de listeliyor. Bu nedenle istemci tarafı çizimi "hiçbir veri dışarı gitmez" vaadiyle eşitlememek gerekir. Bizim offline profilimizde dış istek bulunmadığını ağ kapalı testle kanıtlamalıyız. [MapToPoster JS kaynak açıklaması](https://raw.githubusercontent.com/dimartarmizi/map-to-poster/main/README.md)

## Benim önce çözeceğim sorunlar

| Öncelik | Kullanıcının sorunu | Ekleyeceğim çözüm | Başarıyı nasıl ölçerim? |
|---|---|---|---|
| P0 | Güzel görünen haritada eksik deniz, kapanmış poligon deliği veya yanlış yol sırası var | Veri/geometri kontrolü; bridge/tunnel/layer kuralları; kıyı fixture'ları; kısmi sonuç uyarıları | Bilinen örneklerde geometri kaybı ve yanlış çizim sırasının yakalanması |
| P0 | Çıktıyı Illustrator/Inkscape'te düzeltmek zor | Anlamlı SVG grupları, kararlı öğe kimlikleri, ayrı metin/çizgi katmanları | Yol rengi veya başlık, diğer katmanları bozmadan değiştirilebiliyor mu? |
| P0 | Renk değiştirince tekrar indirme ve uzun bekleme gerekiyor | Veri/sahne/render önbelleklerinin ayrılması | Aynı veriden palet değişiminde yeni ağ isteği olmaması; süreyi ayrı ölçmek |
| P0 | Baskıda ince çizgiler kayboluyor, yazılar taşıyor | mm/pt birimleri, güvenli kenar boşluğu, font/taşma/çizgi kontrolü | Hazırlanmış hatalı örneklerin üretimden önce işaretlenmesi |
| P0 | Başkasının makinesinde görünüm değişiyor | Veri ve font snapshot'ı, sürümlü tarif ve manifesto | Sabit ortamda yeniden üretim; diğer ortamda belgelenmiş görsel tolerans |
| P1 | Farklı bölgeler aynı şablonda tutarsız duruyor | Ölçek, detay seviyesi, başlık ve lejant kuralları | Çoklu alan serisinin aynı ölçü ve görsel kurala uyması |
| P1 | Küçük bir istek bütün haritayı değiştiriyor | Hedefli, sürümlü düzenleme ve geri alma | İstenen alan dışındaki stil/sahne özelliklerinin değişmemesi |

"Baskı kontrolü" başlangıçta tanımlı bir RGB çıktı profilinin kontrolüdür. Bütün matbaa süreçleri için CMYK/PDF-X uygunluğu iddiası değildir. Minimum çizgi genişliği gibi eşikler çıktı profiline bağlı olmalı.

Tipografi özel bir iş paketi olurdu: Türkçe karakterler, font bulunamaması, metin genişliği, sabit başlık alanı ve basit etiket çakışmaları. Genel çok dilli etiket yerleşimini bir anda çözmek yerine desteklenen diller/fontlar örneklerle sınanır.

## MCP'yi hangi kullanıcı deneyimi için eklerdim?

Örnek hedef konuşma:

> Kadıköy'ü A3 yatay çiz. Denizi açık bırak, ana yolları belirginleştir. Seçtiğim beş mekânı numaralandır. Aynı haritanın Türkçe ve İngilizce sürümünü ver. Sonra yalnız yol rengini değiştir.

Bu deneyimin altında **incelenebilir bir harita tarifi** bulunmalı. Önerilen araç akışı: `inspect_map → propose_patch → preview_map → apply_patch → export_map`. Bunlar taslak ürün araçlarıdır, standart MCP araçları veya uygulanmış API değildir. Salt önizleme adımı, istemcinin her küçük değişiklik için ayrı kullanıcı onayı istemesini gerektirmez; kullanıcının verdiği kapsam içinde çalışma devam edebilir.

Her revizyon; hangi katman/özelliğin değiştiğini, neyin sabit kaldığını ve yeni çıktı kimliğini döndürür. Kaynak veriden geometri üretimi deterministik kalır; model sadece doğrulanan parametreleri ve filtreleri seçer. Kullanıcı bir yol adını yanlış söylerse model hayali yol üretmez; eşleşme veya adaylar döner.

Mapbox zaten interaktif ve statik harita araçları, QGIS MCP ise düzenleme ve checkpoint işlevleri belgeliyor. Dolayısıyla savunulabilir ürün hipotezi, **dar bir tasarım işinde doğru sonuç, tutarlı çıktı ve daha az düzeltme süresi** olur. "MCP'li ilk harita aracı" iddiası kullanılmamalı. [Mapbox araçları](https://github.com/mapbox/mcp-server), [QGIS MCP araçları](https://github.com/nkarasiak/qgis-mcp)

## Niş fikirler

Aşağıdaki sıralama benim mühendislik ve ürün değerlendirmemdir. Talep, ödeme isteği ve rakiplere üstünlük henüz doğrulanmadı.

### 1. Mimarlık ve tasarım stüdyoları için kent atlası

Kullanıcı tek alan için dolu-boş bina haritası, yol hiyerarşisi, yeşil alan ve su şeması ister. Aynı işi birkaç mahalle veya proje alanında, aynı ölçekte tekrarlayabilir.

İlk paket: bir yerel veri kümesinden dört görünüm; 1:5000 gibi açık ölçek; katmanlı SVG/PDF; tutarlı lejant; başlık alanı ve kaynak kaydı. Eksik OSM binası "orada yapı yok" sonucu gibi gösterilmemeli; veri kapsamı ve tarihi açık olmalı.

Benim ilk seçimim bu olurdu: geometri, stil ve vektör çıktı çekirdeğimizle doğrudan örtüşüyor. QGIS Atlas zaten bu tür üretim için güçlü bir alternatif; hipotezimiz hazır tasarım kuralları ve Python/MCP iş akışıyla kurulum/revizyon süresini azaltmak. [QGIS Layout/Atlas](https://docs.qgis.org/3.44/en/docs/user_manual/print_layout/index.html)

İlk doğrulama: üç mimar/tasarımcıya aynı veri ve brief ile dört görünümlü bir sayfa hazırlatmak; mevcut yöntemle ve prototiple ilk kullanılabilir çıktı süresini, elle düzeltme sayısını, tekrar kullanım isteğini karşılaştırmak. Sayılar pilot tasarımıdır, yapılmış test değildir.

### 2. Butik oteller ve yerel işletmeler için semt rehberi

Otel çevresindeki seçilmiş mekânları marka renkleriyle gösteren A5 kart, oda posteri ve dijital görsel aynı tariften üretilir. Türkçe/İngilizce metinler ve numaralı mekân listesi desteklenir.

Farklılaşma hipotezi; müşterinin doğruladığı noktalar, marka şablonu, çoklu dil ve aynı veriden farklı formatlar. İlk sürüm rota önermeden seçilmiş noktaları gösterebilir. "15 dakika yürüyüş" eklenecekse gerçek yol ağıyla hesaplanmalı; kuş uçuşu çember bu adla sunulmamalı.

İlk doğrulama: iki işletmeden kendi seçtikleri noktaları alarak gerçek baskı örneği hazırlamak; veri düzeltme ve yeniden baskı ihtiyacını görmek. Ticari çekiciliği varsaymak yerine tekrar sipariş/revizyon isteği aranır.

### 3. Lazer kesim ve plotter için üretim dosyaları

Ürün çıktısı renkli posterin yanında fiziksel üretime uygun SVG olur: kapalı konturlar, yinelenen çizgi temizliği, minimum parça genişliği, kopacak adaların tespiti, malzemeye göre kesim payı ve montaj işaretleri.

Bu fikir boş bir alan değil. Laser Slicer, arazi ve OSM öğelerinden katmanlı SVG ve 3D önizleme ürettiğini belgeliyor. Bizim test edilecek odağımız şehir sokak deseninde üretim öncesi kontrol ve kullanıcı tarafından onaylanan düzeltmeler olurdu. [Laser Slicer](https://github.com/borsic77/laser_slicer)

İlk doğrulama: bir atölyeyle üç küçük örneği gerçekten üretmek; kopan parçaları, elle dosya temizleme süresini ve çizimden üretime geçişi ölçmek. Kesim payı/makine/material kalibrasyonu olmadan "her makinede hazır" sözü verilmemeli.

### 4. Spor kulüpleri için toplu rota hatıraları

Kişisel veya etkinlik GPX'i; katılımcı adı, tarih ve kullanıcının sağladığı istatistiklerle poster olur. Kulüp tek şablondan çok sayıda kişiselleştirilmiş çıktı alır. Yerel işleme, başlangıç/bitiş çevresini gizleme ve tekrar üretilebilir tasarım değerli olabilir.

GPX posteri zaten mevcut: Track To Print, GPX yükleme, spor etkinliği posterleri ve dijital/basılı ürün sunuyor. Fırsat hipotezi kulüp toplu üretimi ve yerel veri işleme; GPX kabul etmek tek başına yeni özellik değil. [Track To Print](https://tracktoprint.com/en)

İlk doğrulama: bir kulüpte küçük bir seri; manuel kişiselleştirme süresi ve hatalı isim/rota oranı. Eksik GPX yükseltisini gerçek ölçüm gibi tamamlamamalı, sağlayıcıdan türetilmişse bunu belirtmeli.

### 5. Müze, okul ve kampüsler için dokunsal haritalar

Sadeleştirilmiş yol/bina geometrisi, dokuyla ayrılan alanlar, büyük yazı ve fiziksel üretim hedeflenebilir. Bu erişilebilirlik iş akışının tasarımı görme engelli kullanıcılar ve uzmanlarla birlikte yapılmalıdır.

Touch Mapper zaten OSM tabanlı dokunsal haritalar ve 3D/embosser/kabaran kâğıt çıktıları sunuyor. Bizim hipotezimiz kurumun kendi onaylı verisi, belirli kampüs dili ve tekrar kullanılabilir şablonlardır. Erişilebilirlik doğruluğu görsel güzellikle ölçülemez. [Touch Mapper](https://touch-mapper.org/en/)

Toplumsal değeri yüksek olsa da ilk sürümde seçmezdim: kullanıcı araştırması ve fiziksel kullanılabilirlik doğrulaması çekirdek poster işinden farklı uzmanlık gerektiriyor.

### 6. Zaman içindeki şehir değişimini anlatan atlas

Aynı ölçekte iki tarihli veri, ortak görsel kuralla karşılaştırılır. Müzeler, kent araştırmaları ve eğitim için bir hikâye anlatım eklentisi olabilir.

Buradaki büyük sorun doğru zaman bilgisidir. OSM kayıt değişimi bir binanın o tarihte gerçekten yapıldığını göstermez. Güvenilir tarihli/veri kaynağı belli katmanlar ve anlatım kuralları olmadan bu özelliği ürün vaadine koymazdım. Önce kullanıcı tarafından sağlanan iki açıkça tarihli veri kümesiyle karşılaştırma yapılabilir.

## Hangi özellikleri sonraya bırakırdım?

İlk doğrulama tamamlanana kadar genel amaçlı GIS analizi, dünya çapında navigasyon, 3D şehir motoru, büyük tema pazarı ve kapsamlı web editörü sonraki kapsam olurdu. Bu alanların her biri ayrı ürün sorumluluğu yaratır.

Özellikle çok sayıda tema eklemekten önce üç temanın farklı veri yoğunluklarında iyi çalışmasını isterdim. Temalar sadece paleti değiştirmekle kalmayabilir: ölçekle detay azaltma, çizgi hiyerarşisi, etiket yoğunluğu ve sayfa kompozisyonu birlikte tasarlanabilir.

## İlk prototip için somut brief

**Bir İstanbul kesiti → dört mimari görünüm → aynı veriyle A3/A4, Türkçe/İngilizce, SVG/PDF/PNG.** Bütün çıktılarda düzenlenebilir katmanlar, görünür kaynak atfı, veri/şema/font bilgisi ve taşma kontrolü bulunur. MCP üzerinden yalnız ana yolların kalınlığı değiştirilir; diğer öğelerin sabit kaldığı sahne farkıyla gösterilir.

Başarı ölçümü: ilk kullanılabilir çıktı süresi; elle düzeltilmesi gereken öğe sayısı; stil değişiminde yeni veri isteği; aynı tarifi tekrar çalıştırmanın tutarlılığı; kullanıcının yeniden kullanmak istediği iş. Hız ve maliyet hedefleri ilk ölçümden sonra konur.

## Kanıt → ürün çıkarımı → doğrulama

| Kanıt | Çıkarım | Bir sonraki doğrulama |
|---|---|---|
| Prettymapp, MapToPoster ve JS alternatifleri temel poster deneyimini belgeliyor | Hazır tema/PNG temel beklenti | Aynı brief ile prototipin çıktı kalitesini karşılaştır |
| QGIS Layout/Atlas ve QGIS MCP üretim/düzenleme işlevleri sunuyor | Vektör, toplu çıktı veya MCP tek başına benzersiz değil | Dar görevde süre ve revizyon sayısı karşılaştırması |
| Mapbox resmi MCP sunucusu mevcut | MCP pazarlama etiketi yeterli avantaj sağlamaz | Kendi verisiyle offline üretim ve kontrollü revizyon demosu |
| GPX, dokunsal ve lazer harita ürünleri mevcut | Niş seçmek rekabeti ortadan kaldırmaz | Belirli kullanıcı ve dosya üretim sorunuyla pilot |

Ek durum notu: Araştırmada Map2Model ana sayfası kapanış duyurusu gösterdi; bu nedenle aktif rakip listesine alınmadı. Duyurudan hareketle başka ürünler hakkında hukuki sonuç çıkarılmadı. [Map2Model durumu](https://map2model.com/)
