#!/bin/bash

# MevzuatGPT System Health Check Script
# Bu script tüm servislerin erişilebilirliğini kontrol eder

echo "============================================="
echo "🔍 MevzuatGPT System Health Check"
echo "============================================="
echo "$(date)"
echo ""

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Başarı/Hata sayaçları
SUCCESS=0
FAILED=0

# Test fonksiyonu
test_service() {
    local name="$1"
    local url="$2"
    local expected_code="$3"
    
    echo -n "📡 Testing $name... "
    
    response_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 30 "$url" 2>/dev/null)
    
    if [ "$response_code" = "$expected_code" ]; then
        echo -e "${GREEN}✅ OK ($response_code)${NC}"
        ((SUCCESS++))
    else
        echo -e "${RED}❌ FAILED (Got: $response_code, Expected: $expected_code)${NC}"
        ((FAILED++))
    fi
}

# Systemd servis durumu kontrolü
check_systemd_service() {
    local service_name="$1"
    
    echo -n "⚙️  Checking $service_name service... "
    
    if systemctl is-active --quiet "$service_name"; then
        echo -e "${GREEN}✅ RUNNING${NC}"
        ((SUCCESS++))
    else
        echo -e "${RED}❌ NOT RUNNING${NC}"
        ((FAILED++))
    fi
}

# Port kontrolü
check_port() {
    local service_name="$1"
    local port="$2"
    
    echo -n "🔌 Checking $service_name port $port... "
    
    if netstat -tuln | grep -q ":$port "; then
        echo -e "${GREEN}✅ LISTENING${NC}"
        ((SUCCESS++))
    else
        echo -e "${RED}❌ NOT LISTENING${NC}"
        ((FAILED++))
    fi
}

echo "🚀 1. SYSTEMD SERVICES CHECK"
echo "---------------------------------------------"
check_systemd_service "nginx"
check_systemd_service "mevzuatgpt-api"
check_systemd_service "mevzuatgpt-celery"
check_systemd_service "redis-server"
echo ""

echo "🔌 2. PORT AVAILABILITY CHECK"
echo "---------------------------------------------"
check_port "Nginx HTTP" "80"
check_port "Nginx HTTPS" "443"
check_port "FastAPI" "8000"
check_port "Redis" "6379"
echo ""

echo "🌐 3. HTTP ENDPOINTS CHECK"
echo "---------------------------------------------"
# Nginx (Ana sayfa)
test_service "Nginx (Main Page)" "http://localhost/" "200"

# FastAPI Health Endpoint
test_service "FastAPI Health" "http://localhost:8000/health" "200"

# FastAPI API Info
test_service "FastAPI API Info" "http://localhost:8000/api" "200"

# FastAPI Docs (eğer debug mode açıksa)
test_service "FastAPI Docs" "http://localhost:8000/docs" "200"

echo ""

echo "🔍 4. EXTERNAL SERVICES CHECK"
echo "---------------------------------------------"
# Elasticsearch
test_service "Elasticsearch" "https://elastic.mevzuatgpt.org" "200"

# Supabase
test_service "Supabase" "https://supabase.mevzuatgpt.org/rest/v1/" "200"

echo ""

echo "📊 5. REDIS CONNECTION CHECK"
echo "---------------------------------------------"
echo -n "🔴 Testing Redis connection... "
if redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN}✅ PONG${NC}"
    ((SUCCESS++))
else
    echo -e "${RED}❌ NO RESPONSE${NC}"
    ((FAILED++))
fi

echo ""

echo "📈 6. CELERY WORKER CHECK"
echo "---------------------------------------------"
echo -n "👷 Testing Celery workers... "
# Celery worker durumunu kontrol et
celery_status=$(cd /var/www/mevzuatgpt && source venv/bin/activate && celery -A tasks.celery_app inspect active 2>/dev/null | grep -c "OK" || echo "0")
if [ "$celery_status" -gt 0 ]; then
    echo -e "${GREEN}✅ $celery_status WORKER(S) ACTIVE${NC}"
    ((SUCCESS++))
else
    echo -e "${RED}❌ NO ACTIVE WORKERS${NC}"
    ((FAILED++))
fi

echo ""

# Özet rapor
echo "============================================="
echo "📋 HEALTH CHECK SUMMARY"
echo "============================================="
echo -e "✅ ${GREEN}Successful checks: $SUCCESS${NC}"
echo -e "❌ ${RED}Failed checks: $FAILED${NC}"
echo -e "📊 ${BLUE}Total checks: $((SUCCESS + FAILED))${NC}"
echo ""

# Genel sistem durumu
if [ $FAILED -eq 0 ]; then
    echo -e "🎉 ${GREEN}ALL SYSTEMS OPERATIONAL${NC}"
    exit 0
elif [ $FAILED -le 2 ]; then
    echo -e "⚠️  ${YELLOW}SOME SERVICES HAVE ISSUES${NC}"
    exit 1
else
    echo -e "🚨 ${RED}CRITICAL SYSTEM ISSUES DETECTED${NC}"
    exit 2
fi