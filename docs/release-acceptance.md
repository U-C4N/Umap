# v0.2.0 kabul yönergesi / release acceptance

23 Ekim 2026 yayın kararı: yayın sorumlusu v0.2.0 için üç manuel yayın koşulunu
açıkça kaldırdı: Inkscape'te düzenleme/kaydetme/yeniden açma kabulü, üç gerçek
kullanıcı pilotu ve fiziksel 4 çekirdek/16 GB referans cihaz kabulü. Üçü de kanıt
kaydında `waived` olarak tutulur; yapılmış veya başarılı sayılmaz.

Inkscape uygulaması açıldı, ancak SVG düzenleme, kaydetme ve yeniden açma kabulü
tamamlanmadı. Kullanıcı pilotu ve fiziksel referans cihaz testi yapılmadı.
Geliştirme bilgisayarındaki üç ek benchmark koşusunun ikisi geçti, biri 5 saniyelik
önizleme hedeflerini aştı; ayrıntılar [doğrulama kaydında](validation.md).
Bu ölçümler referans donanım garantisi değildir.

Otomatik testler, platform matrisi, kurulu paket kontrolleri ve aynı CI paketinin
hash doğrulaması korunur. Aşağıdaki manuel kabul protokolü gelecekte uygulanmak
üzere saklanmıştır; v0.2.0 için yeniden zorunlu kapı oluşturmaz. `passed`, yalnız
gerçekten tamamlanmış başarılı kontrolü; `waived`, yayın sorumlusunun kaldırdığı
koşulu ifade eder.

## Gelecekteki manuel kabul protokolü

Bu protokol uygulanacak bir sürümde aşağıdaki adımları ve ölçütleri kullanın.
v0.2.0 için yukarıdaki tarihli yayın kararı geçerlidir.

### 1. Aynı adayı kullanın

Yayın sorumlusu başarılı aday CI çalışmasının Ubuntu/Python 3.14 artifact'inden
wheel ve sdist dosyalarını indirir. Aday commit SHA, CI run ID, artifact ID ve iki
dosyanın SHA-256 değerlerini kaydeder. Katılımcılara aynı wheel, bu yönerge ve
[Türkçe başlangıç](hizli-baslangic.md) belgesi verilir. PyPI'daki önceki sürümü
kurmak ya da kaynak checkout'undan çalıştırmak bu kabulü karşılamaz.

Windows'ta indirilen wheel'in hash'i:

```powershell
Get-FileHash .\umap_art-0.2.0-py3-none-any.whl -Algorithm SHA256
```

Python 3.12–3.14 ile yeni bir ortam açın ve aynı wheel'i kurun. Bu kurulum internet
gerektirebilir. Örneğin Windows PowerShell:

```powershell
python -m venv acceptance-env
.\acceptance-env\Scripts\python.exe -m pip install .\umap_art-0.2.0-py3-none-any.whl
.\acceptance-env\Scripts\python.exe -m umap_art --version
.\acceptance-env\Scripts\python.exe -m umap_art doctor
```

Linux/macOS'ta Python yolu `acceptance-env/bin/python` olur. Bundan sonra aynı
ortamın Python'unu kullanın. Kurulum, font kurulumu ve Inkscape hazırlığı bittikten
sonra interneti kapatın. Kurulum süresini kullanıcı görev süresinden ayrı kaydedin.
Örnek görevlerde `PYTHON` yazan yeri Windows'ta
`.\acceptance-env\Scripts\python.exe`, Linux/macOS'ta `./acceptance-env/bin/python`
ile değiştirin. Bu bir komut adı değil, yukarıda doğruladığınız ortamın tam yoludur.

### 2. Üç yeni kullanıcıyla pilot

Katılımcılar Umap'i daha önce kullanmamış mimar veya tasarımcılar olmalıdır.
Kimlikleri `P1`, `P2`, `P3` olarak tutulur; isim veya kişisel bilgi gerekmez.
Gözlemci süre tutar ve takılmaları kaydeder; görevleri kullanıcı yerine yapmaz,
ek komut veya çözüm söylemez. Yalnız belgeler kullanılabilir. Geliştirici yardımı
gereken deneme başarısız kaydedilir; düzeltme sonrası yeni deneme açıkça ayrılır.

Kurulumdan sonra süreyi başlatın:

1. `PYTHON -m umap_art demo --output acceptance-output` ile poster üretin.
   Komutun gösterdiği PNG ve PDF dosyalarını açın.
2. `PYTHON -m umap_art demo --preset guide --output acceptance-output` ve
   `PYTHON -m umap_art demo --preset atlas --output acceptance-output` çalıştırın.
   Rehberde üç örnek nokta, atlasta dört ayrı görünüm olduğunu kontrol edin.
3. Posterin `recipe.json` dosyasını metin düzenleyicide açın. `style.theme`
   değerini `blueprint` yapın. `places` listesinin ilk iki nesnesinin sırasını
   değiştirin; her nesnenin `id`, `label` ve `coordinates` alanlarını birlikte
   taşıyın. Aynı dosyayı kaydedin. Yanındaki `snapshot.json` dosyasına dokunmayın.
4. `PYTHON -m umap_art render <recipe.json-yolu> --output acceptance-revised`
   ile yeniden üretin. Tema ve numaralar değişmeli; noktaların konumları aynı kalmalı.
