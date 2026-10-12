# Umap hızlı başlangıç

Umap, seçtiğin bölgenin açık harita verisini çevrimiçi alır; PNG, düzenlenebilir SVG
ve vektör PDF üretir. Hesap veya API anahtarı gerekmez.

## Kurulum ve ilk harita

Depo klasöründe Python 3.12–3.14 ile:

```sh
python -m pip install '.[mcp]'
umap-art doctor
umap-art render examples/kadikoy.json --output outputs
```

MCP kullanmayacaksan `python -m pip install .` yeterlidir. Windows'ta komut
bulunamazsa aynı Python ortamıyla `python -m umap_art` kullanabilirsin.

İlk indirme ortak servislerin hızına bağlıdır. Sonuçlar `outputs` altında her işlem
için ayrı klasöre yazılır. Eski çıktının üzerine yazılmaz.

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
üretilir. `style.theme` için `architectural` ve `city_poster` seçenekleri vardır.

## Kaydetme ve yeniden üretim

Her sonuç klasöründeki `recipe.json`, yanındaki `snapshot.json` dosyasına bağlanır.
Bu tarifi yeniden çizmek internet gerektirmez. Klasörün tamamını veya `project.zip`
arşivini sakla. Tarif dosyasını tek başına taşıma.

Renk değişikliği için kayıtlı tarifin `style.layers` alanını düzenleyip tekrar
`umap-art render` çalıştır. Yeni harita verisi almak için aynı tarif üzerinde
`umap-art refresh` kullan; başarısız yenileme eski dosyaları değiştirmez.

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
