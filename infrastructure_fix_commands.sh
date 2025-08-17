#!/bin/bash
# Infrastructure Team Fix Commands
# PostgREST Schema Cache (PGRST002) Fix

echo "🔧 PostgREST Schema Cache Fix Commands"
echo "======================================"

echo "1️⃣ Restart PostgREST container:"
echo "docker restart supabase-rest"
echo

echo "2️⃣ Check PostgREST logs:"
echo "docker logs supabase-rest --tail 20"
echo

echo "3️⃣ If restart doesn't work, recreate container:"
echo "docker-compose stop rest"
echo "docker-compose up -d rest"
echo

echo "4️⃣ Check database connection from PostgREST:"
echo "docker exec supabase-rest postgrest --help"
echo

echo "5️⃣ Alternative: Full service restart:"
echo "docker-compose restart"
echo

echo "6️⃣ Check specific PostgREST endpoint:"
echo "curl -v http://localhost:3000/"
echo

echo "💡 Expected result after fix:"
echo "- PostgREST should return HTTP 200"
echo "- Schema cache error should disappear"
echo "- MevzuatGPT test should show 6/6 passed"

echo
echo "🧪 Test command after fix:"
echo "python test_supabase_connection.py"