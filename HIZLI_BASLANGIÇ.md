# Hızlı Başlangıç Kılavuzu

Bu kılavuz, scraper'ı en hızlı şekilde çalıştırmanız için adım adım talimatlar içerir.

## Adım 1: Kurulum

```bash
cd /home/user/sentim
bash setup.sh
```

Bu komut otomatik olarak:
- Sistem güncellemelerini yapar
- Python ve gerekli paketleri kurar
- Playwright browser'ları kurar
- Sanal ortamı oluşturur

## Adım 2: Google Service Account

### A. Service Account Oluşturma

1. Tarayıcınızda açın: https://console.cloud.google.com/
2. "Select a project" > "New Project" > Proje ismi girin (örn: "sentim-scraper") > "Create"
3. Sol menüden "APIs & Services" > "Library"
4. "Google Sheets API" arayın ve "Enable"
5. "Google Drive API" arayın ve "Enable"
6. Sol menüden "APIs & Services" > "Credentials"
7. "Create Credentials" > "Service Account"
8. İsim girin (örn: "sentim-bot") > "Create and Continue"
9. Role olarak "Editor" seçin > "Continue" > "Done"
10. Oluşturulan service account'a tıklayın
11. "Keys" sekmesi > "Add Key" > "Create new key" > "JSON" > "Create"
12. İndirilen dosyayı `credentials.json` olarak `/home/user/sentim/` dizinine kopyalayın

### B. Dosya Kopyalama (Eğer yerel bilgisayarınızdan VPS'e kopyalıyorsanız)

```bash
# Yerel bilgisayarınızdan çalıştırın:
scp credentials.json kullanici@vps-ip:/home/user/sentim/
```

Veya:
- FileZilla, WinSCP gibi FTP programları ile yükleyin

## Adım 3: Google Sheets Paylaşımı

1. Google Sheets dosyanızı açın: https://docs.google.com/spreadsheets/d/1daGabBAYapAd0sDqcvI6qn908Id2hz8Y/edit
2. Sağ üstteki "Share" butonuna tıklayın
3. `credentials.json` dosyasını açın ve `client_email` alanındaki email adresini kopyalayın
   - Örnek: `sentim-bot@sentim-scraper-123456.iam.gserviceaccount.com`
4. Bu email'i "Add people and groups" alanına yapıştırın
5. Yetki olarak "Editor" seçin
6. "Send" butonuna tıklayın

## Adım 4: Test

```bash
cd /home/user/sentim
source venv/bin/activate
python3 scraper.py
```

İlk çalıştırmada şunları göreceksiniz:
- Login sayfasına giriş yapılıyor
- Hedef sayfaya gidiliyor
- Tab'a tıklanıyor
- Son güncelleme zamanı kontrol ediliyor
- Tablo verisi çekiliyor
- Google Sheets'e ekleniyor

## Adım 5: Otomatik Çalıştırma (Cron)

Her 30 dakikada bir otomatik çalıştırmak için:

```bash
crontab -e
```

Aşağıdaki satırı ekleyin:
```
*/30 * * * * cd /home/user/sentim && /home/user/sentim/venv/bin/python3 /home/user/sentim/scraper.py >> /home/user/sentim/scraper.log 2>&1
```

Kaydet ve çık (nano için: CTRL+O, Enter, CTRL+X)

## Logları İzleme

```bash
# Canlı log izleme
tail -f /home/user/sentim/scraper.log

# Son 50 satır
tail -n 50 /home/user/sentim/scraper.log
```

## Cron Job Zamanlamaları

```bash
# Her 15 dakikada bir
*/15 * * * * cd /home/user/sentim && /home/user/sentim/venv/bin/python3 /home/user/sentim/scraper.py >> /home/user/sentim/scraper.log 2>&1

# Her 30 dakikada bir
*/30 * * * * cd /home/user/sentim && /home/user/sentim/venv/bin/python3 /home/user/sentim/scraper.py >> /home/user/sentim/scraper.log 2>&1

# Her saat başı
0 * * * * cd /home/user/sentim && /home/user/sentim/venv/bin/python3 /home/user/sentim/scraper.py >> /home/user/sentim/scraper.log 2>&1

# Her gün 09:00 ve 17:00
0 9,17 * * * cd /home/user/sentim && /home/user/sentim/venv/bin/python3 /home/user/sentim/scraper.py >> /home/user/sentim/scraper.log 2>&1

# Her pazartesi 09:00
0 9 * * 1 cd /home/user/sentim && /home/user/sentim/venv/bin/python3 /home/user/sentim/scraper.py >> /home/user/sentim/scraper.log 2>&1
```

## Sorun mu var?

### Hata: "credentials.json not found"
```bash
# credentials.json dosyasının doğru yerde olduğundan emin olun
ls -la /home/user/sentim/credentials.json
```

### Hata: "Permission denied"
```bash
# Google Sheets'te service account'a yetki verdiğinizden emin olun
# credentials.json içindeki client_email değerini kontrol edin
cat credentials.json | grep client_email
```

### Hata: Playwright browser hatası
```bash
# Sistem bağımlılıklarını tekrar kurun
sudo playwright install-deps chromium
playwright install chromium
```

### Giriş başarısız
- Email ve şifrenin doğru olduğunu kontrol edin (.env dosyası)
- Site yapısı değişmiş olabilir
- Screenshot dosyalarını kontrol edin: `screenshot.png` veya `error_screenshot.png`

## Yardım

Detaylı bilgi için: `README.md`

Sorun yaşıyorsanız:
1. Log dosyasını kontrol edin: `tail -n 100 scraper.log`
2. Screenshot dosyalarını kontrol edin
3. Manuel test çalıştırın ve çıktıyı inceleyin
