# Kabul edilmiş v0.2.0 paketini yayımlama

Kararlı sürüm, gerçek Inkscape kabulü, üç kullanıcı pilotu ve referans makinedeki
üç performans koşusu tamamlanmadan yayımlanmaz. Aday için RC yayımlamak gerekmez:
GitHub Actions çıktıları ve taslak GitHub Release kullanılır. Yerel test başarısı,
bu insan ve donanım kanıtlarının yerine geçmez.

Yayın akışı **kabul testinde kullanılan wheel ve sdist dosyalarını aynen taşır**.
Release sırasında yeniden paket üretmez. `release-evidence.json` eksikse, aday
kimliği uyuşmazsa veya artifact süresi dolmuşsa PyPI yüklemesi durur.

## Bir kez yapılacak hesap ayarları

[GitHub Environments](https://github.com/U-C4N/Umap/settings/environments)
içindeki mevcut `pypi` ortamını ve onay ayarlarını kontrol et. Yayın sorumlusu
kararlı yayını başlatmadan önce gerçek kabul kanıtlarını incelemelidir.
İstenirse **Required reviewers** ile bu kontrol ortam onayına da bağlanabilir;
bu ek ayar yayın için yeni bir zorunlu onay süreci değildir. Mevcut ortam onayı
etkinse workflow onu kullanır. `environment: pypi` satırı tek başına reviewer
koruması oluşturmaz.

PyPI'da `umap-art` projesinin Trusted Publisher kaydı şu değerleri kullanır:

| Alan | Değer |
|---|---|
| Owner | `U-C4N` |
| Repository | `Umap` |
| Workflow | `publish.yml` |
| Environment | `pypi` |

Proje ilk kez oluşturulacaksa aynı değerlerle `umap-art` için pending publisher
kaydı gerekir. Mevcut kayıt her sürümde yeniden oluşturulmaz. OIDC kullanılır;
GitHub'a PyPI parolası veya uzun ömürlü API anahtarı eklenmez.

## 1. Kaynakları koru ve adayı dondur

Mevcut izlenen değişiklikleri ve izlenmeyen release dosyalarını koru; yalnız
incelenmiş dosyaları commit'e al. `git clean` veya değişiklikleri atan bir reset
bu sürecin parçası değildir. Kaynak, örnek, font/veri lisansları, testler, şemalar,
belgeler, `uv.lock` ve workflow'lar aynı aday commit içinde olmalı.

`pyproject.toml`, `src/umap_art/__init__.py` ve lockfile sürümü **0.2.0** olmalı.
Değişiklikler incelendikten sonra `main` üzerindeki nihai commit SHA'sını kaydet.
Kabul başladıktan sonra bu commit'i değiştirme; yeni bir değişiklik yeni bir aday
ve ilgili kanıtların yenilenmesini gerektirir. Kanıtları aday commit'ine sonradan
eklemek yerine taslak Release'e ekle; böylece aday SHA değişmez.

## 2. Aday CI çalışmasını ve dosyalarını seç

`main` üzerindeki adayın normal `push` veya `workflow_dispatch` CI çalışmasını
bekle. Fork, pull request veya başka workflow sonuçları yayın adayı sayılmaz.

Şunların tamamı başarılı olmalı:

- Windows x64, Linux x64, macOS ARM64 × Python 3.12, 3.13, 3.14: dokuz işte
  locked kurulum, Ruff, offline testler, paket üretimi ve kurulu wheel doğrulaması.
- Üç işletim sisteminin Python 3.14 işinde plain pip ile core wheel kurulumu.
- Ubuntu/Python 3.14 işinde sdist'in checkout dışında wheel'e dönüştürülmesi ve
  temiz ortama kurulup doğrulanması.

Canonical artifact **`umap-ubuntu-24.04-py3.14`** içindeki `dist/` dosyalarıdır.
Bu artifact'in ID'sini ve başarılı CI run ID'sini kaydet. Artifact'ler 90 gün
saklanır. ZIP'i indir; `dist/` altındaki wheel ve sdist'i değiştirmeden koru.
Yerel `dist/` dosyalarını bunların yerine koyma ve paketleri yeniden üretme.

PowerShell ile indirilen dosyaların SHA-256 değerlerini hesaplayabilirsin:

```powershell
Get-FileHash -Algorithm SHA256 .\dist\umap_art-0.2.0-py3-none-any.whl
Get-FileHash -Algorithm SHA256 .\dist\umap_art-0.2.0.tar.gz
```

Manifestte hash'leri küçük harfle yaz. CI'nin kendi test sonuçlarını ve bu
dosyaları kabul süresince sakla. Yalnız önceki bir sürümün yeşil olması yeterli
değildir; CI run `head_sha` değeri tam olarak aday SHA olmalı.

## 3. Aynı wheel ile gerçek kabulü tamamla

Canonical wheel'i kabul ortamlarına kur. [Adım adım kabul yönergesini](release-acceptance.md)
uygula: Inkscape'te gerçek düzenleme/kaydetme/yeniden açma; üç ayrı kullanıcıyla
tam iş akışı; gerçek 4 çekirdek/16 GiB makinede üç bağımsız benchmark koşusu.
Benchmark'ı `--check` ile çalıştır; başarısız koşuyu başarılı diye kaydetme.

Her kanıt kaydında aday SHA, wheel SHA-256, uygulama/işletim sistemi bilgileri,
tarih ve sonuç bulunsun. Performans kayıtları gerçek donanımı, üç ayrı JSON raporu
ve ölçülen eşikleri içersin. Pilot kimlikleri anonim olabilir; üç ayrı kullanıcı
oldukları anlaşılmalı. Başarısız ya da eksik kabul varsa kararlı yayın bekler.

## 4. Taslak Release'e kanıt dosyasını ekle

[`release-evidence.example.json`](release-evidence.example.json) dosyasını
`release-evidence.json` adıyla kopyala. Örnekteki `null` ve `pending` değerleri
bilinçlidir: örnek yayın kapısını geçmez ve tamamlanmış kanıt değildir.

| Alan | Nasıl doldurulur? |
|---|---|
| `schema_version` | `"1"` |
| `version` | `"0.2.0"` |
| `candidate_sha` | Aday commit'in 40 karakterli küçük harf SHA'sı |
| `ci_run_id` | Aynı SHA'nın başarılı, `main` kaynaklı CI run ID'si; pozitif sayı |
| `artifact_id` | O çalışmadaki canonical artifact ID'si; pozitif sayı |
| `files.wheel`, `files.sdist` | İndirilen iki dosyanın tam adı ve SHA-256 değeri |
| `manual.inkscape` | Gerçek kabul başarılıysa `passed`, HTTPS kanıt bağlantısı |
| `manual.pilot.results` | Üç ayrı `participant_id`, her biri `passed` ve kanıt bağlantısı |
| `manual.performance.reports` | Üç ayrı başarılı koşunun HTTPS kanıt bağlantıları |

Pilot ve performance üst `status` değerlerini yalnız tüm alt kayıtlar başarılı
olduğunda `passed` yap. Doğrulayıcı ek/bilinmeyen alanları reddeder; URL'leri komut
veya veri kaynağı olarak kullanmaz. Kanıt bağlantıları yayın sorumlusunun
inceleyebileceği kayıtlar olmalı.

Bu manifest **insanın beyanıdır**. Workflow kimlikleri, hash'leri, kayıt sayılarını
ve `passed` durumlarını denetler; ekran görüntülerinin doğruluğunu, üç gerçek
kişinin katılımını veya donanımın fiziksel özelliklerini bağımsız ölçmüş olmaz.
Yayın sorumlusu kanıtların içeriğini incelemelidir.

[Taslak GitHub Release](https://github.com/U-C4N/Umap/releases/new) oluştur;
hedefi tam olarak aday commit, etiketi **`v0.2.0`**, başlığı **`Umap Art 0.2.0`**
yap. Sürüm notlarını ekle ve dosyayı bu Release'e asset olarak yükle. Dosya adı
tam olarak `release-evidence.json` olmalı ve yalnız bir tane bulunmalı.
Kaynak depodaki örnek dosya, issue eki veya keyfî bir indirme URL'si kullanılmaz.

## 5. Yayını başlat

İnsan/donanım kabulü ve kanıt dosyası tamamlandıktan sonra **Publish release**
düğmesine bas. Bu adım GitHub Release'i görünür yapar. Varsa mevcut `pypi` ortam
onayı GitHub Release'in görünürlüğünü değil, sonraki PyPI yüklemesini durdurur.

Yayın workflow'u sırasıyla:

1. Tag ile kaynak sürümünü karşılaştırır; remote tag'in çözülen commit'i checkout
   ve `candidate_sha` ile aynı olmalı.
2. Yalnız bu Release'in kanıt asset'ini GitHub API üzerinden okur.
3. CI'nin aynı depodaki `.github/workflows/ci.yml` çalışması olduğunu, `main`
   üzerindeki güvenilen olaydan geldiğini ve tamamının başarılı olduğunu doğrular.
4. Kaydedilen artifact ID'sinin o CI çalışmasına ait, doğru adlı ve süresi
   dolmamış olduğunu doğrular. Resmî `actions/download-artifact` adımı, doğrulanmış
   artifact ID ve run ID ile aynı depodaki o çalışmanın artifact'ini indirir.
5. Yalnız kaydedilen iki `dist/` dosyasını seçer; hash'leri ve wheel/sdist içindeki
   paket adı/sürüm metadata'sını doğrular. Bu aşama paket kodu çalıştırmaz.
6. Doğrulanmış baytları ayrı bir workflow artifact'ine aktarır. Varsa mevcut
   `pypi` onayından sonra ayrı job tam iki dosyanın adlarını ve SHA-256 değerlerini yeniden
   doğrular, sonra PyPI'ya gönderir; checkout, build veya kurulum yapmaz.

Yayın sorumlusu SHA'yı, aday CI'yi, paket hash'lerini ve manuel kayıtları kontrol
eder; mevcut ortam onayı varsa bunu tamamlar. [Actions](https://github.com/U-C4N/Umap/actions)
başarısızsa otomatik
olarak yeni build'e veya farklı artifact'e geçilmez.

## 6. PyPI sonucunu doğrula

Yayın işi başarılı olduğunda temiz bir ortamda:

```sh
python -m pip install "umap-art[mcp]==0.2.0"
umap-art --version
umap-art doctor
umap-art demo --preset poster --output outputs
```

[PyPI](https://pypi.org/project/umap-art/) üzerindeki wheel/sdist hash'lerini kabul
edilmiş dosyalarla karşılaştır. GitHub Release'in görünür olması tek başına PyPI
yüklemesinin tamamlandığı anlamına gelmez. Gerçek sonucu ve varsa takip işlerini
Release kaydına ekle; geçmiş aday kanıtlarını değiştirme.

## Hata, yeniden deneme ve sonraki sürüm

| Durum | İşlem |
|---|---|
| Kanıt eksik veya kabul başarısız | Kararlı yayını beklet; eksik kabulü tamamla. |
| Artifact yok, süresi dolmuş veya hash farklı | Yükleme durur. Yeni aday paketleriyle kabulü yenile; sessiz rebuild yapma. |
| Geçici API/CI erişim hatası | Aynı aday ve dosyalarla workflow'u yeniden dene. |
| Yalnız PyPI job'ı geçici hata verdi, henüz dosya yüklenmedi | **Re-run failed jobs** aynı doğrulanmış artifact'i kullanır. |
| Yükleme kısmen tamamlandı veya sürüm zaten var | Körlemesine yeniden deneme yapma. PyPI dosyalarının SHA-256 değerlerini adayla karşılaştır; yalnız eksik dosyalar için kontrollü yayın kurtarması gerekir. |
| Trusted Publisher eşleşmiyor | Owner/repository/workflow/environment alanlarını kontrol et. |
| Ortam onayı bekleniyor | Yetkili yayın sorumlusu gerçek kanıtları inceleyip onaylar. |
| Henüz yayımlanmamış adayda kod değişti | Yeni SHA/CI/artifact kaydı oluştur; ilgili kabulü yenile. |
| Yayımlanmış sürümde kod hatası var | Tag'i taşıma, dosya üzerine yazma; 0.2.1 gibi yeni patch hazırla. Gerekirse sorunlu PyPI sürümünü yank et. |

PyPI dosyaları değiştirilemez. `skip-existing: false` kullanılır: mevcut bir
dosyanın aynı baytları taşıdığı doğrulanmadan yükleme başarılı sayılmaz. Kısmi
yüklemede önce mevcut dosyaları ve hash'lerini doğrula; farklı içerik varsa aynı
sürümle devam etme, yeni patch sürümü hazırla. Sonraki sürümde
paket/public/lock sürümlerini birlikte güncelle; yeni
aday CI ve o sürüme ait yeni kanıt dosyasıyla aynı süreci uygula.
