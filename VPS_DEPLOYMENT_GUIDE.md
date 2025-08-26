# 🚀 MevzuatGPT VPS Ubuntu 24.04 Deployment Rehberi

> **Not**: Bu rehber mevcut uzak Redis, Supabase ve Elasticsearch servislerinizi kullanarak basitleştirilmiş deployment içindir.

## 📋 Gerekli VPS Kaynakları

- **RAM**: 4GB minimum (8GB önerilen)
- **CPU**: 2 vCPU (4 vCPU önerilen)  
- **Disk**: 20GB SSD (PostgreSQL yok, sadece kod)
- **Bant Genişliği**: 500GB/ay

---

## 🔧 1. Sunucu Hazırlama

### Sistem Güncellemesi
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip software-properties-common build-essential
```

### Python 3.11+ Kurulumu
```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Python version kontrol
python3 --version  # Python 3.11.x olmalı
```

### Nginx Web Server Kurulumu
```bash
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Nginx test
sudo systemctl status nginx
```

---

## 🔄 2. Proje Kodunu Sunucuya Transfer

### Yöntem A: Git ile (Önerilen)
```bash
cd /opt
sudo mkdir mevzuatgpt && sudo chown $USER:$USER mevzuatgpt
cd mevzuatgpt

# GitHub'dan clone (eğer private repo ise SSH key gerekli)
git clone https://github.com/kullanici_adi/mevzuat-gpt.git .
```

### Yöntem B: SCP/SFTP ile dosya yükleme
```bash
# Lokal makinenizden:
scp -r ./mevzuat-gpt/ user@vps_ip:/opt/mevzuatgpt/

# VPS'de:
sudo chown -R $USER:$USER /opt/mevzuatgpt/
```

### Yöntem C: ZIP upload
```bash
# ZIP'i sunucuya yükleyin, sonra:
cd /opt
sudo unzip mevzuat-gpt.zip -d mevzuatgpt/
sudo chown -R $USER:$USER /opt/mevzuatgpt/
```

---

## ⚙️ 3. Python Environment ve Dependencies

### Virtual Environment Oluşturma
```bash
cd /opt/mevzuatgpt
python3 -m venv venv
source venv/bin/activate

# pip güncellemesi
pip install --upgrade pip
```

### Requirements Kurulumu
```bash
# Eğer requirements.txt varsa:
pip install -r requirements.txt

# Manuel kurulum (requirements.txt yoksa):
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0
pip install sqlalchemy==2.0.23
pip install asyncpg==0.29.0
pip install psycopg2-binary==2.9.9
pip install celery==5.3.4
pip install redis==5.0.1
pip install pydantic==2.5.2
pip install pydantic-settings==2.1.0
pip install openai==1.3.8
pip install groq==0.4.1
pip install langchain==0.1.0
pip install langchain-text-splitters==0.0.1
pip install pdfplumber==0.9.0
pip install pypdf2==3.0.1
pip install python-multipart==0.0.6
pip install supabase==2.3.0
pip install elasticsearch==8.11.1
pip install httpx==0.25.2
pip install aiohttp==3.9.1
pip install python-dotenv==1.0.0
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4
pip install sendgrid==6.11.0
pip install email-validator==2.1.0
pip install python-json-logger==2.0.7
pip install alembic==1.13.1
pip install pgvector==0.2.4
pip install numpy==1.25.2
```

---

## 🌍 4. Environment Variables Konfigürasyonu

### .env Dosyası Oluşturma
```bash
cd /opt/mevzuatgpt
nano .env
```

### Environment Variables İçeriği
```env
# ===========================================
# UZAK SERVİSLER (Mevcut)
# ===========================================

# Supabase (Uzak - Mevcut)
SUPABASE_URL=https://supabase.mevzuatgpt.org
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
SUPABASE_ANON_KEY=your_anon_key_here

# Elasticsearch (Uzak - Mevcut) 
ELASTICSEARCH_URL=https://elastic.mevzuatgpt.org/
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your_elastic_password_here

# Redis (Uzak - Mevcut)
REDIS_URL=redis://your_redis_host:6379/0
# Eğer Redis Cloud kullanıyorsanız:
# REDIS_URL=redis://default:password@redis-host:port/0

# ===========================================
# AI SERVİSLERİ
# ===========================================

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Groq
GROQ_API_KEY=your_groq_api_key_here

# ===========================================
# DOSYA DEPOLAMA
# ===========================================

