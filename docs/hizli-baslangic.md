# Umap hızlı başlangıç

Umap, açık harita verisinden PNG, düzenlenebilir SVG ve vektör PDF üretir.
Paketle gelen örneği çevrimdışı deneyebilir, kendi bölgenin verisini çevrimiçi
alabilirsin. Hesap veya API anahtarı gerekmez.

## Kurulum ve ilk poster

Python **3.12–3.14** kullan. Bu komutlar PyPI'da yayımlanmış **v0.2.0** paketini
gerektirir. Yayın ve doğrulama durumunu [v0.2.0 sürüm sayfasından](https://github.com/U-C4N/Umap/releases/tag/v0.2.0)
ve [doğrulama kaydından](validation.md) kontrol edebilirsin.

```sh
python -m pip install "umap-art==0.2.0"
umap-art doctor
umap-art demo
```

Komut bulunamazsa aynı Python ortamıyla `python -m umap_art` kullanabilirsin.
Depoyu klonlaman veya JSON düzenlemen gerekmez.

Kurulum Python bağımlılıklarını indirebilir; `demo` paketle gelen Kadıköy verisini
kullanır ve harita servislerine bağlanmaz. Varsayılan çıktı vintage temasında,
1:5000 ölçekte bir A4 portre posterdir.
Komut PNG önizlemelerinin, SVG/PDF'lerin, tarifin ve proje klasörünün yolunu gösterir.
Sonuçlar `outputs` altında her işlem için ayrı klasöre yazılır.

Önce bir PNG aç. Ardından SVG'yi vektör düzenleyicine al: tekil bina ve yol çizgileri,
katman grupları ve metinler düzenlenebilir. Yazı için teslim edilen DejaVu Sans
fontunu kur; teslim paketi bu fontun lisansını da taşır.

## Bir semt, üç anlatı

```sh
umap-art demo --preset guide --output outputs
umap-art demo --preset atlas --output outputs
umap-art demo --theme neon --output outputs
```

Rehber blueprint, atlas architectural, poster vintage temasıyla başlar;
`--theme` temayı değiştirir. Atlas dolu-boş, yollar, yeşil alanlar ve su için
dört ayrı A4 portre sayfa üretir; hepsi 1:5000 ölçektedir.
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
umap-art demo --preset atlas --output outputs
```

Aynı merkez ve ölçekte dolu-boş, yollar, yeşil alanlar ve su için dört ayrı sayfa
üretilir. Analiz görünümleri varsayılan `classic` düzenini kullanır.

## Kendi posterini oluşturma

[Depodaki tarifleri](../examples) indirip kendi bilgilerinle düzenleyebilir veya
[Python örneğiyle](../README.md#create-a-poster-in-python) başlayabilirsin.
Aşağıdaki komutlar depo kökünden çalışır; PyPI kurulumu bu dosyaları çalışma
klasörüne kopyalamaz:

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
python -m pip install "umap-art[mcp]==0.2.0"
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

## Geliştiriciler için kaynaktan kurulum

```sh
git clone https://github.com/U-C4N/Umap.git
cd Umap
python -m pip install ".[mcp]"
umap-art demo
```

MCP gerekmiyorsa `python -m pip install .` yeterlidir. Testler ve gösteri üretimi
için [geliştirme yönergesini](../README.md#development-and-verification) izle.
