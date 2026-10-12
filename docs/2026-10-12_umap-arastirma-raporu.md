# Umap: bağımsız harita kütüphanesi ve MCP araştırması

Araştırma tarihi: **12 Ekim 2026**. Durum: **mimari öneri; çalışan ürün veya performans ölçümü değildir**.

Devam araştırması: [Rakipler, çözülecek sorunlar ve niş ürün fikirleri](2026-10-12_rakipler-ve-urun-firsatlari.md).

## Önerilen yön

Kendi veri modelimizi, geometri hazırlama hattımızı, stil dilimizi ve sahne derleyicimizi geliştirelim. İlk çizim adaptörü Matplotlib, geometri altyapısı Shapely ve pyproj olsun. Python API, terminal arayüzü (CLI) ve MCP aynı uygulama servislerini çağırsın. Prettymaps ve OSMnx çalışma zamanı bağımlılığı olmasın.

İlk geliştirme dilimi, yerel GeoJSON'dan çevrimdışı çalışan bir harita üreticisidir. İlk kullanılabilir sürüm buna özgün temalar, PNG/SVG/PDF, CLI, yerel MCP ve bir OSM veri sağlayıcısı eklemelidir. Yer adıyla arama ayrı, yapılandırılabilir bir hizmettir. Web arayüzü, uzak MCP ve 3D sonraki kapsamdır.

Bu raporda bağımsızlık, **ürünün davranışını ve sözleşmelerini bizim kodumuzun belirlemesi** anlamına gelir. GEOS, PROJ veya font rasterleştirme altyapısını sıfırdan yazma varsayımı yapılmamıştır. Python önceliği araştırma varsayımıdır; kullanıcı henüz dil/dağıtım tercihini kesinleştirmedi.

## Araştırma kapsamı ve yöntem

Altı araştırma ajanı üçer kişilik iki dalgada çalıştı. Ana oturum kritik lisans, hizmet politikası, MCP sürümü ve SDK desteği bulgularını ayrıca kontrol etti. Yalnızca proje depoları, resmi belgeler, standartlar ve resmi paket kayıtları teknik kanıt olarak kullanıldı.

| Ajan | İncelenen konu | Birleştirmeye katkı |
|---|---|---|
| Prettymaps analizi | Ürün davranışları, bağımlılıklar, alternatifler, lisans bildirimleri | Kolay kullanım ile bağımsız iç modelin ayrılması |
| OSM veri hattı | GeoJSON, PBF, Overpass, Nominatim, CRS, atıf | Çevrimdışı çekirdek ve değiştirilebilir sağlayıcılar |
| Çizim motoru | Matplotlib, Cairo, Skia, baskı, fontlar | Kendi sahne modeli ve ilk Matplotlib adaptörü |
| MCP tasarımı | Protokol, SDK, araçlar, dosya çıktıları, uzun işler | Küçük araç yüzeyi ve sürüm uyumluluğu |
| API mimarisi | Modüller, şemalar, ergonomi, paket adı | Tek çekirdek, açık veri/stil sözleşmeleri |
| Kalite ve yayın | Geometri, görsel test, kurulum, benchmark, dağıtım | Ölçülebilir kabul koşulları |

Kaynaklarda görülen davranışlar aşağıda kaynak bağlantısıyla belirtilmiştir. Mimari kararlar ve kabul koşulları bizim önerilerimizdir. `main` ve `stable` bağlantıları zamanla değişebilir; bu inceleme belirli bir kurulu bağımlılık kilidinin deneyi değildir. Hiçbir hız, bellek veya işletim sistemi uyumluluğu iddiası benchmark ile doğrulanmış sayılmamalıdır.

## Prettymaps'ten hangi ürün derslerini alıyoruz?

