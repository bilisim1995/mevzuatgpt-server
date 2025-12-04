#!/bin/bash
# 🚀 MevzuatGPT Hızlı Paket Kurulum Scripti
# Ubuntu sunucusunda migration sonrası gerekli paketleri kurar

set -e  # Hata durumunda dur

echo "=========================================="
echo "🚀 MevzuatGPT Paket Kurulumu Başlıyor..."
echo "=========================================="

# 1. Sistem Paketleri
echo ""
echo "📦 Sistem paketleri kuruluyor..."
sudo apt update
sudo apt install -y \
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    poppler-utils \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev

echo "✅ Sistem paketleri kuruldu!"

# 2. Tesseract Doğrulama
echo ""
echo "🔍 Tesseract kontrol ediliyor..."
tesseract --version
if tesseract --list-langs | grep -q "tur"; then
    echo "✅ Türkçe dil paketi kurulu!"
else
    echo "⚠️  Türkçe dil paketi bulunamadı!"
fi

# 3. Python Paketleri
echo ""
echo "🐍 Python paketleri kuruluyor..."

# Proje dizinine git
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Virtual environment kontrolü
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment bulunamadı!"
    echo "💡 Önce virtual environment oluşturun: python3 -m venv venv"
    exit 1
fi

# Virtual environment'ı aktifleştir
source venv/bin/activate

# pip güncelle
pip install --upgrade pip

# OCR paketlerini kur
pip install pytesseract>=0.3.10 pdf2image>=1.16.3 Pillow>=10.0.0

echo "✅ Python paketleri kuruldu!"

# 4. Python Paket Doğrulama
echo ""
echo "🔍 Python paketleri kontrol ediliyor..."
python -c "import pytesseract; print('✅ pytesseract:', pytesseract.__version__)" || echo "❌ pytesseract import hatası"
python -c "import pdf2image; print('✅ pdf2image: OK')" || echo "❌ pdf2image import hatası"
python -c "from PIL import Image; print('✅ Pillow:', Image.__version__)" || echo "❌ Pillow import hatası"

# 5. Servisleri Yeniden Başlat
echo ""
echo "🔄 Servisler yeniden başlatılıyor..."

if systemctl is-active --quiet mevzuat-celery; then
    echo "⏸️  Celery worker durduruluyor..."
    sudo systemctl stop mevzuat-celery
    sleep 2
    echo "▶️  Celery worker başlatılıyor..."
    sudo systemctl start mevzuat-celery
    sleep 2
    if systemctl is-active --quiet mevzuat-celery; then
        echo "✅ Celery worker başarıyla başlatıldı!"
    else
        echo "⚠️  Celery worker başlatılamadı! Logları kontrol edin: sudo journalctl -u mevzuat-celery -f"
    fi
else
    echo "ℹ️  Celery worker servisi bulunamadı veya çalışmıyor"
fi

# 6. Özet
echo ""
echo "=========================================="
echo "✅ Kurulum Tamamlandı!"
echo "=========================================="
echo ""
echo "📋 Yapılanlar:"
echo "  ✅ Tesseract OCR kuruldu"
echo "  ✅ Türkçe dil paketi kuruldu"
echo "  ✅ Poppler-utils kuruldu"
echo "  ✅ Python OCR paketleri kuruldu"
echo "  ✅ Celery worker yeniden başlatıldı"
echo ""
echo "🧪 Test için:"
echo "  sudo journalctl -u mevzuat-celery -f"
echo ""
echo "📖 Detaylı bilgi için:"
echo "  destek/ubuntu_paket_kurulumu.md"
echo ""