5. Üretilen `general.svg` dosyasını Inkscape'te açın. Başlığı ve tek bir binanın
   rengini değiştirip ayrı dosyaya kaydedin. Tekrar açarak sonucu kontrol edin.
6. Son projenin `project.zip` dosyasını başka bir klasöre çıkarın. Çıkarılan
   `recipe.json` dosyasını `render` ile yeniden üretin. Bu adım hâlâ internet kapalıyken
   tamamlanmalıdır. SVG editöründe yapılan değişikliklerin recipe'ye geri aktarılması
   beklenmez; yeniden üretim recipe'deki tasarımı kullanır.

Kabul: üç kullanıcının üçü de bütün görevleri yardımsız ve veri kaybetmeden bitirir.
İlk faydalı poster en fazla 5 dakika, bütün görevler en fazla 15 dakika sürer.
Bu eşikler küçük pilot içindir; genel kullanıcı kitlesi için hız garantisi değildir.

| Katılımcı | İşletim sistemi / Python | Kurulum süresi | İlk çıktı | Bütün görevler | Yardım / hata | Sonuç |
|---|---|---|---|---|---|---|
| P1 | pending | pending | pending | pending | pending | pending |
| P2 | pending | pending | pending | pending | pending | pending |
| P3 | pending | pending | pending | pending | pending | pending |

Tablo gelecekte doldurulacak boş bir şablondur; v0.2.0 için yapılmış pilot kaydı değildir.

### 3. Inkscape kabulü

Üretilen proje klasöründeki `assets/fonts/DejaVuSans.ttf` fontunu kabul bilgisayarına kurun.
Inkscape sürümünü kaydedin. Poster ve rehber SVG'lerinde ayrı ayrı:

- Başlığı `Kadıköy — Çığ, Iİıi` olarak değiştirin; metin metin olarak düzenlenebilsin.
- Gerekirse gruba girerek tek bina, tek yol ve bir noktanın rengini değiştirin.
- Yeni dosya adıyla kaydedin, kapatın ve yeniden açın.
- Sayfa 210 × 297 mm kalmalı; değiştirilmemiş öğeler yerinden oynamamalı.
- Türkçe glifler ve atıf okunmalı; kırpılmış başlık veya liste olmamalı.
- PDF çıktısını da açın; yerleşim ve sayfa ölçüsü PNG/SVG ile uyuşmalı.

Önce/sonra SVG'leri ve ekran görüntülerini kanıt paketine ekleyin. Bu bir geri
aktarım testi değildir: harici SVG düzenlemesi Umap recipe'sini güncellemez.

### 4. Referans cihaz performansı

Gerçek 4 fiziksel çekirdek ve 16 GB sınıfı RAM'e sahip cihaz kullanın. CPU modeli,
işletim sistemi, Python sürümü, güç modu ve takılı RAM'i kaydedin. Güçlü bir cihaza
işlemci affinity sınırı koymak yeterli değildir. Sanal makine kullanıldıysa bunu
ayrıca belirtin; gerçek referans donanım kabulü olarak işaretlemeyin.

Aday commit'teki `scripts/benchmark.py` dosyasını indirin. Aynı wheel'in kurulu
olduğu ortamda yalnız benchmark yardımcısı `psutil` paketini ekleyin. Scripti
checkout dışındaki bir klasörden çalıştırın; ortamda editable Umap bulunmamalı.

```sh
PYTHON -m pip install psutil
PYTHON benchmark.py --check --output benchmark-run-1
PYTHON benchmark.py --check --output benchmark-run-2
PYTHON benchmark.py --check --output benchmark-run-3
```

Üç komut da sıfır çıkış koduyla bitmelidir. Her çalışmanın `latest.json` dosyasının
işaret ettiği raporu saklayın. Script ağdan harita indirmez. Her koşuda:

- Soğuk A3, 300 DPI, PNG + SVG + PDF + ZIP: en fazla 30 saniye.
- Tanımlı sıcak/önbellekli/düzenleme önizlemeleri: en fazla 5 saniye.
- Her aşamada örneklenen tepe RSS: en fazla 2 GiB.
- Yeni poster çerçevesinin ilk hazırlığı ayrı raporlanır; sıcak önizleme eşiği yoktur.

Scriptin kendi raporladığı donanım bilgilerini de kontrol edin. `--check` donanımın
gerçek referans cihaz olduğunu doğrulamaz ve ağdan ilk edinimin hızını ölçmez.

### 5. Kanıtların teslimi

Kanıt paketinde aday kimliği, paket hash'leri, Inkscape önce/sonra dosyaları,
anonim pilot tablosu ve üç benchmark raporu bulunsun. Yayın sorumlusu bunları
taslak GitHub Release'e yükleyip [yayın yönergesindeki](publishing.md)
`release-evidence.json` kaydına bağlar. Kayıt doğru paket için doğrulanmadan
`pending` alanları `passed` yapılmaz.

v0.2.0 kanıt kaydında kaldırılan üç manuel koşul için `waived` ve sahibinin
23 Ekim 2026 tarihli kararı korunur; bu boş protokol şablonu başarılı kanıt olarak
eklenmez. Gerçek otomatik sonuçlar ve varsa başarısız ölçümler ayrıca kaydedilir.

Kaynak, demo verisi veya bağımlılık değişirse yeni aday oluşur; eski adayın kabul
sonuçları yeni pakete otomatik taşınmaz.
