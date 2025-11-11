# Sentimentalgo Web Scraper

Ubuntu VPS'te çalışan, Sentimentalgo sitesinden veri çeken ve Google Sheets'e aktaran otomatik web scraper.

## Özellikler

- Otomatik giriş yapma
- Belirtilen tab'daki tablo verilerini çekme
- Son güncelleme kontrolü (sadece değişiklik varsa güncelleme)
- Google Sheets'e otomatik veri aktarımı
- Headless mod (arka planda çalışır)
- Cron job ile zamanlanabilir

## Gereksinimler

- Ubuntu 20.04+ veya benzeri Linux dağıtımı
- Python 3.8+
- Google Service Account (Google Sheets API erişimi için)

## Kurulum

### 1. Sistem Bağımlılıklarını Kurun

```bash
# Sistem güncellemeleri
sudo apt update && sudo apt upgrade -y

# Python ve pip
sudo apt install python3 python3-pip python3-venv -y
```

### 2. Python Sanal Ortamı Oluşturun

```bash
# Proje dizinine gidin
cd /home/user/sentim

# Sanal ortam oluşturun
python3 -m venv venv

# Sanal ortamı aktifleştirin
source venv/bin/activate
```

### 3. Python Paketlerini Kurun

```bash
pip install -r requirements.txt

# Playwright browser'ları kurun
playwright install chromium
playwright install-deps chromium
```

### 4. Google Service Account Oluşturun

1. [Google Cloud Console](https://console.cloud.google.com/) adresine gidin
2. Yeni bir proje oluşturun veya mevcut bir proje seçin
3. "APIs & Services" > "Enable APIs and Services" bölümüne gidin
4. "Google Sheets API" ve "Google Drive API"'yi aktifleştirin
5. "Credentials" > "Create Credentials" > "Service Account" seçin
6. Service account oluşturduktan sonra, "Keys" sekmesinden JSON key oluşturun
7. İndirilen JSON dosyasını `credentials.json` olarak proje dizinine kaydedin

### 5. Google Sheets Ayarları

1. Google Sheets dosyanızı açın
2. Sağ üst köşeden "Share" butonuna tıklayın
3. Service account email adresinizi ekleyin (credentials.json içinde `client_email` alanında bulabilirsiniz)
4. "Editor" yetkisi verin

### 6. Yapılandırma Dosyasını Oluşturun

```bash
# .env.example dosyasını kopyalayın
cp .env.example .env

# Gerekirse .env dosyasını düzenleyin
nano .env
```

`.env` dosyası varsayılan olarak doğru değerleri içeriyor. Değiştirmek isterseniz düzenleyebilirsiniz.

## Kullanım

### Manuel Çalıştırma

```bash
# Sanal ortamı aktifleştirin (henüz aktif değilse)
source venv/bin/activate

# Scraper'ı çalıştırın
python3 scraper.py
```

### Otomatik Çalıştırma (Cron Job)

Scraper'ı belirli aralıklarla otomatik çalıştırmak için cron job oluşturun:

```bash
# Crontab'ı düzenleyin
crontab -e

# Aşağıdaki satırı ekleyin (her 30 dakikada bir çalıştırır)
*/30 * * * * cd /home/user/sentim && /home/user/sentim/venv/bin/python3 /home/user/sentim/scraper.py >> /home/user/sentim/scraper.log 2>&1

# Veya her saat başı çalıştırmak için:
0 * * * * cd /home/user/sentim && /home/user/sentim/venv/bin/python3 /home/user/sentim/scraper.py >> /home/user/sentim/scraper.log 2>&1

# Veya her gün saat 09:00'da çalıştırmak için:
0 9 * * * cd /home/user/sentim && /home/user/sentim/venv/bin/python3 /home/user/sentim/scraper.py >> /home/user/sentim/scraper.log 2>&1
```

### Logları Kontrol Etme

```bash
# Log dosyasını görüntüleyin
tail -f scraper.log

# Son 50 satırı göster
tail -n 50 scraper.log

# Tüm logları temizle
> scraper.log
```

## Çalışma Mantığı

1. **Giriş**: Sentimentalgo sitesine otomatik giriş yapar
2. **Sayfa Gezinme**: `/bist/lines` sayfasına gider
3. **Tab Seçimi**: `#rc-tabs-1-tab-999` tab'ına tıklar
4. **Güncelleme Kontrolü**: Son güncelleme zamanını kontrol eder
5. **Veri Çekme**: Eğer güncelleme varsa, tablo verilerini çeker
6. **Google Sheets**: Verileri Google Sheets'e ekler
7. **Kayıt**: Son güncelleme bilgisini `last_update.txt` dosyasına kaydeder

## Sorun Giderme

### Playwright Hatası

Eğer Playwright browser hatası alırsanız:

```bash
# System dependencies
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2

# Playwright'i tekrar kurun
playwright install-deps chromium
```

### Google Sheets Erişim Hatası

- `credentials.json` dosyasının doğru yerde olduğundan emin olun
- Service account email'inin Google Sheets'te "Editor" yetkisi olduğunu kontrol edin
- Sheet ID'nin doğru olduğunu kontrol edin

### Giriş Başarısız

- Email ve şifrenin doğru olduğunu kontrol edin
- Sitenin HTML yapısı değişmiş olabilir, selector'ları güncellemeniz gerekebilir

### Debug

Hata durumunda `error_screenshot.png` dosyası oluşturulur. Bu dosyayı inceleyerek sorunu görebilirsiniz.

## Dosya Yapısı

```
sentim/
├── scraper.py              # Ana scraper script
├── requirements.txt        # Python bağımlılıkları
├── .env                   # Yapılandırma dosyası (gizli)
├── .env.example           # Örnek yapılandırma dosyası
├── credentials.json       # Google Service Account credentials (gizli)
├── last_update.txt        # Son güncelleme bilgisi
├── scraper.log            # Log dosyası
├── screenshot.png         # Başarılı scraping screenshot
├── error_screenshot.png   # Hata durumunda screenshot
└── README.md              # Bu dosya
```

## Güvenlik Notları

- `.env` ve `credentials.json` dosyalarını asla paylaşmayın veya git'e commit etmeyin
- VPS'te güvenlik için SSH key authentication kullanın
- Düzenli olarak sistem güncellemelerini yapın
- Scraper loglarını kontrol edin

## Lisans

Bu proje özel kullanım içindir.
