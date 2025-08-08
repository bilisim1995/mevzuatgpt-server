#!/usr/bin/env python3
"""
Direct OpenAI API Test with Specified Key
"""

import asyncio
import httpx
import json

async def test_openai_direct():
    """Test OpenAI API directly with the specified key"""
    
    api_key = "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"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "input": "Bu bir direkt OpenAI API testidir",
        "model": "text-embedding-3-small"
    }
    
    print("🔍 OpenAI API Direkt Test")
    print("=" * 40)
    print(f"Key başlangıcı: {api_key[:30]}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                embedding = data['data'][0]['embedding']
                usage = data.get('usage', {})
                
                print("✅ BAŞARILI!")
                print(f"   HTTP Status: {response.status_code}")
                print(f"   Embedding boyutu: {len(embedding)}")
                print(f"   Token kullanımı: {usage.get('total_tokens', 'unknown')}")
                print(f"   Model: {data.get('model', 'unknown')}")
                return True
                
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": "Non-JSON response"}
                print("❌ BAŞARISIZ!")
                print(f"   HTTP Status: {response.status_code}")
                print(f"   Hata: {error_data.get('error', {}).get('message', 'Bilinmeyen hata')}")
                return False
                
    except Exception as e:
        print(f"❌ İstisnai durum: {str(e)}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_openai_direct())
    print(f"\nSonuç: {'API çalışıyor' if result else 'API çalışmıyor'}")