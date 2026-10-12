# GitHub üzerinden PyPI'ya yayımlama

Bu depodaki `publish.yml`, yayımlanan bir GitHub Release için testleri çalıştırır
ve başarılı olursa `umap-art` paketini PyPI'ya gönderir. İlk yayın öncesinde aşağıdaki
GitHub ve PyPI ayarlarını bir kez yapmalısın. Bu dosyanın bulunması paketin zaten
yayımlandığı anlamına gelmez.

Kimlik doğrulama **Trusted Publishing / OIDC** ile yapılır. GitHub'a PyPI parolası
veya uzun ömürlü API anahtarı eklemek gerekmez.
[PyPI'nın resmî yayınlama açıklaması](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
bu mekanizmayı tarif eder.

## 1. GitHub ortamını oluştur

[Umap → Settings → Environments](https://github.com/U-C4N/Umap/settings/environments)
sayfasını aç. **New environment** ile adı tam olarak `pypi` olan ortamı oluştur.
Workflow ve PyPI kaydındaki ortam adı bununla aynı olmalı.

Ortam için onay veren bir kişi tanımlarsan, yayın işi testlerden sonra o kişinin
GitHub onayını bekler. Ortamın dağıtım kısıtları kullanılıyorsa sürüm etiketlerinin
bu ortama erişebildiğinden emin ol.

## 2. PyPI'da ilk yayıncıyı kaydet

PyPI hesabına giriş yap ve hesabın gerektirdiği e-posta/iki aşamalı doğrulamayı
tamamla. Paket henüz oluşturulmadığı için
[hesabının Publishing sayfasını](https://pypi.org/manage/account/publishing/) aç.
**Add a new pending publisher** bölümünde **GitHub** seçeneğini şu bilgilerle doldur:

| PyPI alanı | Girilecek değer |
|---|---|
| PyPI Project Name | `umap-art` |
| Owner | `U-C4N` |
| Repository name | `Umap` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

Workflow alanına yalnız dosya adını yaz: `publish.yml`. GitHub'da dosyanın yolu
`.github/workflows/publish.yml` olacak.

Bu kayıt ilk başarılı yüklemede projeyi oluşturur ve normal yayıncı kaydına
dönüşür. Kayıt açmak paket adını rezerve etmez; yayın sırasında adın kullanılabilir
olması gerekir. Proje zaten senin hesabındaysa yayıncıyı projenin **Publishing**
ayarlarından ekle.
[PyPI'nın ilk proje için resmî yönergesi](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)

## 3. Hazır dosyaları GitHub'a gönder

İlk sürümün kaynakları, testleri, `uv.lock` ve iki workflow da sürüm etiketinin
işaret edeceği commit içinde olmalı. Bu checkout'un dalı `main`; depo kökünde:

```sh
git add .github .gitignore LICENSE README.md docs examples pyproject.toml scripts src tests uv.lock
git commit -m "Add Umap Art and trusted PyPI publishing"
git push origin main
```

Bu gönderim normal CI kontrollerini başlatır. PyPI yüklemesi için sonraki adımda
GitHub Release'i yayımlamak gerekir. Kaynaklar daha önce commit edilip gönderildiyse
aynı commit'i tekrar oluşturmana gerek yoktur.

## 4. `v0.1.0` GitHub Release'ini yayımla

[Yeni release sayfasını](https://github.com/U-C4N/Umap/releases/new) aç:

1. Yeni etiket olarak `v0.1.0` seç ve hedefi hazır dosyaları içeren `main` commit'i yap.
2. Başlığı `Umap Art 0.1.0` olarak yaz; sürüm notlarını ekle.
3. **Publish release** düğmesine bas.

Etiket, `pyproject.toml` içindeki sürümün başına `v` eklenmiş haliyle tam eşleşmeli:
`version = "0.1.0"` için `v0.1.0`. Taslak release kaydetmek veya yalnız etiketi
göndermek yayın işini başlatmaz. Tetikleyici `release: published` olayıdır.

[Actions sayfasından](https://github.com/U-C4N/Umap/actions) yayın çalışmasını izle.
Akış; Python 3.12, 3.13 ve 3.14 için Ubuntu x64, Windows x64 ve macOS ARM64
üzerindeki dokuz CI kombinasyonunu çalıştırır. Testler, paket üretimi veya kurulu
wheel doğrulaması başarısızsa **PyPI yüklemesi yapılmaz**. Başarılı kontrollerden
sonra ayrı yayın işi, `pypi` ortamında resmî PyPA action'ıyla paketi gönderir.

CI kontrolleri otomatik yayın koşullarıdır. Manuel tasarımcı pilotu gibi ayrıca
izlenen doğrulamalar [yayın durumunda](validation.md) listelenir.

## 5. Başarılı yayını kontrol et

Yayın işi başarılı olduktan sonra
[PyPI proje sayfasında](https://pypi.org/project/umap-art/) sürümü kontrol et.
Python 3.12 veya daha yeni bir ortamda:

```sh
python -m pip install "umap-art[mcp]==0.1.0"
umap-art --version
umap-art doctor
```

İlk komutun ilk başarılı yüklemeden önce çalışması beklenmez. GitHub Release'in
yayımlanmış olması tek başına PyPI yüklemesinin tamamlandığını göstermez;
Actions'taki yayın işinin sonucunu da kontrol et.

## Hata ve sonraki sürümler

| Durum | Yapılacak işlem |
|---|---|
| Trusted Publisher eşleşmiyor | Owner, depo, `publish.yml` ve `pypi` alanlarını yukarıdaki tabloyla karşılaştır. |
| Ortam onayı bekleniyor | GitHub'daki bekleyen deployment için ortamda tanımlı onayı tamamla. |
| Test veya kurulum başarısız | İlgili matrix işinin kaydındaki hatayı düzelt; düzeltilmiş commit'i yeni sürüm etiketiyle yayımla. |
| Geçici yükleme hatası | Aynı Actions çalışmasında **Re-run failed jobs** kullan. Workflow mevcut dosyaları denetleyerek yeniden denemeyi destekler. |
| Aynı sürümün içeriği değişti | Yeni bir sürüm numarası ve buna karşılık gelen yeni etiket kullan. PyPI'daki mevcut dosyaların üzerine yazılamaz. |

Sonraki sürümde `pyproject.toml` içindeki `version` ile
`src/umap_art/__init__.py` içindeki `__version__` değerini birlikte güncelle.
Yayın kontrolü bu iki değerin ve etiketin eşleşmesini ister. `uv lock` çalıştır,
değişiklikleri commit edip GitHub'a gönder. Ardından yeni sürümle eşleşen release'i
yayımla; örneğin `0.1.1` için `v0.1.1`. İlk yayıncı kaydı başarılı olduktan sonra
aynı depo, workflow ve ortam için PyPI kaydını her sürümde yeniden oluşturman
gerekmez.
