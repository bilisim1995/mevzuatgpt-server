# MevzuatGPT cURL Örnekleri

## Sistem Durumu Kontrolü

```bash
# Health check
curl -X GET "http://0.0.0.0:5000/health"

# API bilgisi
curl -X GET "http://0.0.0.0:5000/"
```

## Authentication

### Login
```bash
curl -X POST "http://0.0.0.0:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mevzuatgpt.com",
    "password": "admin123"
  }'
```

### Register
```bash
curl -X POST "http://0.0.0.0:5000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "full_name": "Test User",
    "institution": "Test Institution"
  }'
```

## Soru Sorma (Ask Endpoint)

### Basit Soru
```bash
curl -X POST "http://0.0.0.0:5000/api/user/ask" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "KVKK kapsamında kişisel veri nedir?"
  }'
```

### Detaylı Soru
```bash
curl -X POST "http://0.0.0.0:5000/api/user/ask" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "İş güvenliği mevzuatına göre işveren yükümlülükleri nelerdir?",
    "institution_filter": "Çalışma ve Sosyal Güvenlik Bakanlığı",
    "limit": 5,
    "similarity_threshold": 0.8,
    "use_cache": true
  }'
```

### Hukuki Danışmanlık
```bash
curl -X POST "http://0.0.0.0:5000/api/user/ask" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Şirket kuruluş süreçlerinde hangi belgeler gereklidir?",
    "limit": 3,
    "similarity_threshold": 0.75
  }'
```

## Admin İşlemleri

### Belge Yükleme
```bash
curl -X POST "http://0.0.0.0:5000/api/admin/upload" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "title=Test Document" \
  -F "institution=Test Institution" \
  -F "category=regulation"
```

### Belge Listesi
```bash
curl -X GET "http://0.0.0.0:5000/api/admin/documents?page=1&limit=10" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## User Services

### Öneri Listesi
```bash
curl -X GET "http://0.0.0.0:5000/api/user/suggestions" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Test Script'i

```bash
#!/bin/bash

BASE_URL="http://0.0.0.0:5000"
TOKEN=""

# 1. Health check
echo "=== Health Check ==="
curl -X GET "$BASE_URL/health"
echo -e "\n"

# 2. Login
echo "=== Login ==="
RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mevzuatgpt.com",
    "password": "admin123"
  }')

TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')
echo "Token: $TOKEN"
echo -e "\n"

# 3. Ask Question
if [ ! -z "$TOKEN" ]; then
  echo "=== Ask Question ==="
  curl -X POST "$BASE_URL/api/user/ask" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "query": "KVKK nedir?"
    }'
  echo -e "\n"
fi
```

## Production Test Commands

### VPS Hazırlık Test
```bash
# System readiness test
python tests/final_vps_ready_test.py

# Environment test
python tests/env_based_test.py

# API connection test
curl -X GET "http://0.0.0.0:5000/health"
```

### Performance Test
```bash
# Measure response time
time curl -X POST "http://0.0.0.0:5000/api/user/ask" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Test performance"}' \
  -w "\nTime: %{time_total}s\nStatus: %{http_code}\n"
```

## Troubleshooting

### Bağlantı Testi
```bash
# Port kontrolü
curl -I "http://0.0.0.0:5000"

# Network connectivity
ping 0.0.0.0

# Service status
curl -v "http://0.0.0.0:5000/health"
```

### Error Response Examples
```bash
# 401 Unauthorized
{"success":false,"error":{"message":"Authentication required","detail":"Valid Bearer token required","code":"UNAUTHORIZED"}}

# 429 Rate Limited
{"success":false,"error":{"message":"Rate limit exceeded","detail":"Maximum 30 requests per minute allowed","code":"RATE_LIMIT_EXCEEDED"}}

# 400 Bad Request
{"success":false,"error":{"message":"Invalid request","detail":"Query must be at least 3 characters long","code":"VALIDATION_ERROR"}}
```