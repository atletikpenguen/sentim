# Sentimentalgo Web Scraper

Sentimentalgo.com'dan hisse senedi ve endeks verilerini otomatik olarak çekip Google Sheets'e yazan Python web scraper uygulaması.

## 📋 İçindekiler

- [Uygulama Ne Yapıyor?](#uygulama-ne-yapıyor)
- [Nasıl Çalışıyor?](#nasıl-çalışıyor)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Ayarları Değiştirme](#ayarları-değiştirme)
- [Cron Job Yönetimi](#cron-job-yönetimi)
- [Sorun Giderme](#sorun-giderme)

---

## 🎯 Uygulama Ne Yapıyor?

Bu uygulama şu işlemleri otomatik olarak gerçekleştirir:

### 1. Hisse Senedi Verisi Çekme (Sayfa1)
- **Kaynak:** https://app.sentimentalgo.com/bist/lines
- **Çekilen Veri:** BIST hisse senetleri ve teknik göstergeleri (3 sayfa)
- **Google Sheets:** Sayfa1'e **ekleme (append)** modu ile yazılır
- Özellikler:
  - Sayfalama desteği (3 sayfa veri)
  - Tüm hisse senetleri ve göstergeleri
  - Her çalışmada yeni satırlar eklenir

### 2. Endeks Verisi Çekme (Sayfa2)
- **Kaynak:** https://app.sentimentalgo.com/index/home (Pano sekmesi)
- **Çekilen Veri:** XU100 ve diğer endeks verileri (205 satır)
- **Google Sheets:** Sayfa2'ye **UPSERT** modu ile yazılır
- Özellikler:
  - Mevcut satırlar: Sadece "Son Çekilme Tarihi" güncellenir
  - Yeni satırlar: Tüm veri ile eklenir
  - Veri bütünlüğü korunur

### 3. Veri İşleme
- ✅ Ondalık ayırıcı dönüşümü (. → ,) - Türkiye lokali için
- ✅ Tarih damgası ekleme
- ✅ Rate limit kontrolü (Google Sheets API)
- ✅ Batch update ile performans optimizasyonu

---

## 🔄 Nasıl Çalışıyor?

### Genel Akış

```
┌─────────────────────────────────────────────────────────────────┐
│                        ANA PROGRAM BAŞLAR                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Playwright    │
                    │  Context Açılır│
                    └────────┬───────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Login İşlemi  │
                    │  (Tek Seferlik)│
                    └────────┬───────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
    ┌──────────────────────┐  ┌──────────────────────┐
    │  HİSSE SENEDİ        │  │  ENDEKS VERİSİ       │
    │  VERİSİ ÇEK          │  │  ÇEK                 │
    └──────────┬───────────┘  └──────────┬───────────┘
               │                          │
               ▼                          ▼
    ┌──────────────────────┐  ┌──────────────────────┐
    │  Sayfa1'e APPEND     │  │  Sayfa2'ye UPSERT    │
    │  (Yeni satır ekle)   │  │  (Timestamp güncelle)│
    └──────────────────────┘  └──────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Browser Kapat │
                    └────────────────┘
```

### Detaylı İş Akışı

#### 1️⃣ Başlangıç ve Login
```python
# Playwright browser başlatılır (headless mode)
# → Tek browser, tek context, iki scraper için paylaşımlı
# → Login bir kez yapılır
# → Aynı session iki scraper için kullanılır
```

#### 2️⃣ Hisse Senedi Scraping (Sayfa1)

```
Navigate → sentimentalgo.com/bist/lines
    ↓
Popup'ları kapat (varsa)
    ↓
Sayfa 1'i oku
    ↓
"Sonraki" butonuna tıkla
    ↓
Sayfa 2'yi oku
    ↓
"Sonraki" butonuna tıkla
    ↓
Sayfa 3'ü oku
    ↓
Tüm veriyi birleştir (30 satır)
    ↓
Ondalık nokta → virgül dönüşümü
    ↓
Google Sheets Sayfa1'e ekle (APPEND)
```

**Sayfa Geçiş Mantığı:**
- Ant Design pagination komponenti kullanılır
- `.ant-pagination-next` butonu ile sayfa geçişi
- Buton disabled olunca döngü durur
- Her sayfa sonrası 2 saniye beklenir

#### 3️⃣ Endeks Scraping (Sayfa2)

```
Navigate → sentimentalgo.com/index/home
    ↓
Popup'ları kapat (varsa)
    ↓
"Pano" butonunu bul ve tıkla
    ↓
5 saniye bekle (sayfa yüklensin)
    ↓
Tabloyu JavaScript evaluate() ile oku (205 satır)
    ↓
Ondalık nokta → virgül dönüşümü
    ↓
UPSERT mantığı ile Google Sheets Sayfa2'ye yaz
```

**UPSERT Mantığı:**
```
Her satır için:
    ├─ İlk sütun değeri (endeks adı) zaten var mı?
    │
    ├─ EVET → Sadece son sütunu güncelle (Son Çekilme Tarihi)
    │          Diğer veriler korunur
    │
    └─ HAYIR → Yeni satır olarak tüm veriyi ekle
```

#### 4️⃣ Google Sheets Yazma

**Sayfa1 (Append Mode):**
```python
# Mevcut satır sayısını al
start_row = len(existing_data) + 1

# Tek seferde tüm satırları yaz
worksheet.update(f'A{start_row}:J{end_row}', rows_to_add)
```

**Sayfa2 (UPSERT Mode):**
```python
# Batch update listesi oluştur
updates = [
    {'range': 'J5', 'values': [['18.11.2025 14:10']]},  # Sadece timestamp
    {'range': 'A206:J206', 'values': [[new_row_data]]}, # Yeni satır
    # ... 205 satır için
]

# Tek API çağrısı ile tüm güncellemeleri yap
worksheet.batch_update(updates)
```

**Rate Limit Önleme:**
- Google Sheets API: 60 yazma/dakika limiti
- `batch_update()` kullanarak 205 istek → 1 istek'e düşürülür

---

## 💻 Kurulum

### 1. Sistem Gereksinimleri
- Ubuntu 18.04+ veya Debian
- Python 3.7+
- Root veya sudo yetkisi

### 2. Otomatik Kurulum

```bash
# Projeyi indir
git clone https://github.com/atletikpenguen/sentim.git
cd sentim

# Kurulum scriptini çalıştır
bash setup.sh
```

**Setup.sh ne yapar?**
- Sistem paketlerini günceller
- Python3, pip, wget kurar
- Virtual environment oluşturur
- Playwright kurar ve Chromium browser'ı indirir
- Gerekli Python paketlerini yükler

### 3. Manuel Kurulum

```bash
# 1. Python paketlerini kur
sudo apt update && sudo apt install -y python3 python3-pip python3-venv

# 2. Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate

# 3. Gereksinimleri yükle
pip install -r requirements.txt

# 4. Playwright browser'ı kur
playwright install chromium
```

### 4. Google Credentials Ayarla

1. Google Cloud Console'a git: https://console.cloud.google.com/
2. Yeni proje oluştur veya mevcut projeyi seç
3. Google Sheets API'yi etkinleştir
4. Service Account oluştur:
   - IAM & Admin → Service Accounts
   - Create Service Account
   - JSON key indir
5. İndirilen JSON'ı `credentials.json` olarak kaydet
6. Google Sheets'i service account email ile paylaş (Editor yetkisi)

### 5. .env Dosyasını Yapılandır

```bash
cp .env.example .env
nano .env
```

```env
# Sentimentalgo giriş bilgileri
SENTIMENT_EMAIL=your_email@gmail.com
SENTIMENT_PASSWORD=your_password

# Google Sheets bilgileri
SHEET_ID=your_sheet_id_here
SHEET_NAME=Sayfa1
INDEX_SHEET_NAME=Sayfa2
GOOGLE_CREDENTIALS_FILE=credentials.json
```

**Sheet ID'yi bulmak:**
```
https://docs.google.com/spreadsheets/d/1uw7Ymoa86ttsclYQxnIH3AQNrEDeTZExKZ_Z5Azw7Oo/edit
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                       Bu kısım Sheet ID'dir
```

---

## 🚀 Kullanım

### Manuel Çalıştırma

```bash
cd /root/sentim
source venv/bin/activate
python3 scraper.py
```

**Çıktı Örneği:**
```
==================================================
Sentimentalgo Scraper
==================================================

--- Scraping Stock Data ---
Logging in...
Checking for popups...
Found 3 pages
Page 1/3...
Page 2/3...
Page 3/3...
Extracted 30 rows of stock data
✓ Successfully added 30 rows to Google Sheet

--- Scraping Index Data ---
Navigating to index page...
Looking for 'Pano' tab...
Found Pano tab with: .chart-menu-buttons button:has-text("Pano")
Found 205 rows
Performing batch update with 205 updates...
✓ Successfully updated 205 rows in Sayfa2

✓ Browser closed
==================================================
SUCCESS: All data scraped and uploaded!
==================================================
```

### Log Takibi

```bash
# Real-time log izle
tail -f /root/sentim/scraper.log

# Son 50 satır
tail -50 /root/sentim/scraper.log

# Log dosyasını temizle
> /root/sentim/scraper.log
```

---

## ⚙️ Ayarları Değiştirme

### Çalışma Saatlerini Değiştirme

```bash
crontab -e
```

**Örnekler:**

```bash
# Her gün 11:10, 14:10 ve 18:10'da
10 11,14,18 * * * cd /root/sentim && /root/sentim/venv/bin/python3 /root/sentim/scraper.py >> /root/sentim/scraper.log 2>&1

# Sadece hafta içi günlerde 09:00'da
0 9 * * 1-5 cd /root/sentim && /root/sentim/venv/bin/python3 /root/sentim/scraper.py >> /root/sentim/scraper.log 2>&1

# Her 6 saatte bir
0 */6 * * * cd /root/sentim && /root/sentim/venv/bin/python3 /root/sentim/scraper.py >> /root/sentim/scraper.log 2>&1

# Her saat başı
0 * * * * cd /root/sentim && /root/sentim/venv/bin/python3 /root/sentim/scraper.py >> /root/sentim/scraper.log 2>&1
```

**Cron Format:**
```
┌───────────── dakika (0-59)
│ ┌───────────── saat (0-23)
│ │ ┌───────────── ayın günü (1-31)
│ │ │ ┌───────────── ay (1-12)
│ │ │ │ ┌───────────── haftanın günü (0-7, 0 ve 7 = Pazar)
│ │ │ │ │
* * * * *
```

### Sayfa Sayısını Değiştirme

Hisse senedi verisinde daha fazla/az sayfa çekmek için:

```python
# scraper.py içinde (satır ~195)
max_pages = 3  # Bunu istediğin sayıya değiştir
```

### Bekleme Sürelerini Ayarlama

Sayfa yükleme sorunları yaşıyorsan:

```python
# scraper.py içinde
time.sleep(3)  # 3 saniye yerine 5 veya 10 yapabilirsin
```

**Kritik bekleme noktaları:**
- Login sonrası: 3 saniye
- Tab tıklama sonrası: 3 saniye
- Pano tab için: 5 saniye (cron için önemli)
- Sayfa geçişi sonrası: 2 saniye

### Farklı Sheet'e Yazmak

```bash
# .env dosyasını düzenle
nano .env
```

```env
SHEET_ID=yeni_sheet_id_buraya
SHEET_NAME=FarklıSayfaAdı
INDEX_SHEET_NAME=BaşkaSayfaAdı
```

---

## 🕐 Cron Job Yönetimi

### Cron Job Ekleme

```bash
crontab -e
```

Aşağıdaki satırı ekle:
```bash
10 11,14,18 * * * cd /root/sentim && /root/sentim/venv/bin/python3 /root/sentim/scraper.py >> /root/sentim/scraper.log 2>&1
```

### Cron Job'u Görüntüleme

```bash
crontab -l
```

### Cron Job'u Durdurma

**Geçici olarak devre dışı bırak (yorum satırı yap):**
```bash
crontab -e
# Satırın başına # ekle:
# 10 11,14,18 * * * cd /root/sentim && /root/sentim/venv/bin/python3 /root/sentim/scraper.py >> /root/sentim/scraper.log 2>&1
```

**Tamamen kaldır:**
```bash
crontab -e
# İlgili satırı sil ve kaydet
```

### Cron Job'u Tekrar Başlatma

```bash
crontab -e
# Yorum işaretini (#) kaldır ve kaydet
```

### Cron Servisini Kontrol Etme

```bash
# Cron servisi çalışıyor mu?
sudo systemctl status cron

# Cron servisini başlat
sudo systemctl start cron

# Cron servisini durdur
sudo systemctl stop cron

# Cron servisini yeniden başlat
sudo systemctl restart cron
```

### Cron Loglarını İnceleme

```bash
# Cron'un çalışıp çalışmadığını kontrol et
grep CRON /var/log/syslog | tail -20

# Sentim scraper'a özel loglar
grep sentim /var/log/syslog | tail -20
```

---

## 🛠️ Sorun Giderme

### 1. "Pano tab not found" Hatası (Cron'da)

**Sebep:** Cron'dan çalıştığında sayfa yüklenmesi daha yavaş oluyor.

**Çözüm:** Kod zaten 3 deneme + 5 saniye bekleme içeriyor. Eğer hala sorun varsa:

```python
# scraper.py içinde (satır ~385)
time.sleep(5)  # Bunu 10'a çıkar
max_attempts = 3  # Bunu 5'e çıkar
```

### 2. "Rate Limit Exceeded" (429) Hatası

**Sebep:** Google Sheets API dakikada 60 yazma isteği limiti.

**Çözüm:** Kod zaten batch_update kullanıyor. Eğer hala sorun varsa:

```python
# Birden fazla sheet'e yazma arasına delay ekle
import time
time.sleep(10)  # 10 saniye bekle
```

### 3. Login Başarısız

**Kontrol edilecekler:**
```bash
# .env dosyasını kontrol et
cat .env

# Credentials doğru mu?
SENTIMENT_EMAIL=doğru_email@gmail.com
SENTIMENT_PASSWORD=doğru_şifre
```

### 4. Google Sheets'e Yazamıyor

**Kontrol edilecekler:**

```bash
# 1. credentials.json var mı?
ls -lh credentials.json

# 2. Sheet ID doğru mu?
cat .env | grep SHEET_ID

# 3. Service account email sheet'e eklenmiş mi?
# → Google Sheets'i aç
# → Share → service account email'i ekle (Editor yetkisi)
```

### 5. Screenshot Debug

Sorun olduğunda ne gördüğünü anlamak için:

```python
# scraper.py içinde screenshot'ları etkinleştir
page.screenshot(path="debug.png")

# Her önemli adımda screenshot al
page.screenshot(path="after_login.png")
page.screenshot(path="after_pano_click.png")
```

### 6. Headless Mode'u Kapatma (Debug için)

```python
# scraper.py içinde (satır ~865)
browser = p.chromium.launch(headless=False)  # False yap
```

Bu şekilde browser görünür olur ve ne olduğunu izleyebilirsin.

### 7. Çalışan Process'i Durdurma

```bash
# Çalışan scraper'ı bul
ps aux | grep scraper.py

# PID'yi kullanarak durdur
kill <PID>

# Zorla durdur
kill -9 <PID>
```

### 8. Dependencies Eksik

```bash
cd /root/sentim
source venv/bin/activate
pip install --upgrade -r requirements.txt
playwright install chromium
```

### 9. Timezone Sorunları

VPS farklı saat diliminde ise:

```bash
# VPS'in saat dilimini kontrol et
timedatectl

# Türkiye saatine ayarla
sudo timedatectl set-timezone Europe/Istanbul

# Doğrula
date
```

---

## 📊 Veri Formatı

### Sayfa1 (Hisse Senedi Verileri)

| Sütun | Açıklama | Örnek |
|-------|----------|-------|
| A | Hisse Kodu | THYAO |
| B | Fiyat | 123,45 |
| C | Değişim % | 2,34 |
| D | Hacim | 1234567 |
| E | Sentiment | Pozitif |
| ... | Diğer göstergeler | ... |
| J | Son Çekilme Tarihi | 18.11.2025 14:10 |

**Not:** Ondalık sayılar virgül (,) ile yazılır (Türkiye lokali).

### Sayfa2 (Endeks Verileri)

| Sütun | Açıklama | Örnek |
|-------|----------|-------|
| A | Endeks Adı | XU100 |
| B | Endeks Değeri | 9876,54 |
| C | Günlük Sentiment | 45,67 |
| D | Günlük Sentiment 2 | 12,34 |
| E | Günlük Sentiment - Mom | -2,34 |
| ... | Diğer göstergeler | ... |
| J | Son Çekilme Tarihi | 18.11.2025 14:10 |

**UPSERT Davranışı:**
- Endeks zaten varsa: Sadece **J sütunu** (Son Çekilme Tarihi) güncellenir
- Yeni endeks: Tüm satır eklenir

---

## 🔒 Güvenlik

### Credentials Güvenliği

```bash
# .env ve credentials.json'ı git'e ekleme
# .gitignore dosyası zaten bunları hariç tutuyor

# Dosya izinlerini kontrol et
chmod 600 .env
chmod 600 credentials.json
```

### API Anahtarlarını Paylaşma

- ❌ .env dosyasını GitHub'a yükleme
- ❌ credentials.json'ı public yapma
- ❌ Log dosyalarını paylaşma (şifreler içerebilir)
- ✅ .env.example kullan (örnek değerlerle)

---

## 📁 Proje Yapısı

```
sentim/
├── scraper.py              # Ana scraper kodu
├── setup.sh                # Otomatik kurulum scripti
├── requirements.txt        # Python paket gereksinimleri
├── .env                    # Konfigürasyon (GİZLİ)
├── .env.example            # Örnek konfigürasyon
├── credentials.json        # Google Service Account (GİZLİ)
├── README.md               # Bu dosya
├── HIZLI_BAŞLANGIÇ.md     # Hızlı başlangıç rehberi
├── last_update.txt         # Son çalışma zamanı
├── scraper.log             # Log dosyası
├── venv/                   # Python virtual environment
└── *.png                   # Debug screenshot'ları (opsiyonel)
```

---

## 📝 Notlar

### Performans

- **Hisse Senedi Scraping:** ~30 saniye (3 sayfa)
- **Endeks Scraping:** ~20 saniye (205 satır)
- **Google Sheets Yazma:** ~5 saniye (batch update)
- **Toplam:** ~1 dakika

### Limitler

- **Google Sheets API:** 60 yazma/dakika
- **Playwright Memory:** 205+ satır için evaluate() kullan
- **Cron Frequency:** Minimum 1 dakika aralıklarla

### Best Practices

1. ✅ Her zaman virtual environment kullan
2. ✅ Log dosyalarını düzenli kontrol et
3. ✅ credentials.json'ı güvenli tut
4. ✅ Test için önce manuel çalıştır
5. ✅ Cron job eklemeden önce doğrula

---

## 🆘 Destek

Sorun yaşarsan:

1. **Log dosyasını kontrol et:**
   ```bash
   tail -100 /root/sentim/scraper.log
   ```

2. **Manuel çalıştır ve hata mesajını gör:**
   ```bash
   cd /root/sentim
   source venv/bin/activate
   python3 scraper.py
   ```

3. **Screenshot'ları incele:**
   ```bash
   ls -lh *.png
   ```

4. **GitHub Issues:**
   https://github.com/atletikpenguen/sentim/issues

---

## 📄 Lisans

Bu proje kişisel kullanım içindir. Ticari kullanım için izin gereklidir.

---

## 🎉 Geliştirmeler

### Yapılan İyileştirmeler

- ✅ Event loop sorunu düzeltildi (tek Playwright context)
- ✅ Pano tab seçici güncellendi (.chart-menu-buttons)
- ✅ Bellek sorunu çözüldü (evaluate() kullanımı)
- ✅ Rate limit sorunu giderildi (batch_update)
- ✅ Satır numarası artırma düzeltildi (next_available_row)
- ✅ Cron timing sorunları giderildi (retry logic + bekleme)
- ✅ Türkçe locale desteği (ondalık . → ,)
- ✅ Sayfa2 için timestamp-only update

### Gelecek İyileştirmeler

- ⏳ E-posta bildirimleri (başarı/hata)
- ⏳ Telegram bot entegrasyonu
- ⏳ Dashboard/UI
- ⏳ Veri analizi ve görselleştirme
- ⏳ Çoklu kullanıcı desteği
- ⏳ Docker containerization

---

**Son Güncellenme:** 18 Kasım 2025
**Versiyon:** 1.0.0