# Bunny.net CDN (Mevcut)
BUNNY_STORAGE_URL=your_bunny_storage_url
BUNNY_API_KEY=your_bunny_api_key_here
BUNNY_CDN_URL=https://cdn.mevzuatgpt.org

# ===========================================
# EMAIL SERVİSİ
# ===========================================

# SendGrid
SENDGRID_API_KEY=your_sendgrid_api_key_here
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# ===========================================
# GÜVENLİK
# ===========================================

# JWT Security
JWT_SECRET_KEY=super_secure_random_jwt_secret_key_here_change_this
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# ===========================================
# UYGULAMA AYARLARI
# ===========================================

# Environment
ENVIRONMENT=production
DEBUG=False

# Domain ve CORS
ALLOWED_HOSTS=your_domain.com,www.your_domain.com,vps_ip_address
CORS_ORIGINS=https://your_domain.com,https://www.your_domain.com

# Server ayarları
HOST=0.0.0.0
PORT=5000
```

### Dosya İzinleri
```bash
chmod 600 .env  # Sadece owner okuyabilir
```

---

## 🔧 5. Systemd Services Kurulumu

### API Server Service
```bash
sudo nano /etc/systemd/system/mevzuat-api.service
```

```ini
[Unit]
Description=MevzuatGPT FastAPI Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/mevzuatgpt
Environment=PATH=/opt/mevzuatgpt/venv/bin
EnvironmentFile=/opt/mevzuatgpt/.env
ExecStart=/opt/mevzuatgpt/venv/bin/python app.py server
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# Resource limits
LimitNOFILE=65536
TimeoutStartSec=60

[Install]
WantedBy=multi-user.target
```

### Celery Worker Service
```bash
sudo nano /etc/systemd/system/mevzuat-celery.service
```

```ini
[Unit]
Description=MevzuatGPT Celery Worker
After=network.target
Wants=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/mevzuatgpt
Environment=PATH=/opt/mevzuatgpt/venv/bin
EnvironmentFile=/opt/mevzuatgpt/.env
ExecStart=/opt/mevzuatgpt/venv/bin/celery -A tasks.celery_app worker --loglevel=info --concurrency=2
Restart=always
RestartSec=5

# Resource limits
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### Dosya İzinleri ve Service Aktivasyonu
```bash
# Klasör sahipliğini değiştir
sudo chown -R www-data:www-data /opt/mevzuatgpt

# Systemd reload
sudo systemctl daemon-reload

# Services'i aktifleştir
sudo systemctl enable mevzuat-api
sudo systemctl enable mevzuat-celery

# Services'i başlat
sudo systemctl start mevzuat-api
sudo systemctl start mevzuat-celery

# Status kontrol
sudo systemctl status mevzuat-api
sudo systemctl status mevzuat-celery
```

---

## 🌐 6. Nginx Reverse Proxy Konfigürasyonu

### Site Konfigürasyonu
```bash
sudo nano /etc/nginx/sites-available/mevzuatgpt
```

```nginx
server {
    listen 80;
    server_name your_domain.com www.your_domain.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 10240;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # API routes
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeout ayarları
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
        
        # Buffer ayarları
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # FastAPI docs
    location /docs {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /redoc {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:5000;
        access_log off;
        proxy_set_header Host $host;
    }
    
    # Static files (if any)
    location /static/ {
        root /opt/mevzuatgpt;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # File upload limits
    client_max_body_size 50M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    
    # Rate limiting (opsiyonel)
    # limit_req zone=api burst=20 nodelay;
}

# Rate limiting zone tanımı (opsiyonel)
# http {
#     limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
# }
```

### Site'i Aktifleştir
```bash
# Sembolik link oluştur
sudo ln -s /etc/nginx/sites-available/mevzuatgpt /etc/nginx/sites-enabled/

# Default site'i kaldır (opsiyonel)
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx konfigürasyonunu test et
sudo nginx -t

# Nginx'i yeniden başlat
sudo systemctl restart nginx
```

---

## 🔒 7. SSL Sertifikası (Let's Encrypt)

### Certbot Kurulumu
```bash
sudo apt install -y snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot

# Certbot'u PATH'e ekle
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

### SSL Sertifikası Alma
```bash
# Otomatik nginx konfigürasyonu ile
sudo certbot --nginx -d your_domain.com -d www.your_domain.com

