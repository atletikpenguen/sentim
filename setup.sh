#!/bin/bash

# Sentimentalgo Scraper Setup Script
# Ubuntu/Debian için otomatik kurulum

echo "========================================="
echo "Sentimentalgo Scraper Kurulum Başlıyor"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Bu scripti root kullanıcısı olarak çalıştırmayın."
    echo "Lütfen normal kullanıcı olarak çalıştırın."
    exit 1
fi

# Update system
echo "1. Sistem güncellemeleri yapılıyor..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo ""
echo "2. Python ve pip kuruluyor..."
sudo apt install -y python3 python3-pip python3-venv

# Install system dependencies for Playwright
echo ""
echo "3. Playwright sistem bağımlılıkları kuruluyor..."
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
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0

# Create virtual environment
echo ""
echo "4. Python sanal ortamı oluşturuluyor..."
python3 -m venv venv

# Activate virtual environment
echo ""
echo "5. Sanal ortam aktifleştiriliyor..."
source venv/bin/activate

# Install Python packages
echo ""
echo "6. Python paketleri kuruluyor..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo ""
echo "7. Playwright browser'ları kuruluyor..."
playwright install chromium
sudo playwright install-deps chromium

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "8. .env dosyası oluşturuluyor..."
    cp .env.example .env
    echo ".env dosyası oluşturuldu. Gerekirse düzenleyebilirsiniz."
else
    echo ""
    echo "8. .env dosyası zaten mevcut."
fi

# Check for credentials.json
echo ""
if [ ! -f credentials.json ]; then
    echo "⚠️  UYARI: credentials.json dosyası bulunamadı!"
    echo ""
    echo "Google Service Account oluşturmanız gerekiyor:"
    echo "1. https://console.cloud.google.com/ adresine gidin"
    echo "2. Yeni proje oluşturun"
    echo "3. Google Sheets API ve Google Drive API'yi aktifleştirin"
    echo "4. Service Account oluşturun ve JSON key indirin"
    echo "5. İndirdiğiniz dosyayı 'credentials.json' olarak bu dizine kopyalayın"
    echo ""
else
    echo "✓ credentials.json dosyası bulundu."
fi

echo ""
echo "========================================="
echo "✓ Kurulum tamamlandı!"
echo "========================================="
echo ""
echo "Sonraki adımlar:"
echo ""
echo "1. credentials.json dosyasını ekleyin (henüz eklemediyseniz)"
echo "2. Google Sheets'i service account ile paylaşın"
echo "3. Scraper'ı test edin:"
echo "   source venv/bin/activate"
echo "   python3 scraper.py"
echo ""
echo "4. Otomatik çalıştırma için cron job ekleyin:"
echo "   crontab -e"
echo "   */30 * * * * cd $(pwd) && $(pwd)/venv/bin/python3 $(pwd)/scraper.py >> $(pwd)/scraper.log 2>&1"
echo ""
echo "Detaylı bilgi için README.md dosyasını okuyun."
echo ""
