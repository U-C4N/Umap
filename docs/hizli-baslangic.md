# Umap hızlı başlangıç

Umap, seçtiğin bölgenin açık harita verisini çevrimiçi alır; PNG, düzenlenebilir SVG
ve vektör PDF üretir. Hesap veya API anahtarı gerekmez.

## Kurulum ve ilk mimari set

Depo klasöründe Python 3.12–3.14 ile:

```sh
python -m pip install '.[mcp]'
umap-art doctor
umap-art demo --preset atlas --output outputs
```

MCP kullanmayacaksan `python -m pip install .` yeterlidir. Windows'ta komut
bulunamazsa aynı Python ortamıyla `python -m umap_art` kullanabilirsin.

Kurulum Python bağımlılıklarını indirebilir; `demo` paketle gelen Kadıköy verisini
kullanır ve harita servislerine bağlanmaz. JSON düzenlemeden dolu-boş, yollar,
yeşil alanlar ve su için dört A4 portre sayfa üretir. Hepsi 1:5000 ölçektedir.
Komut PNG önizlemelerinin, SVG/PDF'lerin, tarifin ve proje klasörünün yolunu gösterir.
Sonuçlar `outputs` altında her işlem için ayrı klasöre yazılır.

Önce bir PNG aç. Ardından SVG'yi vektör düzenleyicine al: tekil bina ve yol çizgileri,
katman grupları ve metinler düzenlenebilir. Yazı için teslim edilen DejaVu Sans
fontunu kur; teslim paketi bu fontun lisansını da taşır.

## Bir semt, üç anlatı

```sh
umap-art demo --preset guide --output outputs
umap-art demo --preset poster --output outputs
umap-art demo --theme neon --output outputs
```

Rehber blueprint, poster vintage temasıyla başlar; `--theme` temayı değiştirir.
Üç örnek de aynı kayıtlı veriyi kullanır. Poster ve rehberdeki üç nokta örnek kullanıcı
seçimleridir; doğrulanmış işletme veya yürüyüş rotası değildir. Atlasın harita alanı
daha uzundur: aynı veri ve ölçek, bütün düzenlerin aynı kadrajı gösterdiği anlamına
gelmez. Veriler 12 Ekim 2026'da alınmıştır; güncel saha ölçümü değildir.

![Aynı Kadıköy verisinden mimari set, rehber ve poster](release-showcase.png)

Her çalıştırma kendi PNG, SVG, PDF, `recipe.json`, `snapshot.json`, kaynak bilgileri
ve `project.zip` dosyasını üretir. Önceki çıktılar korunur. Kurulu pakette bu demo
örnekleri bulunur; ayrı bir örnek dosyası indirmek gerekmez.

Kendi bölgeni çizmek için aşağıdaki konum akışını ve [Python örneğini](../README.md#create-a-poster-in-python)
kullan. İlk veri edinimi çevrimiçidir ve ortak servislerin hızına bağlıdır.

## Konum seçimi

```sh
umap-art locations "Kadıköy, İstanbul"
```

Sonuçlardan doğru ülke/il/ilçeyi seç ve `center` değerini tarife koy. Koordinat
sırası **boylam, enlem**; bbox sırası **batı, güney, doğu, kuzey**.

`area.center` ile `scale_denominator: 5000` kullanırsan kâğıt değişince kapsanan
alan değişir. `area.bbox` kullanırsan alan kâğıda sığdırılır ve ölçek hesaplanır.
Yer adı seçmek bütün ilçenin idari sınırını seçmek anlamına gelmez.

## Mimari görünüm seti

```sh
umap-art render examples/architecture-atlas.json --output outputs
```

Aynı merkez ve ölçekte dolu-boş, yollar, yeşil alanlar ve su için dört ayrı sayfa
üretilir. Analiz görünümleri varsayılan `classic` düzenini kullanır.

## Kendi posterini oluşturma

```sh
umap-art render examples/kadikoy-poster.json --output outputs
umap-art render examples/kadikoy-guide.json --output outputs
umap-art styles
```

Altı tema: `architectural`, `city_poster`, `minimal`, `blueprint`, `vintage`, `neon`.
`page.layout="poster"` başlığı haritanın altında ortalar; `guide` üstte gösterir.
İkisi de `views=["general"]` ile kullanılır ve altta iki sütunlu mekân listesi sunar.
[Tema galerisi ve ayrıntılar](posters.md).

Tarifin `places` listesine en fazla 12 nesne ekle: `id`, `label` ve
`coordinates: [boylam, enlem]`. Örnek tariflerdeki noktalar gösterim amaçlıdır;
gerçek işletme önerileri değildir. Kendi seçtiğin koordinatlarla değiştir.
Numaralar liste sırasından gelir; `id` değerini aynı mekân için koru.

`style.ink` yazı rengini, `style.accent` işaret rengini, `page.title_size_pt` ve
`page.subtitle_size_pt` yazı boyutlarını ayarlar. Liste bandı boşken de sabittir;
nokta ekleyip çıkarmak harita alanını değiştirmez. Yazı taşarsa kısalt veya boyutunu
ayarla; metin otomatik kesilmez. Harita dışındaki konum hata, çakışan işaret uyarı verir.

v0.2 eski tarifleri okur. Yeni alanları taşıyan tarifleri açmak için v0.2 gerekir;
tarif şema numarası `1` olarak kalır.

## Kaydetme ve yeniden üretim

Her sonuç klasöründeki `recipe.json`, yanındaki `snapshot.json` dosyasına bağlanır.
Bu tarifi yeniden çizmek internet gerektirmez. Klasörün tamamını veya `project.zip`
arşivini sakla. Tarif dosyasını tek başına taşıma.

Renk değişikliği için kayıtlı tarifin `style.layers` alanını düzenleyip tekrar
`umap-art render` çalıştır. Yeni harita verisi almak için aynı tarif üzerinde
`umap-art refresh` kullan; başarısız yenileme eski dosyaları değiştirmez.
MCP'de kapsamı büyüten sayfa değişikliği için `refresh_map_data` aracına mevcut
`base_revision` ile `changes` gönder. Başarılı yenileme tek bir yeni revizyon üretir.

## MCP

```sh
umap-art mcp --workspace ./map-workspace
```

MCP istemcisine bu komutu, mutlak workspace yoluyla tanıt. İstemci harita oluşturup
iş kimliğini sorgulayabilir; yalnız yolların rengini değiştirebilir; revizyonları
geri yükleyebilir ve çıktıları alabilir. Sunucunun kendi model API anahtarına
ihtiyacı yoktur.

## Çıktıyı düzenleme

SVG öğeleri katman grupları ve nesne kimlikleri taşır. Metin düzenlemek için
teslim paketindeki DejaVu Sans fontunu düzenleyici ortamına kur. Fonta bağlı
kalmamak için `page.text_mode` değerini `outline` yap; bu modda harfler yola dönüşür.

Harita verisindeki eksiklikleri gerçek dünyada yapı veya yol yokluğu olarak
yorumlama. Kaynak tarihleri ve tanılar `manifest.json` içindedir. Kaynak atıflarını
paylaşılan çıktılarda koru.
