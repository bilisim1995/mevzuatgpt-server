# 🐧 Ubuntu Sunucu Paket Kurulum Rehberi

Bu rehber, migration sonrası Ubuntu sunucusunda yapılması gereken paket kurulumlarını içerir.

## 📋 Yapılacaklar Listesi

1. ✅ Sistem paketleri (Tesseract OCR, Poppler)
2. ✅ Python paketleri (requirements.txt güncellemesi)
3. ✅ Servisleri yeniden başlatma
4. ✅ Test ve doğrulama

---

## 🔧 1. Sistem Paketleri Kurulumu

### Tesseract OCR ve Poppler Kurulumu

```bash
# Sistem güncellemesi
sudo apt update

# Tesseract OCR kurulumu (PDF'lerden metin çıkarma için)
sudo apt install -y tesseract-ocr

# Türkçe dil paketi (opsiyonel ama önerilir)
sudo apt install -y tesseract-ocr-tur

# İngilizce dil paketi (varsayılan)
sudo apt install -y tesseract-ocr-eng

# Poppler-utils (PDF2Image için gerekli)
sudo apt install -y poppler-utils

# Image processing kütüphaneleri (Pillow için)
sudo apt install -y libjpeg-dev zlib1g-dev libpng-dev libtiff-dev libwebp-dev
```

### Kurulum Doğrulama

```bash
# Tesseract versiyonunu kontrol et
tesseract --version

# Türkçe dil paketinin kurulu olduğunu kontrol et
tesseract --list-langs | grep tur

# Poppler araçlarını kontrol et
pdftoppm -v
```

**Beklenen Çıktı:**
```
tesseract 4.1.1 (veya üzeri)
tur (Türkçe dil paketi listede görünmeli)
```

---

## 🐍 2. Python Paketleri Kurulumu

### Virtual Environment Aktifleştirme

```bash
# Proje dizinine git
cd /opt/mevzuatgpt-server/MevzuatGPT

# Virtual environment'ı aktifleştir
source venv/bin/activate

# pip'i güncelle
pip install --upgrade pip
```

### Yeni Python Paketlerini Kurma

```bash
# OCR ve PDF işleme paketleri
pip install pytesseract>=0.3.10
pip install pdf2image>=1.16.3
pip install Pillow>=10.0.0

# VEYA tüm requirements.txt'i güncelle
pip install -r requirements.txt --upgrade
```

### Kurulum Doğrulama

```bash
# Python paketlerinin kurulu olduğunu kontrol et
python -c "import pytesseract; print('✅ pytesseract:', pytesseract.__version__)"
python -c "import pdf2image; print('✅ pdf2image: OK')"
python -c "from PIL import Image; print('✅ Pillow:', Image.__version__)"

# Tesseract'in Python'dan erişilebilir olduğunu kontrol et
python -c "import pytesseract; print('Tesseract path:', pytesseract.pytesseract.tesseract_cmd)"
```

**Beklenen Çıktı:**
```
✅ pytesseract: 0.3.10 (veya üzeri)
✅ pdf2image: OK
✅ Pillow: 10.0.0 (veya üzeri)
Tesseract path: /usr/bin/tesseract
```

---

## 🔄 3. Servisleri Yeniden Başlatma

### Celery Worker'ı Yeniden Başlat

```bash
# Celery servisini durdur
sudo systemctl stop mevzuat-celery

# Servisi yeniden başlat
sudo systemctl start mevzuat-celery

# Durumu kontrol et
sudo systemctl status mevzuat-celery

# Logları kontrol et
sudo journalctl -u mevzuat-celery -f --lines=50
```

### API Servisini Yeniden Başlat (Opsiyonel)

```bash
# API servisini yeniden başlat (eğer değişiklik varsa)
sudo systemctl restart mevzuat-api

# Durumu kontrol et
sudo systemctl status mevzuat-api
```

---

## ✅ 4. Test ve Doğrulama

### OCR Fonksiyonunu Test Et

```bash
# Python shell'de test
cd /opt/mevzuatgpt-server/MevzuatGPT
source venv/bin/activate
python
```

Python shell'de:

```python
# OCR test
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import io

# Tesseract'in çalıştığını test et
try:
    print(pytesseract.image_to_string(Image.new('RGB', (100, 100), color='white')))
    print("✅ OCR çalışıyor!")
except Exception as e:
    print(f"❌ OCR hatası: {e}")

# PDF2Image test
try:
    # Test için basit bir kontrol
    from pdf2image import convert_from_bytes
    print("✅ pdf2image import başarılı!")
except Exception as e:
    print(f"❌ pdf2image hatası: {e}")

exit()
```