# Manuel olarak (sadece sertifika):
# sudo certbot certonly --nginx -d your_domain.com -d www.your_domain.com
```

### Otomatik Yenileme
```bash
# Crontab'a otomatik yenileme ekle
sudo crontab -e

# Bu satırı ekle:
0 12 * * * /usr/bin/certbot renew --quiet

# Test için:
sudo certbot renew --dry-run
```

---

## 🔥 8. Firewall Konfigürasyonu

### UFW Firewall Kurulumu
```bash
# UFW'yi aktifleştir
sudo ufw --force enable

# Gerekli portları aç
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'

# HTTP ve HTTPS'yi ayrı ayrı da açabilirsiniz:
# sudo ufw allow 80/tcp
# sudo ufw allow 443/tcp

# Status kontrol
sudo ufw status verbose
```

---

## 📊 9. Logging ve Monitoring

### Log Dizinleri
```bash
sudo mkdir -p /var/log/mevzuatgpt
sudo chown www-data:www-data /var/log/mevzuatgpt
```

### Logrotate Konfigürasyonu
```bash
sudo nano /etc/logrotate.d/mevzuatgpt
```

```conf
/var/log/mevzuatgpt/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    copytruncate
    postrotate
        systemctl reload mevzuat-api > /dev/null 2>&1 || true
    endscript
}
```

### Sistem Log'larını İzleme
```bash
# API server logları
sudo journalctl -u mevzuat-api -f

# Celery worker logları  
sudo journalctl -u mevzuat-celery -f

# Nginx logları
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Tüm servis durumları
systemctl status mevzuat-api mevzuat-celery nginx
```

---

## 🚀 10. Deployment Script

### Otomatik Deployment Script'i
```bash
nano /opt/mevzuatgpt/deploy.sh
chmod +x /opt/mevzuatgpt/deploy.sh
```

```bash
#!/bin/bash

echo "🚀 MevzuatGPT Production Deployment Starting..."
echo "=================================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to project directory
cd /opt/mevzuatgpt

echo -e "${YELLOW}📥 Updating code from repository...${NC}"
# Git pull (if using git)
git pull origin main

echo -e "${YELLOW}🐍 Activating virtual environment...${NC}"
source venv/bin/activate

echo -e "${YELLOW}📦 Installing/updating dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${YELLOW}🔄 Restarting services...${NC}"
sudo systemctl restart mevzuat-api
sudo systemctl restart mevzuat-celery

echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 10

echo -e "${YELLOW}🏥 Performing health checks...${NC}"
# Health check API
if curl -f -s http://localhost:5000/health > /dev/null; then
    echo -e "${GREEN}✅ API health check passed${NC}"
else
    echo -e "${RED}❌ API health check failed!${NC}"
    exit 1
fi

# Check services status
API_STATUS=$(systemctl is-active mevzuat-api)
CELERY_STATUS=$(systemctl is-active mevzuat-celery)

if [ "$API_STATUS" = "active" ]; then
    echo -e "${GREEN}✅ API service is running${NC}"
else
    echo -e "${RED}❌ API service is not running!${NC}"
    exit 1
fi

if [ "$CELERY_STATUS" = "active" ]; then
    echo -e "${GREEN}✅ Celery worker is running${NC}"
else
    echo -e "${RED}❌ Celery worker is not running!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo "=================================================="
echo "🔗 API: https://your_domain.com/api/"
echo "📚 Docs: https://your_domain.com/docs"
echo "🏥 Health: https://your_domain.com/health"
echo "=================================================="
```

---

## 🔍 11. Test ve Doğrulama

### Manuel Testler
```bash
# 1. Local API test
curl -X GET http://localhost:5000/health

# 2. Domain üzerinden test  
curl -X GET https://your_domain.com/health

# 3. SSL certificate kontrolü
curl -I https://your_domain.com

# 4. API endpoints test
curl -X GET https://your_domain.com/api/health

# 5. Service status kontrolü
sudo systemctl status mevzuat-api
sudo systemctl status mevzuat-celery
sudo systemctl status nginx
```

### Automated Test Script
```bash
nano /opt/mevzuatgpt/health_check.sh
chmod +x /opt/mevzuatgpt/health_check.sh
```

```bash
#!/bin/bash

echo "🏥 MevzuatGPT Health Check Starting..."

# Test endpoints
ENDPOINTS=(
    "http://localhost:5000/health"
    "https://your_domain.com/health"
    "https://your_domain.com/api/health"
)

