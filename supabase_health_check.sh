#!/bin/bash
# Supabase Health Check Script - Run on server

echo "🏥 Supabase Health Check - $(date)"
echo "=================================="

# Check container status
echo "📦 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep supabase

echo ""

# Check PostgREST specifically
echo "🔌 PostgREST Health:"
POSTGREST_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/)
if [ "$POSTGREST_HEALTH" = "200" ]; then
    echo "✅ PostgREST responding (HTTP $POSTGREST_HEALTH)"
else
    echo "❌ PostgREST issues (HTTP $POSTGREST_HEALTH)"
fi

echo ""

# Check PostgreSQL
echo "🗄️ PostgreSQL Health:"
PG_HEALTH=$(docker exec supabase-db pg_isready -U postgres)
if [[ $PG_HEALTH == *"accepting connections"* ]]; then
    echo "✅ PostgreSQL accepting connections"
else
    echo "❌ PostgreSQL connection issues"
fi

echo ""

# Check auth service
echo "🔐 Auth Service Health:"
AUTH_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9999/health)
if [ "$AUTH_HEALTH" = "200" ]; then
    echo "✅ Auth service responding (HTTP $AUTH_HEALTH)"
else
    echo "❌ Auth service issues (HTTP $AUTH_HEALTH)"
fi

echo ""
echo "💡 If issues found, run: docker-compose restart"