### PDF Parsing Test

```bash
# Test scripti oluştur
cat > /tmp/test_pdf_ocr.py << 'EOF'
import sys
sys.path.insert(0, '/opt/mevzuatgpt-server/MevzuatGPT')

from services.pdf_source_parser import PDFSourceParser
import requests

# Test PDF indir (opsiyonel)
# pdf_url = "https://example.com/test.pdf"
# pdf_content = requests.get(pdf_url).content

# Veya mevcut bir PDF'i test et
# with open('/path/to/test.pdf', 'rb') as f:
#     pdf_content = f.read()

# parser = PDFSourceParser()
# result = parser.parse_pdf_with_sources(pdf_content, "test.pdf")
# print(f"Parsing başarılı: {result.get('parsing_success')}")
# print(f"Chunk sayısı: {len(result.get('chunks', []))}")

print("✅ PDF parser import başarılı!")
EOF

python /tmp/test_pdf_ocr.py
```

---

## 🚨 Sorun Giderme

### Tesseract Bulunamıyor Hatası

```bash
# Tesseract path'ini kontrol et
which tesseract

# Python'da path ayarla (gerekirse)
# /opt/mevzuatgpt-server/MevzuatGPT/services/pdf_source_parser.py dosyasında:
# import pytesseract
# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
```

### Poppler Bulunamıyor Hatası

```bash
# Poppler kurulumunu kontrol et
dpkg -l | grep poppler

# Eksikse tekrar kur
sudo apt install --reinstall poppler-utils
```

### Memory Hatası (Büyük PDF'ler için)

```bash
# Swap alanı ekle (eğer yoksa)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Kalıcı yapmak için /etc/fstab'a ekle
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Permission Hatası

```bash
# Celery worker kullanıcısının gerekli dosyalara erişimi olduğundan emin ol
sudo chown -R www-data:www-data /opt/mevzuatgpt-server/MevzuatGPT
sudo chmod -R 755 /opt/mevzuatgpt-server/MevzuatGPT
```

---

## 📊 5. Performans Optimizasyonu (Opsiyonel)

### Tesseract Optimizasyonu

```bash
# Tesseract config dosyası oluştur (daha hızlı OCR için)
sudo nano /etc/tesseract/tesseract.conf
```

İçeriğe ekle:
```
# Daha hızlı OCR için
tessedit_pageseg_mode 6  # Uniform block of text
tessedit_char_whitelist ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZabcçdefgğhıijklmnoöprsştuüvyz0123456789.,;:!?()[]{}/-+*=
```

### PDF İşleme Limitleri

Eğer çok büyük PDF'ler işleniyorsa, `services/pdf_source_parser.py` dosyasında:

```python
# DPI ayarını düşür (daha hızlı ama daha az kaliteli)
images = convert_from_bytes(pdf_content, dpi=200)  # 300 yerine 200
```

---

## ✅ Kurulum Tamamlandı Kontrol Listesi

- [ ] Tesseract OCR kuruldu ve çalışıyor
- [ ] Türkçe dil paketi kuruldu
- [ ] Poppler-utils kuruldu
- [ ] Python paketleri (pytesseract, pdf2image, Pillow) kuruldu
- [ ] Celery worker yeniden başlatıldı
- [ ] OCR test başarılı
- [ ] PDF parsing test başarılı
- [ ] Loglarda hata yok

---

## 🎯 Sonraki Adımlar

1. **PDF Yükleme Testi**: Gerçek bir PDF yükleyip işleme alın
2. **Log İzleme**: Celery loglarını izleyin ve OCR fallback'in çalıştığını doğrulayın
3. **Performans İzleme**: Büyük PDF'lerin işleme süresini kontrol edin

---

## 📝 Notlar

- OCR işlemi CPU yoğun bir işlemdir, büyük PDF'ler için zaman alabilir
- Görüntü tabanlı PDF'ler için OCR kullanılır, metin tabanlı PDF'ler için normal parsing yeterlidir
- Tesseract Türkçe dil desteği için `tesseract-ocr-tur` paketi gereklidir
- Poppler-utils PDF'leri görüntüye dönüştürmek için gereklidir

---

**Son Güncelleme:** Migration sonrası OCR desteği eklendi
**Hazırlayan:** MevzuatGPT Development Team