for endpoint in "${ENDPOINTS[@]}"; do
    if curl -f -s "$endpoint" > /dev/null; then
        echo "✅ $endpoint - OK"
    else
        echo "❌ $endpoint - FAILED"
    fi
done

# Service status
services=("mevzuat-api" "mevzuat-celery" "nginx")

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo "✅ $service - Running"
    else
        echo "❌ $service - Not Running"
    fi
done
```

---

## 📱 12. Domain ve DNS Ayarları

### DNS Records (Örnek)
```
# A Records
your_domain.com        A    123.456.789.123  (VPS IP)
www.your_domain.com    A    123.456.789.123  (VPS IP)

# CNAME Records (alternatif)
www.your_domain.com    CNAME    your_domain.com
```

### DNS Propagation Test
```bash
# DNS kontrolü
nslookup your_domain.com
dig your_domain.com

# SSL kontrolü
openssl s_client -connect your_domain.com:443 -servername your_domain.com
```

---

## ⚡ 13. Performans Optimizasyonu

### Nginx Worker Processes
```bash
sudo nano /etc/nginx/nginx.conf
```

```nginx
# CPU core sayısına göre ayarlayın
worker_processes auto;
worker_connections 1024;

# Event model
events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}
```

### Sistem Optimizasyonu
```bash
# File descriptor limits
echo "www-data soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "www-data hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Kernel parameters
echo "net.core.somaxconn = 65536" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## ✅ Production Deployment Checklist

### Kurulum Öncesi
- [ ] VPS hazır (Ubuntu 24.04, minimum 4GB RAM)
- [ ] Domain name kaydı yapıldı
- [ ] DNS A records ayarlandı
- [ ] Uzak servis credentials'ları hazır (Supabase, Redis, Elasticsearch)

### Kurulum Sırası
- [ ] Sistem güncellemesi yapıldı
- [ ] Python 3.11+ kuruldu
- [ ] Nginx kuruldu ve başlatıldı
- [ ] Proje kodu transfer edildi
- [ ] Virtual environment oluşturuldu
- [ ] Dependencies yüklendi
- [ ] .env dosyası konfigüre edildi
- [ ] Systemd services oluşturuldu ve başlatıldı
- [ ] Nginx reverse proxy konfigüre edildi
- [ ] SSL sertifikası kuruldu
- [ ] Firewall ayarlandı

### Test ve Doğrulama
- [ ] API health endpoint çalışıyor
- [ ] HTTPS erişimi aktif
- [ ] Celery worker çalışıyor
- [ ] Log monitoring çalışıyor
- [ ] Deploy script test edildi
- [ ] Uzak servis bağlantıları test edildi (Redis, Supabase, Elasticsearch)

### Production Hazır
- [ ] Domain üzerinden API erişilebilir
- [ ] SSL sertifikası otomatik yenileniyor
- [ ] Monitoring ve alerting aktif
- [ ] Backup stratejisi belirlendi
- [ ] Documentation güncel

---

## 🚨 Troubleshooting

### Yaygın Problemler ve Çözümleri

**1. Service başlamıyor:**
```bash
sudo journalctl -u mevzuat-api -f
sudo systemctl status mevzuat-api
```

**2. Port 5000 kullanımda:**
```bash
sudo lsof -i :5000
sudo netstat -tlnp | grep :5000
```

**3. Nginx 502 Bad Gateway:**
```bash
sudo nginx -t
sudo systemctl status nginx
curl http://localhost:5000/health
```

**4. SSL sertifikası sorunu:**
```bash
sudo certbot certificates
sudo certbot renew --force-renewal
```

**5. Permission errors:**
```bash
sudo chown -R www-data:www-data /opt/mevzuatgpt
sudo chmod +x /opt/mevzuatgpt/venv/bin/python
```

---

## 📞 Production Support

### Log Locations
- API Server: `sudo journalctl -u mevzuat-api -f`
- Celery Worker: `sudo journalctl -u mevzuat-celery -f`  
- Nginx Access: `/var/log/nginx/access.log`
- Nginx Error: `/var/log/nginx/error.log`

### Useful Commands
```bash
# Service yeniden başlatma
sudo systemctl restart mevzuat-api mevzuat-celery nginx

# Real-time monitoring
sudo journalctl -u mevzuat-api -u mevzuat-celery -f

# Resource usage
htop
df -h
free -h
```

**🎯 Bu rehberle MevzuatGPT projeniz production VPS'de sorunsuz çalışacak!**