Prettymaps tek çağrıyla harita üretir; OSM etiketleriyle katman seçimi, katman stili, JSON presetleri ve daire/yarıçap seçenekleri sunar. Sonuç geometrilerine ve Matplotlib nesnelerine erişim sağlar. Güncel öğretici çoklu kompozisyon, yükselti gölgelendirmesi ve önemli noktalar gibi daha geniş örnekler içerir. Bizim için esas ürün değeri kolay başlangıç ve sonradan özelleştirmedir. [Prettymaps README](https://github.com/marceloprates/prettymaps), [öğretici](https://github.com/marceloprates/prettymaps/blob/main/docs/tutorial.md)

İncelenen veri ve çizim kaynakları OSMnx ile veri edinimini ve Matplotlib/vsketch ile çıktıyı birleştiriyor. Gereksinimler raster, notebook ve web araçlarını da kapsıyor. Bizim kararımız; çekirdeğin, isteğe bağlı özelliklerden ayrı tutulması ve veri sağlayıcı hatasının boş harita olarak gizlenmemesidir. [Veri alımı](https://raw.githubusercontent.com/marceloprates/prettymaps/main/prettymaps/fetch.py), [çizim kodu](https://raw.githubusercontent.com/marceloprates/prettymaps/main/prettymaps/draw.py), [bağımlılıklar](https://raw.githubusercontent.com/marceloprates/prettymaps/main/requirements.txt)

| Referans | Gözlenen yaklaşım | Bizim tasarım kararımız |
|---|---|---|
| Prettymaps | Tek çağrı, katmanlar, presetler | Basit üst API; gelişmiş aşamalar ayrıca erişilebilir |
| Prettymapp | Alan, OSM geometrisi ve çizimin ayrılması; yerel OSM XML girişi | Veri edinimini render'dan ayır; ağsız girdiyi baştan destekle |
| Mapnik | Veri kaynağı, özellik, katman ve harita nesneleri | Kaynak ve çizim adaptörü sınırlarını açık tut |

Prettymapp'in hız hedefleri bu araştırmada karşılaştırmalı olarak ölçülmedi. Mapnik genel kartografik motor örneğidir; aynı poster deneyiminin birebir karşılığı değildir. [Prettymapp](https://raw.githubusercontent.com/chrieke/prettymapp/main/README.md), [Mapnik](https://github.com/mapnik/mapnik)

### Kaynak kodu ve veri lisansı

Prettymaps'in LICENSE dosyası ve README'si AGPL-3.0 yönünde; incelenen `setup.py` ise MIT metadata'sı taşıyor. Bu tutarsızlık projeyi MIT kabul ederek kod almak için dayanak değildir. Önerimiz kaynak, preset ve görselleri taşımadan kendi gereksinimlerimizden uygulama geliştirmektir. [LICENSE](https://raw.githubusercontent.com/marceloprates/prettymaps/main/LICENSE), [setup.py](https://github.com/marceloprates/prettymaps/blob/main/setup.py)

Kendi yazılım lisansı, bağımlılık lisansları, font lisansları ve harita verisi lisansı ayrı kaydedilmeli. OSM atfı çıktı üzerinde okunabilir olmalı; veri kaynağı ve lisans bilgisi manifestoya da girmeli. ODbL kapsamındaki veritabanı dağıtımı ile bitmiş harita dağıtımının koşulları aynı kabul edilmemeli. Bunlar somut dağıtım biçimiyle değerlendirilmesi gereken ürün gereksinimleridir; bu rapor hukuki uygunluk garantisi vermez. [OSMF atıf rehberi](https://osmfoundation.org/wiki/Attribution_Guidelines), [lisans açıklamaları](https://osmfoundation.org/wiki/Licence_and_Legal_FAQ)

## Önerilen mimari

```mermaid
flowchart LR
    python["Python API"] --> service["Ortak uygulama servisleri"]
    cli["CLI: terminal komutları"] --> service
    mcp["Yerel MCP"] --> service
    service --> source["Veri sağlayıcıları"]
    local["GeoJSON / PBF"] --> source
    online["Yapılandırılmış OSM hizmeti"] --> source
    source --> dataset["Doğrulanmış Dataset"]
    dataset --> geometry["Projeksiyon ve geometri"]
    geometry --> scene["Sahne derleyicisi"]
    style["Özgün stil şeması"] --> scene
    scene --> renderer["Çizim adaptörü"]
    renderer --> result["PNG / SVG / PDF ve manifesto"]
```

Şema hedef mimariyi gösterir. PBF ve çevrimiçi sağlayıcılar aşamalı eklenir. MCP bir harita motoru değildir; ortak servisleri araç olarak sunar. Kütüphane MCP kurulmadan, MCP ise harita oluşturmak için ayrı bir model API çağrısı yapmadan çalışabilmelidir. Doğal dili araç çağrısına çeviren model istemci tarafındadır.

| Modül | Sorumluluk | Dışarı sızmaması gereken ayrıntı |
|---|---|---|
| `specs` | MapSpec, SourceSpec, StyleSpec, OutputSpec ve doğrulama | Matplotlib argümanları |
| `sources` | GeoJSON, PBF, Overpass ve sağlayıcı metadata'sı | Sağlayıcıya özgü yanıt biçimleri |
| `geometry` | CRS, geçerlilik, kesme, buffer, sadeleştirme | Ağ istekleri |
| `styles` | Filtre, renk, katman sırası, fiziksel birimler | Python ifadesi çalıştırma |
| `scene` | Çizilecek path, metin, clipping ve sayfa düzeni | MCP nesneleri |
| `renderers` | Sahneyi PNG/SVG/PDF'ye aktarma | Veri indirme |
| `services` | İş akışı, cache, iş durumu ve bütçeler | CLI argüman ayrıştırma |
| `cli` / `mcp_server` | Girdiyi doğrulanmış isteğe çevirme ve sonucu sunma | İkinci bir geometri/çizim uygulaması |

İlk sürüm için mikroservis, dağıtık kuyruk veya LLM framework'ü gerekmiyor. Dosya tabanlı içerik deposu ve SQLite iş/cache metadata'sı yeterli başlangıçtır. Başlangıçta sınırlı tek render işçisi; ihtiyaç ölçülürse süreç tabanlı paralellik önerilir.

### Kendi kodumuz ile altyapı bağımlılıklarının sınırı

| Bizim geliştireceğimiz | Kullanılması önerilen altyapı |
|---|---|
| Veri sağlayıcı arayüzü, katman sınıflandırması | OSM/GeoJSON/PBF veri standartları |
| Stil dili, kompozisyon, tema tasarımı | Renk ve dosya biçimi standartları |
| Geometri hattının sırası ve hata davranışı | Shapely / GEOS işlemleri |
| CRS seçimi ve birim sözleşmesi | pyproj / PROJ dönüşümleri |
| Sahne modeli, render adaptörü | İlk sürümde Matplotlib |
| MCP araçlarının ürün davranışı | Resmi MCP Python SDK |

Bu sınırın kabul testi: Prettymaps ve OSMnx yüklü olmayan temiz ortamda yerel veriyle harita üretilebilmesi. Kaynak dosyalarının bağımsız geliştirilmesi ayrıca sürüm geçmişinde izlenmelidir.

## Veri hattı ve çevrimdışı çalışma

### Veri kaynaklarının sırası

1. **GeoJSON:** küçük örnekler, kullanıcının kendi verisi ve ağsız testler. Dış koordinat sözleşmesi boylam/enlem; bbox sırası `west, south, east, north`. GeoJSON RFC 7946 koordinatları WGS84 temellidir; projekte metre koordinatları standart GeoJSON diye dışa aktarılmamalı. [RFC 7946](https://www.rfc-editor.org/rfc/rfc7946)
2. **PBF:** bölgesel OSM verisi ve tekrar eden üretimler. Pyosmium ile node konumları ve multipolygon ilişkileri kurulmalı; eksik referanslar raporlanmalı. Her kapalı way bina/alan değildir. [Pyosmium geometri kılavuzu](https://docs.osmcode.org/pyosmium/latest/user_manual/03-Working-with-Geometries/)
3. **Overpass:** küçük/orta yerel alanların etiket odaklı edinimi. Kendi sorgu planlayıcımız; kontrollü yeniden deneme, cache ve alan bütçesi. İlişki üyeleri eksik indirilirse hatalı geometri oluşabileceği için tamlık kontrolü şart.
4. **Yer adı çözümleme:** sağlayıcısı açıkça seçilen ayrı arayüz. Birden fazla sonuç varsa koordinat/bölge seçenekleri döndürülmeli; ilk eşleşme sessizce seçilmemeli.

Geofabrik bölgesel PBF dosyaları sunar. Tekrarlanabilirlik için `latest` bağlantısının yanında indirilmiş içeriğin hash'i ve veri zamanı gerekir. [Geofabrik indirmeleri](https://download.geofabrik.de/)

OSMnx hazır veri edinimi ve cache özellikleri nedeniyle bir karşılaştırma aracı veya ileride isteğe bağlı adaptör olabilir. Kendi API'mizin temel sözleşmesi yapılmamalı. OSMnx etiket sorgularında birleşim davranışı bulunduğu için bizim `all`/`any` filtre semantiğimiz açık tanımlanmalıdır. [OSMnx referansı](https://osmnx.readthedocs.io/en/stable/user-reference.html)

### Kamu hizmetleri tasarımı etkiliyor

Kamu Nominatim politikası uygulamanın toplam trafiğine saniyede bir istek üst sınırı, tanımlayıcı istemci bilgisi, atıf ve hizmet değiştirebilme koşulları koyuyor. Otomatik tamamlama yasak. Güncel metin ayrıca no-code/low-code/vibe-coding platformlarında genel yer arama hizmeti olarak sunulmasını kısıtlıyor ve geliştiricinin bilinçli seçimini arıyor. **Öneri: genel MCP yer arama aracını varsayılan kamu Nominatim adresine bağlamayalım.** Bu, bütün Nominatim kurulumlarına yönelik bir yasak değildir; politika belirtilen kamu hizmetine aittir. [Nominatim politikası](https://operations.osmfoundation.org/policies/nominatim/)

Overpass kamu sunucuları paylaşılan kaynaklardır. Oran/bellek/süre sınırları ve 429/504 durumları tasarıma dahil edilmelidir; belge örnekleri bize ayrılmış hizmet kotası değildir. Sağlayıcı başına kuyruk, sınırlandırılmış geri çekilme, toplam zaman bütçesi ve kullanıcıya görünen hata durumu önerilir. [Overpass kaynak paylaşımı](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)

### Geometri açısından ilk günden çözülmesi gerekenler

Shapely düzlemsel çalışır ve CRS dönüşümü yapmaz. Buffer/sadeleştirme mesafeleri için uygun metrik çalışma CRS'si gerekir. pyproj dönüşümünde koordinat sırası `always_xy=True` gibi açık bir sözleşmeyle korunmalıdır. CRS atamak, koordinatları dönüştürmek değildir. [Shapely kılavuzu](https://shapely.readthedocs.io/en/stable/manual.html), [pyproj Transformer](https://pyproj4.github.io/pyproj/stable/api/transformer.html), [GeoPandas CRS açıklaması](https://geopandas.org/en/stable/docs/user_guide/projections.html)

Önerilen sıra: ön eleme → dönüşüm → doğrulama/raporlanan onarım → ölçeğe uygun sadeleştirme → katman geometrisi → son kesme. Yol ve efektler için çalışma sınırına taşma payı eklenmeli. Delikli poligonlar, açık yollar, çok parçalı geometriler ve bridge/tunnel/layer etiketleri test verisine girmeli. Tarih çizgisini aşan, kutupsal veya çok geniş alanlar ilk sürümün destek sınırında açıkça ele alınmalı.

İstanbul gibi kıyı alanlarında deniz dolgusunu ayrıca doğrulamalıyız. `natural=water` sorgusunun bütün denizi kapladığı varsayılamaz. Kıyı çizgisinden alan kurma veya ayrı su poligon kaynağı bir sağlayıcı kabiliyeti olarak tanımlanmalı; eksikse uyarı verilmelidir. Bu, prototipte gerçek kıyı veri örneğiyle doğrulanacak bir kabul konusudur.

Cache için ham veri ile normalize geometri ayrı anahtarlar kullanmalı. Geometri cache'ini renk değişince geçersiz kılmayalım. Manifestoda kaynak hash'i/zamanı, sorgu, çalışma CRS'si, stil ve şema sürümü, font hash'i, seed, renderer ve bağımlılık sürümleri bulunsun. Çevrimdışı profil gizli font, CRS grid veya harita indirmesi yapmamalı; gerekli dönüşüm gridleri ayrıca yönetilmelidir. [pyproj kurulumu](https://pyproj4.github.io/pyproj/stable/installation.html)

## Çizim motoru seçimi

| Seçenek | Güçlü yanı | Maliyet / sınır | Karar |
|---|---|---|---|
| Matplotlib | PNG, SVG ve PDF arka uçları; Python entegrasyonu | Global durum ve eşzamanlılık dikkat ister | İlk adaptör |
| Kendi SVG yazıcımız | Vektör yapısı ve dosya üzerinde doğrudan kontrol | Font, desen, clipping ve raster çıktı sorumluluğu | İkinci adaptör adayı |
| Cairo / Pycairo | Düşük seviyeli 2D çizim kontrolü | Yerel kurulum bileşenleri; gelişmiş metin için ayrı katman | Gereksinim doğarsa |
| Skia | Raster/GPU ve PDF seçenekleri | Python tarafında SVG arka ucu deneysel olarak belgeleniyor | Performans/efekt ölçümü sonrası |

Bu tablo performans sıralaması değildir. Çıktı kabiliyetleri resmi belgelerle kontrol edildi. [Matplotlib arka uçları](https://matplotlib.org/stable/users/explain/figure/backends.html), [Pycairo kurulumu](https://pycairo.readthedocs.io/en/latest/getting_started.html), [Skia canvas](https://skia-python.github.io/skia-python/tutorial/canvas.html)

Matplotlib thread-safe olarak belgelenmiyor. MCP'nin eşzamanlı çağrılarının aynı figür veya global ayarları paylaşmasına izin vermeyelim. İlk uygulamada başsız render ve tek işçi; büyüdüğünde izole süreçler kullanmak daha anlaşılır sınır oluşturur. [Matplotlib FAQ](https://matplotlib.org/stable/users/faq.html#work-with-threads)

Stil şemasında sayfa ölçüleri `mm`, çizgi ölçüleri açık `mm`/`pt`/`m` birimleriyle tanımlansın. Piksel hesabı `mm × DPI / 25,4`; A3 300 DPI yaklaşık 3508 × 4961 pikseldir. SVG/PDF vektörleri DPI ile sınırlanmaz; içlerindeki raster öğeler ayrıca sınırlandırılır. İlk sürüm RGB poster çıktısı hedefler; CMYK/PDF-X baskı sertifikasyonu ayrı kapsamdır.

Türkçe karakterleri kapsayan lisansı uygun font seçilmeli. SVG'de düzenlenebilir metin ile gliflerin yola dönüştürülmesi farklı kullanım seçenekleridir. Font ve FreeType farkları raster sonucu etkileyebilir; platformlar arası byte eşitliği vaat edilmemeli. Karmaşık yazı sistemleri ve otomatik etiket çakışması ayrı iş paketidir. [Matplotlib fontları](https://matplotlib.org/stable/users/explain/text/fonts.html), [Cairo metin sınırları](https://www.cairographics.org/manual/cairo-text.html)

## API ve kullanım taslağı

CLI, aynı kütüphaneyi terminal komutlarıyla kullanma yoludur. Python kodu yazmak istemeyen kullanıcıya ve otomasyona yarar. MCP ise harita işlevlerini yapay zekâ istemcisine açar. Üçü aynı doğrulama ve render hattını kullanmalıdır.

Aşağıdaki örnekler **tasarım taslağıdır; henüz uygulanmış API veya çalıştırılabilir komut değildir**. `umap_art` geçici import adıdır; PyPI/marka müsaitliği doğrulanmış değildir.

```python
# Hedef kullanım taslağı; henüz bir paket implementasyonu bulunmuyor.
from umap_art import MapSpec, render

spec = MapSpec.from_dict({
    "schema_version": "1",
    "source": {"type": "geojson", "path": "istanbul.geojson"},
    "extent": {"bbox": [28.94, 40.99, 29.02, 41.04]},
    "style": {"preset": "minimal"},
    "canvas": {"width_mm": 297, "height_mm": 420, "dpi": 300},
    "seed": 42
})
result = render(spec, formats=["png", "svg", "pdf"], output_dir="outputs")
```

```text
Önerilen terminal komutu:
umap-art render --spec istanbul.map.json --output-dir outputs

Önerilen yerel MCP başlatma komutu:
umap-art mcp --transport stdio
```

Kolay `render()` çağrısının altında veri hazırlama, sahne derleme ve çıktı alma ayrı Python fonksiyonları olarak erişilebilir olmalı. `MapResult`; dosyalar, MIME türü, boyut/hash, atıf, CRS, veri zamanı, katman sayıları ve uyarıları döndürmeli. `EMPTY_DATA`, `PARTIAL_DATA`, `PROVIDER_RATE_LIMIT`, `INVALID_GEOMETRY`, `BUDGET_EXCEEDED` ve `CANCELLED` ayrı sonuçlar olmalı; teknik arıza boş veri diye gizlenmemeli.

Stil filtresi bildirimsel ve sürümlü olmalı: örneğin `all`, `any`, `eq`, `in`, `has`. Rastgele Python kodu, `eval` veya çalıştırılabilir tema dosyaları kabul edilmemeli. OSM etiketleri ve kullanıcı başlıkları veri olarak ele alınıp SVG/metin çıktısına uygun kaçış uygulanmalı.

Dış istek sınırında Pydantic kullanıp JSON Schema'yı aynı modellerden üretmek önerilir. Büyük geometri dizileri bu doğrulama katmanından tekrar tekrar geçirilmemeli; iç model sade kalmalı. Strict doğrulamanın Python ve JSON girdileri arasındaki farkları test edilmelidir. Şema sürümü ile paket sürümü ayrı tutulmalı. [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/), [strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)

### Adlandırma ve paketleme

Depo adı Umap kalabilir; ancak `import umap` adı zaten umap-learn tarafından kullanılıyor. Ayrıca ayrı bir uMap harita projesi var. Bu yüzden dağıtım ve import adı geliştirmeye başlamadan ayrıştırılmalı. `umap-art` / `umap_art` burada yalnız çalışma örneğidir; kullanılabilir veya tescil açısından uygun olduğu iddia edilmiyor. [umap-learn](https://pypi.org/project/umap-learn/), [uMap](https://github.com/umap-project/umap), [paket adı normalizasyonu](https://packaging.python.org/en/latest/specifications/name-normalization/)

Tek depo ve tek Python dağıtımıyla başlayalım. Önerilen çekirdek bağımlılıkları Shapely, pyproj ve dış şema için Pydantic; `render` eki Matplotlib, `pbf` eki Pyosmium, `mcp` eki resmi SDK eklesin. CLI başlangıçta standart `argparse` ile aynı pakette bulunabilir; komutun ihtiyaç duyduğu eksik eki açıkça söylemeli. Yeni kullanıcı belgelerinde çizim ekini içeren tek kurulum gösterilmeli. Bu henüz yayımlanmış kurulum komutu değildir.

GeoPandas, OSMnx, rasterio, Streamlit, 3D ve GPU araçları başlangıç çekirdeğine eklenmesin. `pyproject.toml` içindeki `project.scripts` ve `optional-dependencies` bu ayrımı destekler. Desteklenen Python sürümleri, seçilen native bağımlılıkların wheel matrisi doğrulanınca ilan edilmeli. [Paketleme belirtimi](https://packaging.python.org/en/latest/specifications/pyproject-toml/)

## MCP tasarımı

12 Ekim 2026 kontrolünde resmi PyPI kaydı **mcp 2.3.0**, yayın tarihi **2 Ekim 2026** ve Python gereksinimi **>=3.10** gösteriyor. Resmi örnek `MCPServer` kullanıyor. Bu araştırma için v2'nin yayımlanmış olduğu doğrulandı; uygulama aşamasında seçilen sürümle test edilmeli, eski FastMCP örnekleriyle karıştırılmamalı. [MCP Python SDK paketi](https://pypi.org/project/mcp/)

2026-07-28 protokolü istek başına yetenek/protokol metadata'sı kullanıyor. Eski bağlantı başlangıcı ve oturum varsayımları güncel protokol diye yeniden yazılmamalı. Yerel dağıtım için stdio, uzak dağıtım için Streamable HTTP öneriliyor; SDK uyumluluk katmanı seçilen istemciyle ayrıca sınanmalı. [Güncel şartname](https://modelcontextprotocol.io/specification/2026-07-28), [taşıma sözleşmesi](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)

### Küçük ve açık araç yüzeyi

Aşağıdaki adlar proje taslağıdır; MCP standardının zorunlu araçları değildir.

| Araç | Görev | İlk sürüm davranışı |
|---|---|---|
| `list_styles` | Temaları ve değiştirilebilir alanları listeler | Hazır ve özgün temalar |
| `validate_map` | MapSpec ve kaynak/boyut bütçelerini denetler | Alan bazlı hata; çizim yapmaz |
| `render_map` | Haritayı üretir | Sonuç veya uygulamaya ait iş kimliği |
| `export_map` | Hazır sahneden başka çıktı üretir | Yeniden indirme yapmaz |
| `get_job` | İş aşaması, hata ve sonucu getirir | Sınırlı süre saklanan iş kaydı |
| `cancel_job` | Kuyrukta/çalışan işi iptal etmeyi ister | Kooperatif iptal ve açık durum |
| `get_artifact` | Çıktı metadata'sı veya küçük önizleme sunar | Kayıtlı artifact kimliği kullanır |

`search_places`, uygun geocoder yapılandırıldığında açılan ek araçtır. GeoJSON/bbox/koordinat kullanımı buna ihtiyaç duymaz. Birden fazla konum adayı kullanıcıya/istemciye sunulur. Genel kamu Nominatim adresi varsayılan atanmaz.

Resources; stil kataloğu, şema, manifesto ve çıktı erişimi için kullanılabilir. Prompts, ileride bir şehir posteri hazırlama rehberi olabilir; çekirdek özellik değildir. MCP Apps tabanlı etkileşimli önizleme ayrı bir gelecek kapsamıdır ve istemci desteğine bağlıdır.

### Sonuç ve uzun iş sözleşmesi

Her araç için girdi/çıktı şeması tanımlanmalı. `structuredContent`; `status`, `job_id`, `artifacts`, `warnings`, `attribution` ve `manifest` gibi durumla uyumlu alanlar taşımalı. Artifact kaydı MIME türü, byte boyutu, hash ve URI içermeli. Küçük PNG önizleme image içerik bloğuyla; büyük dosyalar kaynak bağlantısıyla sunulabilir. Sunucuya ait yerel yol, uzak istemci için indirme adresi değildir. [MCP araçları ve sonuçları](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)

Önerilen URI `umap-art://artifacts/{id}` olabilir. Sunucu bu kaynağın okunmasını gerçekten uygulamalı; istemci kaynak bağlantısı tüketemiyorsa `get_artifact` üzerinden metadata/önizleme sağlanmalı. Uzak dağıtımda indirme gerekiyorsa kullanıcıya bağlı HTTPS erişimi tasarlanmalı. Raster önizleme küçük tutulmalı, çok megabaytlı PDF/base64 her araç yanıtına doldurulmamalı.

Kısa işte normal araç yanıtı ve desteklenirse ilerleme bildirimi yeterlidir. Toplam süre bilinmiyorsa uydurma yüzde yerine veri edinme/geometri/çizim aşaması bildirilmeli. İstemcinin progress desteği yoksa iş yine çalışmalı. [Progress sözleşmesi](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

**Tasks uyumluluk farkı:** 2026 protokolündeki Tasks eklentisi polling ve kalıcı görev tanımlıyor. Ancak incelenen resmi SDK geçiş rehberi yeni eklentinin SDK'da henüz uygulanmadığını açıkça belirtiyor. Bu nedenle MVP, kendi `job_id/get_job/cancel_job` araçlarını kullanmalı. Bunlar standart `tasks/get` gibi tanıtılmamalı; ileride destek geldiğinde mevcut iş yöneticisine protokol adaptörü eklenebilir. [Tasks eklentisi](https://modelcontextprotocol.io/extensions/tasks/overview), [SDK geçiş rehberi](https://py.sdk.modelcontextprotocol.io/migration/#experimental-tasks-support-removed)

Yerel stdio sunucusu açık olduğu sürece sınırlı iş kuyruğu ve SQLite kayıtları yeterlidir. Sunucu yeniden başladığında yarım işler `interrupted` olarak işaretlenmeli; devam ettirme desteği uygulanmadan kalıcı yürütme vaat edilmemeli. Uzun iş başlatan kısa araç çağrısı tamamlandıktan sonra iptal `cancel_job` ile yapılır. İşçi süreç kapatma desteği ve timeout, sınırlandırılmış kaynak temizliğiyle ayrıca test edilmeli.

### Dosya, ağ ve kaynak sınırları

MCP katmanına kullanıcı girdisinden serbest URL veya sınırsız dosya yolu işletmek yerine kayıtlı kaynak/sağlayıcı kimliği verelim. Yerel kaynak ve çıktı kökleri sunucu yapılandırmasında belirlensin; çözülmüş yolun kök içinde kaldığı denetlensin. Harita alanı, piksel sayısı, geometri sayısı, indirme byte'ı, süre ve iş sayısı sınırları ölçümle belirlensin. Harici coğrafi etiketler talimat olarak yorumlanmasın.

Dosya oluşturan araç kendisini salt okuma diye tanıtmamalı. Çıktılar benzersiz kimlikle oluşturulsun, bitmeden kullanıcıya hazır gösterilmesin. Uygulama hataları kararlı kod ve düzeltilebilir açıklama taşısın; protokol/şema hataları SDK sözleşmesine uygun döndürülmeli. Başarı, boş veri, kısmi veri ve başarısızlık ayrı test edilmelidir.

Uzak MCP ayrı dağıtım profilidir: kimlik doğrulama, kullanıcıya göre artifact/iş yetkisi ve erişim sınırları gerektirir. Yerel HTTP kullanılırsa localhost bağlaması ve Origin doğrulaması gerekir. İlk stdio sürümü bu sunucu işletim yüküne ihtiyaç duymaz. [Streamable HTTP gereksinimleri](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

## İlk ürün kapsamı ve geliştirme sırası

İlk sürümün hedefi: **mahalle/şehir kesitinden, özgün temayla, kendi motorumuz üzerinden tekrar üretilebilir 2D harita**. Tam dünya çizimi, sokak etiketlerinin genel çakışma çözümü, arazi/3D, animasyon, CMYK/PDF-X, web editörü ve uzak çok kullanıcılı işletim ayrı kapsamdır.

| Aşama | Teslimat | Tamamlanma ölçütü |
|---|---|---|
| 1 — Sözleşme | Adlandırma, MapSpec/StyleSpec/Scene, birimler, hata politikası | Aynı şema bütün giriş yollarına uygulanabilir; küçük fixture seti tanımlı |
| 2 — İlk çizim | GeoJSON, projeksiyon, bina/yol/su/yeşil alan/arka plan, iki özgün tema | Ağ kapalıyken PNG/SVG/PDF; delikler, sınırlar ve atıf doğru |
| 3 — Ortak erişim | Python kolay API, CLI ve yerel MCP | Aynı girdi aynı anlamlı sahneyi üretir; gerçek stdio testi geçer |
| 4 — OSM sağlayıcısı | Öncelikle PBF/Pyosmium; isteğe göre küçük alan Overpass | Multipolygon, eksik üye, timeout, cache ve kıyı örneği doğrulanır |
| 5 — Kalite ve kurulum | Windows/Linux/macOS hedef matrisi, fontlar, çıktı limitleri | İlan edilen her ortamda wheel kurulumundan ilk çizime smoke testi |
| 6 — İlk yayın | Kullanım belgeleri, lisans/atıf kayıtları, örnekler, ölçüm raporu | Test edilen aynı paket artifact'leri yayıma hazır |

Sıralama gerekçesi: önce kendi çekirdeğinin doğruluğunu görmek, ardından veri sağlayıcı karmaşıklığını eklemek. API ajanı kullanım kolaylığı için Overpass'ı öne çıkardı; veri ajanı tekrarlı üretim ve çevrimdışı güvenilirlik için PBF'yi öne çıkardı. Sentez kararı: GeoJSON ortak başlangıç; bağımsız çalışma önceliğinde PBF önce, kurulum kolaylığı önceliğinde küçük alan Overpass önce alınabilir. Her iki sağlayıcıyı ilk çizimden önce bitirmek gerekmiyor.

Kesin hafta tahmini verilmedi. İlk iki aşamadaki ölçümler, gerçek harita örneği ve paket kurulumu sonraki kapsamı belirlemelidir. Şu an araştırma tamamlandı; bu aşamalar henüz uygulanmadı.

## Test ve performans planı

| Kontrol | Ne doğrulanacak? | Hatanın görünür sonucu |
|---|---|---|
| Geometri | Deliklerin korunması, sonlu koordinatlar, clipping, bilinen CRS kontrol noktaları, metre birimi | Küçük fixture üzerinde sayısal fark |
| Stil/sahne | Katman sırası, renk/kalınlık, sabit özellik sırası ve seed | Normalize edilmiş sahne farkı |
| Görsel | PNG toleransı; SVG boyut, öğe, clipping ve font davranışı | Beklenen/üretilen/fark görselleri |
| Çevrimdışı | GeoJSON ve hazır PBF ile ağ kapalı üretim | Gizli ağ erişiminde test başarısızlığı |
| Sağlayıcı | 429, timeout, 5xx, bozuk yanıt, eksik ilişki ve gerçek boş sonuç | Kararlı hata kodu veya kısmi sonuç uyarısı |
| MCP | Şema, sürüm anlaşması, araç listesi/çağrısı, önizleme, iptal | Gerçek istemciyle protokol/ürün hatası |
| Kurulum | Üretilmiş wheel'den CLI/MCP/ilk çıktı; Unicode ve boşluk içeren Windows yolları | Platforma özgü kurulum raporu |

pytest fixture/monkeypatch ile sağlayıcı ve ortam koşulları yalıtılabilir. Matplotlib test rehberi, mümkün olduğunda değer karşılaştırmasını tercih edip gerekli yerlerde görsel referans kullanmayı destekliyor. Kaynakta örnek bulunması bizim testlerimizin çalıştığı anlamına gelmez. [pytest monkeypatch](https://docs.pytest.org/en/stable/how-to/monkeypatch.html), [Matplotlib test rehberi](https://matplotlib.org/devdocs/devel/testing.html)

MCP için bellek içi testin yanında kurulu komutla başlayan gerçek stdio testi gerekir. Güncel 2026 ve desteklenecek eski istemci davranışları ayrı sınanmalı; her istemcinin aynı handshake veya uzantıları kullandığı varsayılmamalı. Loglar protokol akışını bozmamalı. [MCP SDK test rehberi](https://py.sdk.modelcontextprotocol.io/get-started/testing/)

Deterministik sahne, deterministik görüntü ve byte düzeyinde aynı dosya ayrı hedeflerdir. İlk hedef veri/katman/geometri eşdeğerliği; ikinci hedef sabit ortamda görsel tolerans. SVG kimlikleri ve timestamp gibi metadata normalize edilebilir. Font ve bağımlılık sürümleri manifestoya girer. Dosya formatına göre metadata davranışının değiştiği göz önünde tutulmalı. [Matplotlib savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html)

Benchmark; okuma, projeksiyon, geometri, sahne ve render sürelerini ayrı ölçmeli. Sabit küçük/orta/büyük fixture'larda nesne/vertex sayısı, sıcak/soğuk cache, tepe bellek, çıktı boyutu, donanım ve sürümler raporlanmalı. İlk ölçüm olmadan kesin saniye hedefi veya Prettymaps'ten hız üstünlüğü ilan edilmemeli. Karşılaştırma aynı veri, kapsam ve çözünürlükle yapılmalıdır.

Kendi wheel'imiz saf Python olsa bile native bağımlılıkların uygun wheel'leri bulunmalı. CI kaynak checkout'u dışında üretilen paketi temiz ortama kurmalı; ekler ayrı sınanmalı. Yayın için test edilen wheel/sdist ve PyPI Trusted Publishing önerilir; bu araştırmada herhangi bir yayın yapılmadı. [PyPA paketleme akışı](https://packaging.python.org/en/latest/flow/), [GitHub Python CI](https://docs.github.com/en/actions/tutorials/build-and-test-code/python), [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)

## Kanıt → bulgu → uygulama kararı

Bu tablo kaynak gözlemleriyle tasarım çıkarımlarını ayırır. Tarih bütün satırlar için 12 Ekim 2026; kaynak tipi resmi web belgesi veya proje kaynağıdır. Yeniden inceleme, verilen bağlantıların açılmasıyla yapılabilir; hareketli sayfaların gelecekte aynı içerikte kalması garanti değildir.

| Kanıt | Kaynak gözlemi | Bulgu / karar | Uygulama yolu |
|---|---|---|---|
| E01 | [Prettymaps README](https://github.com/marceloprates/prettymaps) ve [metadata](https://github.com/marceloprates/prettymaps/blob/main/setup.py) farklı lisans bildiriyor | Kopyalama için MIT varsayımı kullanma | Kendi API, kaynak, preset ve görsellerini geliştir |
| E02 | [Shapely](https://shapely.readthedocs.io/en/stable/manual.html) düzlemsel çalışıyor | Coğrafi derecede metre işlemi yapma | Açık projeksiyon → geometri → çıktı hattı |
| E03 | [Nominatim politikası](https://operations.osmfoundation.org/policies/nominatim/) kamu hizmetini kısıtlıyor | Genel MCP aramasında varsayılan endpoint kullanma | Sağlayıcı seçimi; koordinat/yerel veri başlangıcı |
| E04 | [Overpass](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html) paylaşılan kaynak/bütçe modeli kullanıyor | Kamu erişimi SLA değildir | Cache, kuyruk, timeout ve geri çekilme |
| E05 | [MCP PyPI](https://pypi.org/project/mcp/) v2 yayını; [migration](https://py.sdk.modelcontextprotocol.io/migration/#experimental-tasks-support-removed) Tasks eksiği | SDK sürümü ve protokol özelliği aynı şey değildir | Test edilmiş v2; uygulamaya ait job araçları |
| E06 | [Matplotlib FAQ](https://matplotlib.org/stable/users/faq.html#work-with-threads) thread güvenliği vermiyor | Aynı render durumunu paralel paylaşma | İlk tek işçi; sonra süreç izolasyonu |
| E07 | [OSMF atıf rehberi](https://osmfoundation.org/wiki/Attribution_Guidelines) çıktı atfını tanımlıyor | Atıf çıktı tasarımının parçasıdır | Görünür atıf + kaynak manifestosu |
| E08 | [umap-learn](https://pypi.org/project/umap-learn/) `umap` import adını kullanıyor | Import adı karışıklığı var | Yayından önce ayrı dağıtım/import adı |

Önerilen uçtan uca uygulama yolu: **doğrulanmış MapSpec → kaynak edinimi/cache → Dataset → projeksiyon/geometri → stil/sahne → render → atomik artifact + manifesto**. Python, CLI ve MCP yalnız giriş/çıkış biçimini değiştirir. Bu yolun başarı kanıtı, aşama 3'te aynı yerel fixture'ın üç girişten de eşdeğer sahne üretmesidir.

## Henüz karara bağlanmayan tercihler

Araştırmayı engellemeyen dört ürün kararı kaldı: paket/marka adı; bağımsızlığın genel altyapı bağımlılıklarını ne ölçüde kapsadığı; ilk kullanıcıların çevrimdışı mı çevrimiçi mi ağırlıklı olacağı; poster çıktısında desteklenecek en büyük alan ve baskı boyutu. Bunlar netleşene kadar rapordaki Python + kendi çekirdek + CLI + yerel MCP yaklaşımı uygulanabilir başlangıç önerisidir.

İlk geliştirme işi, küçük bir İstanbul veri örneğinde bina/yol/su/yeşil alanları iki özgün temayla çizip PNG/SVG/PDF ve manifesto üretmek olmalıdır. Bu iş; görsel kaliteyi, geometri doğruluğunu, bağımsızlığı ve kurulum maliyetini tek bir sınırlı sonuç üzerinde sınar.

